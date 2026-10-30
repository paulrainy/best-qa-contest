# Справка по проекту

- **`InvestApi`** (`framework/api/invest_api.py`) — методы API. Каждый возвращает `requests.Response` как есть, код ответа не проверяет.
- **`DbClient`** (`framework/db/db_client.py`) — подключение к БД сервиса:
  - `query(sql, *args, fetch_one=False)` выполняет запрос и возвращает строки словарями `{'колонка': значение}`; с `fetch_one=True` — первую строку или `None`;
  - `execute(sql, *args)` выполняет изменение и сразу фиксирует его (commit).
- **`Reporting`** (`framework/reporting.py`) — шаги и метки отчёта Allure, `id` связывает тест с кейсом Test IT.
- **`QAServiceKafkaClient`** (`framework/kafka/qa_service.py`) — доступ к Kafka. Со стендов к Kafka напрямую не подключиться, поэтому сообщения читаются и отправляются через HTTP-сервис QA Service:
  - `subscribe(topic, cluster_id, seconds_ago=60, limit=100)` — сообщения топика за последние `seconds_ago` секунд, не больше `limit`, по возрастанию offset. Каждое сообщение — словарь с полями `topic`, `partition`, `offset`, `timestamp` (миллисекунды), `key`, `value`. Если такого топика нет, QA Service отвечает 400, и метод бросает `requests.HTTPError`;
  - `send(topic, cluster_id, value, key=None)` — отправка сообщения.
- **Фикстуры pytest-playwright** — `page`, `context`, `browser`, `base_url` и другие. Каждый тест получает свой `page` в новом контексте браузера. Браузер — установленный на компьютере, его выбирает корневой `conftest.py`.
- **`Config`** (`framework/config.py`) — адрес стенда, QA Service, идентификатор кластера Kafka и служебные учётные записи из переменных окружения, по умолчанию — песочница.

## Схема БД сервиса

БД сервиса — SQLite. Даты и время хранятся текстом в формате `YYYY-MM-DD HH:MM:SS`, время местное.

| Таблица | Что хранит | Колонки |
| --- | --- | --- |
| `client` | Клиенты | `id`, `login`, `password`, `last_name`, `first_name`, `middle_name`, `phone`, `tariff` (`INVESTOR` — «Инвестор», `TRADER` — «Трейдер»), `status` (`ACTIVE`, `LOCKED`), `failed_logins` — неудачных входов подряд, `created_at` |
| `agreement` | Договоры | `id`, `client_id`, `number`, `type` (`BROKER` — брокерский договор, `IIS` — ИИС), `status` (`ACTIVE`, `CLOSED`), `opened_at`, `closed_at` |
| `account` | Денежные счета договоров | `id`, `agreement_id`, `currency`, `balance` |
| `money_order` | Поручения на пополнение и вывод | `id`, `agreement_id`, `type` (`REFILL`, `WITHDRAW`), `amount`, `commission`, `status` (`NEW`, `EXECUTED`), `created_at`, `executed_at` |
| `tax_report` | Заявки на справки НДФЛ | `id`, `client_id`, `tax_period` — год, `status` (`ORDERED` — заказана, `READY` — готова), `request_id` — идентификатор запроса в СОФР, `file_name` — файл готовой справки, `registered_at` |
| `incoming_payment` | Поступления из ЦФТ, уже зачисленные на счёт | `payment_id`, `order_id` — поручение на пополнение, `received_at` |
| `tariff_history` | История смены тарифа | `id`, `client_id`, `old_tariff`, `new_tariff`, `changed_at` |

Стенд общий: на нём работают другие команды и другие прогоны автотестов, клиенты стенда пополняют счета.

## Топики Kafka

Кластер Kafka стенда — `invest-kafka`. Время в сообщениях — местное, без часового пояса.

| Топик | Кто пишет → кто читает | Что в сообщении |
| --- | --- | --- |
| `invest.client-events` | сервис → другие системы | Событие о клиенте: `{"eventType": "CLIENT_CREATED", "clientId": 17, "login": "…", "tariff": "INVESTOR", "eventTime": "2026-10-13T14:05:12.345"}` |
| `invest.money-orders` | сервис → другие системы | Статус денежного поручения, при каждой смене статуса: `{"eventType": "MONEY_ORDER_STATUS", "orderId": 42, "agreementId": 9, "agreementNumber": "БД-1234567", "type": "REFILL", "amount": "1000.00", "status": "EXECUTED", "source": "CFT", "eventTime": "…"}`. `source` — откуда поручение: `API` или `CFT` |
| `cft.incoming-payments` | ЦФТ → сервис | Поступление денег на брокерский счёт: `{"PaymentId": "…", "AgreementNumber": "БД-1234567", "Amount": "1000.00", "Currency": "RUB", "PaymentTime": "…"}`. Ключ сообщения — номер договора. Сервис зачисляет поступление сразу, без задержки, и создаёт исполненное поручение на пополнение. ЦФТ может доставить одно и то же поступление повторно — сервис узнаёт его по `PaymentId` и второй раз не зачисляет |
| `sofr.get-tax-report-info-request` | сервис → СОФР | Запрос справки НДФЛ: `{"GetTaxReportInfoReq": {"RequestId": "…", "ClientId": 17, "AgreementNumbers": ["БД-1234567"], "TaxPeriod": "2025", "RequestTime": "…"}}`. В `AgreementNumbers` — все брокерские договоры клиента |
| `sofr.get-tax-report-info-response` | СОФР → сервис | Справка готова: `{"RequestId": "…", "Status": "READY", "FileName": "…"}`. Сервис переводит заявку с этим `RequestId` в статус `READY` |

На тестовом стенде ЦФТ и СОФР нет, поэтому их сообщения тесты отправляют сами.
