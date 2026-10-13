"""Бизнес-логика сервиса брокерского обслуживания. Работает правильно: ошибки ищите в тестах, а не здесь."""
import random
import secrets
import time
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sandbox.db import Database, now
from sandbox.kafka import Broker

TARIFFS = {'INVESTOR': 'Инвестор', 'TRADER': 'Трейдер'}
# Комиссия за вывод средств: на «Инвесторе» 0,3 %, на «Трейдере» вывод бесплатный
WITHDRAW_COMMISSION = {'INVESTOR': Decimal('0.003'), 'TRADER': Decimal('0')}
MAX_FAILED_LOGINS = 3
ORDER_EXECUTION_DELAY = 1.5


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def money(value) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ApiError(400, 'VALIDATION_ERROR', 'Сумма должна быть числом')
    if amount <= 0 or amount != amount.quantize(Decimal('0.01')):
        raise ApiError(400, 'VALIDATION_ERROR', 'Сумма должна быть больше нуля, не больше двух знаков после запятой')
    return amount


def as_number(value: Decimal):
    """Деньги в БД: целые — INTEGER, с копейками — REAL, как их хранит колонка NUMERIC."""
    return int(value) if value == value.to_integral_value() else float(value)


class InvestService:

    def __init__(self, db: Database, kafka: Broker):
        self.db = db
        self.kafka = kafka
        self.backoffice_tokens = {}
        self.client_tokens = {}
        self.offsets = {'cft.incoming-payments': 0, 'sofr.get-tax-report-info-response': 0}

    # --- авторизация ---

    def backoffice_login(self, login: str, password: str) -> dict:
        user = self.db.one('SELECT * FROM backoffice_user WHERE login = ?', login)
        if not user or user['password'] != password:
            raise ApiError(401, 'INVALID_CREDENTIALS', 'Неверный логин или пароль')
        token = secrets.token_hex(16)
        self.backoffice_tokens[token] = login
        return {'token': token, 'name': user['name']}

    def client_login(self, login: str, password: str) -> dict:
        with self.db.lock:
            client = self.db.one('SELECT * FROM client WHERE login = ?', login)
            if not client:
                raise ApiError(401, 'INVALID_CREDENTIALS', 'Неверный логин или пароль')
            if client['status'] == 'LOCKED':
                raise ApiError(423, 'USER_LOCKED', 'Учётная запись заблокирована. Обратитесь в поддержку')
            if client['password'] != password:
                failed = client['failed_logins'] + 1
                status = 'LOCKED' if failed >= MAX_FAILED_LOGINS else client['status']
                self.db.execute('UPDATE client SET failed_logins = ?, status = ? WHERE id = ?', failed, status, client['id'])
                raise ApiError(401, 'INVALID_CREDENTIALS', 'Неверный логин или пароль')
            self.db.execute('UPDATE client SET failed_logins = 0 WHERE id = ?', client['id'])
        token = secrets.token_hex(16)
        self.client_tokens[token] = client['id']
        return {'token': token, 'clientId': client['id']}

    def backoffice_user(self, token):
        if token not in self.backoffice_tokens:
            raise ApiError(401, 'UNAUTHORIZED', 'Требуется авторизация сотрудника бэк-офиса')
        return self.backoffice_tokens[token]

    def client_id(self, token) -> int:
        if token not in self.client_tokens:
            raise ApiError(401, 'UNAUTHORIZED', 'Требуется авторизация клиента')
        if not self.db.one('SELECT id FROM client WHERE id = ?', self.client_tokens[token]):
            raise ApiError(401, 'UNAUTHORIZED', 'Клиент не найден, авторизуйтесь заново')
        return self.client_tokens[token]

    # --- клиенты и договоры (бэк-офис) ---

    def create_client(self, body: dict) -> dict:
        required = ('login', 'password', 'lastName', 'firstName', 'phone')
        missing = [f for f in required if not body.get(f)]
        if missing:
            raise ApiError(400, 'VALIDATION_ERROR', 'Не заполнены поля: ' + ', '.join(missing))
        tariff = body.get('tariff') or 'INVESTOR'
        if tariff not in TARIFFS:
            raise ApiError(400, 'VALIDATION_ERROR', f'Неизвестный тариф {tariff}')
        with self.db.lock:
            if self.db.one('SELECT id FROM client WHERE login = ?', body['login']):
                raise ApiError(409, 'LOGIN_EXISTS', f"Логин {body['login']} уже занят")
            client_id = self.db.execute(
                'INSERT INTO client (login, password, last_name, first_name, middle_name, phone, tariff, status, created_at)'
                " VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)",
                body['login'], body['password'], body['lastName'], body['firstName'], body.get('middleName'),
                body['phone'], tariff, now())
        client = self.describe_client(client_id)
        self.kafka.publish('invest.client-events', client['login'], {
            'eventType': 'CLIENT_CREATED', 'clientId': client['id'], 'login': client['login'],
            'tariff': client['tariff'], 'eventTime': event_time()})
        return client

    def describe_client(self, client_id: int) -> dict:
        c = self.db.one('SELECT * FROM client WHERE id = ?', client_id)
        if not c:
            raise ApiError(404, 'NOT_FOUND', f'Клиент {client_id} не найден')
        return {'id': c['id'], 'login': c['login'], 'lastName': c['last_name'], 'firstName': c['first_name'],
                'middleName': c['middle_name'], 'phone': c['phone'], 'tariff': c['tariff'], 'status': c['status']}

    def open_agreement(self, client_id: int, body: dict) -> dict:
        kind = body.get('type')
        if kind not in ('BROKER', 'IIS'):
            raise ApiError(400, 'VALIDATION_ERROR', 'Тип договора — BROKER или IIS')
        self.describe_client(client_id)
        with self.db.lock:
            if kind == 'IIS' and self.db.one(
                    "SELECT id FROM agreement WHERE client_id = ? AND type = 'IIS' AND status = 'ACTIVE'", client_id):
                raise ApiError(409, 'IIS_ALREADY_EXISTS', 'У клиента уже есть действующий ИИС')
            prefix = 'ИИС' if kind == 'IIS' else 'БД'
            number = f'{prefix}-{random.randint(2000000, 9999999)}'
            agreement_id = self.db.execute(
                "INSERT INTO agreement (client_id, number, type, status, opened_at) VALUES (?, ?, ?, 'ACTIVE', ?)",
                client_id, number, kind, now())
            self.db.execute("INSERT INTO account (agreement_id, currency, balance) VALUES (?, 'RUB', 0)", agreement_id)
        return self.describe_agreement(agreement_id)

    def describe_agreement(self, agreement_id: int) -> dict:
        a = self.db.one('SELECT a.*, acc.balance, acc.currency FROM agreement a JOIN account acc ON acc.agreement_id = a.id'
                        ' WHERE a.id = ?', agreement_id)
        return {'id': a['id'], 'clientId': a['client_id'], 'number': a['number'], 'type': a['type'],
                'status': a['status'], 'openedAt': a['opened_at'], 'currency': a['currency'],
                'balance': f"{Decimal(str(a['balance'])):.2f}"}

    # --- операции клиента ---

    def own_agreement(self, client_id: int, agreement_id: int) -> dict:
        a = self.db.one('SELECT * FROM agreement WHERE id = ? AND client_id = ?', agreement_id, client_id)
        if not a:
            raise ApiError(404, 'NOT_FOUND', f'Договор {agreement_id} не найден')
        return a

    def agreements(self, client_id: int) -> list:
        rows = self.db.all('SELECT id FROM agreement WHERE client_id = ? ORDER BY id', client_id)
        return [self.describe_agreement(r['id']) for r in rows]

    def agreement(self, client_id: int, agreement_id: int) -> dict:
        self.own_agreement(client_id, agreement_id)
        return self.describe_agreement(agreement_id)

    def refill(self, client_id: int, agreement_id: int, body: dict) -> dict:
        a = self.own_agreement(client_id, agreement_id)
        if a['status'] != 'ACTIVE':
            raise ApiError(409, 'AGREEMENT_CLOSED', 'Договор закрыт')
        amount = money(body.get('amount'))
        order_id = self.db.execute(
            "INSERT INTO money_order (agreement_id, type, amount, status, created_at) VALUES (?, 'REFILL', ?, 'NEW', ?)",
            agreement_id, as_number(amount), now())
        self.publish_order(order_id, 'API')
        return self.describe_order(order_id)

    def withdraw(self, client_id: int, agreement_id: int, body: dict) -> dict:
        a = self.own_agreement(client_id, agreement_id)
        if a['status'] != 'ACTIVE':
            raise ApiError(409, 'AGREEMENT_CLOSED', 'Договор закрыт')
        amount = money(body.get('amount'))
        tariff = self.db.one('SELECT tariff FROM client WHERE id = ?', client_id)['tariff']
        commission = (amount * WITHDRAW_COMMISSION[tariff]).quantize(Decimal('0.01'))
        with self.db.lock:
            if amount + commission > self.available(agreement_id):
                raise ApiError(422, 'INSUFFICIENT_FUNDS', 'Недостаточно средств для вывода')
            order_id = self.db.execute(
                'INSERT INTO money_order (agreement_id, type, amount, commission, status, created_at)'
                " VALUES (?, 'WITHDRAW', ?, ?, 'NEW', ?)",
                agreement_id, as_number(amount), as_number(commission), now())
        self.publish_order(order_id, 'API')
        return self.describe_order(order_id)

    def publish_order(self, order_id: int, source: str):
        o = self.db.one('SELECT o.*, a.number FROM money_order o JOIN agreement a ON a.id = o.agreement_id'
                        ' WHERE o.id = ?', order_id)
        self.kafka.publish('invest.money-orders', o['number'], {
            'eventType': 'MONEY_ORDER_STATUS', 'orderId': o['id'], 'agreementId': o['agreement_id'],
            'agreementNumber': o['number'], 'type': o['type'], 'amount': f"{Decimal(str(o['amount'])):.2f}",
            'status': o['status'], 'source': source, 'eventTime': event_time()})

    def available(self, agreement_id: int) -> Decimal:
        balance = self.db.one('SELECT balance FROM account WHERE agreement_id = ?', agreement_id)['balance']
        pending = self.db.one("SELECT COALESCE(SUM(amount + commission), 0) AS s FROM money_order"
                              " WHERE agreement_id = ? AND type = 'WITHDRAW' AND status = 'NEW'", agreement_id)['s']
        return Decimal(str(balance)) - Decimal(str(pending))

    def describe_order(self, order_id: int) -> dict:
        o = self.db.one('SELECT * FROM money_order WHERE id = ?', order_id)
        return {'id': o['id'], 'agreementId': o['agreement_id'], 'type': o['type'],
                'amount': f"{Decimal(str(o['amount'])):.2f}", 'commission': f"{Decimal(str(o['commission'])):.2f}",
                'status': o['status'], 'createdAt': o['created_at']}

    def order(self, client_id: int, order_id: int) -> dict:
        o = self.db.one('SELECT * FROM money_order WHERE id = ?', order_id)
        if not o:
            raise ApiError(404, 'NOT_FOUND', f'Поручение {order_id} не найдено')
        self.own_agreement(client_id, o['agreement_id'])
        return self.describe_order(order_id)

    def close_agreement(self, client_id: int, agreement_id: int) -> dict:
        a = self.own_agreement(client_id, agreement_id)
        if a['status'] != 'ACTIVE':
            raise ApiError(409, 'AGREEMENT_CLOSED', 'Договор уже закрыт')
        with self.db.lock:
            balance = self.db.one('SELECT balance FROM account WHERE agreement_id = ?', agreement_id)['balance']
            pending = self.db.one("SELECT COUNT(*) AS c FROM money_order WHERE agreement_id = ? AND status = 'NEW'",
                                  agreement_id)['c']
            if Decimal(str(balance)) != 0 or pending:
                raise ApiError(409, 'NONZERO_BALANCE', 'Для закрытия договора выведите денежные средства')
            self.db.execute("UPDATE agreement SET status = 'CLOSED', closed_at = ? WHERE id = ?", now(), agreement_id)
        return self.describe_agreement(agreement_id)

    def order_tax_report(self, client_id: int, body: dict) -> dict:
        try:
            period = int(body.get('taxPeriod'))
        except (TypeError, ValueError):
            raise ApiError(400, 'VALIDATION_ERROR', 'Укажите год taxPeriod')
        if period >= datetime.now().year:
            raise ApiError(422, 'TAX_PERIOD_UNAVAILABLE', 'Справку можно заказать только за завершённый год')
        agreements = self.db.all("SELECT number FROM agreement WHERE client_id = ? AND type = 'BROKER' ORDER BY id",
                                 client_id)
        if not agreements:
            raise ApiError(422, 'NO_AGREEMENTS', 'У клиента нет брокерских договоров')
        request_id = str(uuid.uuid4())
        report_id = self.db.execute(
            'INSERT INTO tax_report (client_id, tax_period, status, request_id, registered_at)'
            " VALUES (?, ?, 'ORDERED', ?, ?)", client_id, period, request_id, now())
        self.kafka.publish('sofr.get-tax-report-info-request', request_id, {'GetTaxReportInfoReq': {
            'RequestId': request_id, 'ClientId': client_id, 'AgreementNumbers': [a['number'] for a in agreements],
            'TaxPeriod': str(period), 'RequestTime': event_time()}})
        return self.describe_tax_report(report_id)

    def describe_tax_report(self, report_id: int) -> dict:
        r = self.db.one('SELECT * FROM tax_report WHERE id = ?', report_id)
        return {'id': r['id'], 'taxPeriod': r['tax_period'], 'status': r['status'], 'fileName': r['file_name'],
                'registeredAt': r['registered_at']}

    def tax_reports(self, client_id: int) -> list:
        rows = self.db.all('SELECT id FROM tax_report WHERE client_id = ? ORDER BY id DESC', client_id)
        return [self.describe_tax_report(r['id']) for r in rows]

    def orders(self, client_id: int, agreement_id: int) -> list:
        self.own_agreement(client_id, agreement_id)
        rows = self.db.all('SELECT id FROM money_order WHERE agreement_id = ? ORDER BY id DESC', agreement_id)
        return [self.describe_order(r['id']) for r in rows]

    def tax_report(self, client_id: int, report_id: int) -> dict:
        if not self.db.one('SELECT id FROM tax_report WHERE id = ? AND client_id = ?', report_id, client_id):
            raise ApiError(404, 'NOT_FOUND', f'Заявка на справку {report_id} не найдена')
        return self.describe_tax_report(report_id)

    def change_tariff(self, client_id: int, body: dict) -> dict:
        tariff = body.get('tariff')
        if tariff not in TARIFFS:
            raise ApiError(400, 'VALIDATION_ERROR', f'Неизвестный тариф {tariff}')
        with self.db.lock:
            old = self.db.one('SELECT tariff FROM client WHERE id = ?', client_id)['tariff']
            if old == tariff:
                raise ApiError(409, 'TARIFF_ALREADY_SET', f'Тариф «{TARIFFS[tariff]}» уже подключён')
            if self.db.one("SELECT o.id FROM money_order o JOIN agreement a ON a.id = o.agreement_id"
                           " WHERE a.client_id = ? AND o.status = 'NEW'", client_id):
                raise ApiError(409, 'PENDING_ORDERS',
                               f'Нельзя перейти на тариф «{TARIFFS[tariff]}», пока есть неисполненные поручения')
            self.db.execute('UPDATE client SET tariff = ? WHERE id = ?', tariff, client_id)
            self.db.execute('INSERT INTO tariff_history (client_id, old_tariff, new_tariff, changed_at) VALUES (?, ?, ?, ?)',
                            client_id, old, tariff, now())
        return self.describe_client(client_id)

    # --- фоновые процессы ---

    def execute_orders(self):
        """Исполняет поручения через ORDER_EXECUTION_DELAY секунд после создания — как процессинг на стенде."""
        with self.db.lock:
            for o in self.db.all("SELECT * FROM money_order WHERE status = 'NEW' ORDER BY id"):
                created = datetime.strptime(o['created_at'], '%Y-%m-%d %H:%M:%S')
                if (datetime.now() - created).total_seconds() < ORDER_EXECUTION_DELAY:
                    continue
                balance = Decimal(str(self.db.one('SELECT balance FROM account WHERE agreement_id = ?',
                                                  o['agreement_id'])['balance']))
                amount = Decimal(str(o['amount'])) + Decimal(str(o['commission']))
                balance = balance + amount if o['type'] == 'REFILL' else balance - amount
                self.db.execute('UPDATE account SET balance = ? WHERE agreement_id = ?', as_number(balance),
                                o['agreement_id'])
                self.db.execute("UPDATE money_order SET status = 'EXECUTED', executed_at = ? WHERE id = ?", now(), o['id'])
                self.publish_order(o['id'], 'API')

    def stand_activity(self):
        """Другие клиенты тоже пополняют счета: стенд общий, жизнь на нём идёт и без наших тестов."""
        seeded = self.db.all("SELECT a.id FROM agreement a JOIN client c ON c.id = a.client_id"
                             " WHERE c.login NOT LIKE 'autotest%' AND a.status = 'ACTIVE'")
        if seeded:
            agreement_id = random.choice(seeded)['id']
            order_id = self.db.execute(
                "INSERT INTO money_order (agreement_id, type, amount, status, created_at) VALUES (?, 'REFILL', ?, 'NEW', ?)",
                agreement_id, random.choice((1000, 2500, 5000, 10000)), now())
            self.publish_order(order_id, 'API')

    def consume(self):
        """Читает входящие топики: поступления из ЦФТ и готовые справки из СОФР."""
        for topic, handler in (('cft.incoming-payments', self.on_payment),
                               ('sofr.get-tax-report-info-response', self.on_tax_report_ready)):
            for message in self.kafka.read_from(topic, self.offsets[topic]):
                self.offsets[topic] = message['offset'] + 1
                try:
                    handler(message['value'])
                except (KeyError, TypeError, ValueError, InvalidOperation, ApiError):
                    pass  # битое сообщение пропускаем, как и настоящий консьюмер

    def on_payment(self, payment: dict):
        with self.db.lock:
            if self.db.one('SELECT payment_id FROM incoming_payment WHERE payment_id = ?', payment['PaymentId']):
                return  # повторная доставка: платёж уже зачислен
            agreement = self.db.one("SELECT id FROM agreement WHERE number = ? AND status = 'ACTIVE'",
                                    payment['AgreementNumber'])
            if not agreement or payment.get('Currency') != 'RUB':
                return
            amount = money(payment['Amount'])
            order_id = self.db.execute(
                'INSERT INTO money_order (agreement_id, type, amount, status, created_at, executed_at)'
                " VALUES (?, 'REFILL', ?, 'EXECUTED', ?, ?)", agreement['id'], as_number(amount), now(), now())
            balance = Decimal(str(self.db.one('SELECT balance FROM account WHERE agreement_id = ?',
                                              agreement['id'])['balance'])) + amount
            self.db.execute('UPDATE account SET balance = ? WHERE agreement_id = ?', as_number(balance), agreement['id'])
            self.db.execute('INSERT INTO incoming_payment VALUES (?, ?, ?)', payment['PaymentId'], order_id, now())
        self.publish_order(order_id, 'CFT')

    def on_tax_report_ready(self, response: dict):
        if response.get('Status') == 'READY':
            self.db.execute("UPDATE tax_report SET status = 'READY', file_name = ? WHERE request_id = ? AND status = 'ORDERED'",
                            response.get('FileName'), response['RequestId'])


def event_time() -> str:
    """Время события — местное, без часового пояса, с миллисекундами: так его пишут сервисы банка."""
    return datetime.now().isoformat(timespec='milliseconds')


def background(interval: float, action):
    def loop():
        while True:
            time.sleep(interval)
            try:
                action()
            except Exception:  # noqa: BLE001 — фоновый процесс не должен останавливаться
                pass
    return loop
