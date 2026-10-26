"""Проверка ключа: воспроизводит каждый заложенный дефект стенда.

Запуск (стенд должен быть запущен, данные стенда будут сброшены):
    pip install -r requirements.txt
    python verify_defects.py            # все функциональные дефекты
    python verify_defects.py O1 A2      # выборочно
    python verify_defects.py controls   # контроль: то, что должно работать по ТЗ

Нагрузочные дефекты Н1–Н3 проверяет load_check.py.
"""
import json
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pika
import requests

BASE = "http://localhost:18400"
AMQP = pika.URLParameters("amqp://guest:guest@localhost:5672/%2F")


def call(method, path, body=None, key=None):
    headers = {"Content-Type": "application/json"}
    if method == "POST" and path == "/api/v1/transfers":
        headers["Idempotency-Key"] = key or str(uuid.uuid4())
    r = requests.request(method, BASE + path, data=None if body is None else json.dumps(body), headers=headers,
                         timeout=30)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, r.text


def new_account(balance="1000000.00", client_id=None, status="ACTIVE"):
    body = {"balance": float(balance), "status": status}
    if client_id:
        body["clientId"] = client_id
    code, acc = call("POST", "/api/test/accounts", body)
    assert code == 201, acc
    return acc


def transfer(src, dst, amount, key=None):
    return call("POST", "/api/v1/transfers", {"fromAccount": src, "toAccount": dst, "amount": amount}, key)


def balance(number):
    return Decimal(str(call("GET", f"/api/v1/accounts/{number}")[1]["balance"]))


def wait_final(transfer_id, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        t = call("GET", f"/api/v1/transfers/{transfer_id}")[1]
        if t["status"] != "PROCESSING":
            return t
        time.sleep(0.1)
    return call("GET", f"/api/v1/transfers/{transfer_id}")[1]


def reset():
    assert call("POST", "/api/test/reset")[0] == 200


# --- общие --------------------------------------------------------------------------------------

def o1():
    """Перевод, ровно исчерпывающий дневной лимит 150 000, отклоняется."""
    a, b = new_account(), new_account()
    code, body = transfer(a["accountNumber"], b["accountNumber"], 150000.00)
    return code == 422 and body["code"] == "DAILY_LIMIT_EXCEEDED", f"{code} {body}"


def o2():
    """Перевод через бесплатный порог: комиссия со всей суммы вместо превышения."""
    a, b = new_account(), new_account()
    transfer(a["accountNumber"], b["accountNumber"], 90000.00)
    code, body = transfer(a["accountNumber"], b["accountNumber"], 20000.00)
    return Decimal(str(body["commission"])) == Decimal("200.00"), f"комиссия {body['commission']}, по ТЗ 100.00"


def o3():
    """Округление комиссии вниз вместо математического."""
    a, b = new_account(), new_account()
    transfer(a["accountNumber"], b["accountNumber"], 100000.00)
    code, body = transfer(a["accountNumber"], b["accountNumber"], 3456.78)
    return Decimal(str(body["commission"])) == Decimal("34.56"), f"комиссия {body['commission']}, по ТЗ 34.57"


def o4():
    """Зачисление на заблокированный счёт запрещено, хотя по ТЗ разрешено."""
    a = new_account()
    blocked = new_account(status="BLOCKED")
    code, body = transfer(a["accountNumber"], blocked["accountNumber"], 1000.00)
    return code == 422 and body["code"] == "ACCOUNT_BLOCKED", f"{code} {body}"


def failed_transfer(amount=120000.00):
    """Готовит перевод в статусе FAILED: учёт на паузе, получатель закрыт до обработки."""
    a, b = new_account(), new_account()
    before = balance(a["accountNumber"])
    call("POST", "/api/test/consumers/accounting/pause")
    code, t = transfer(a["accountNumber"], b["accountNumber"], amount)
    call("PUT", f"/api/test/accounts/{b['accountNumber']}/status", {"status": "CLOSED"})
    call("POST", "/api/test/consumers/accounting/resume")
    t = wait_final(t["transferId"])
    time.sleep(0.5)
    return a, b, before, t


def o5():
    """Отчёт об обороте учитывает FAILED-переводы."""
    reset()
    a, b = new_account(), new_account()
    _, ok = transfer(a["accountNumber"], b["accountNumber"], 1000.00)
    wait_final(ok["transferId"])
    _, _, _, failed = failed_transfer(5000.00)
    rep = call("GET", "/api/v1/reports/turnover")[1]
    return rep["transfersCount"] == 2 and Decimal(str(rep["totalAmount"])) == Decimal("6000.00"), \
        f"отчёт {rep}, по ТЗ 1 перевод на 1000.00; статус второго {failed['status']}"


# --- ручной -------------------------------------------------------------------------------------

def r1():
    """Сутки для лимита считаются по UTC: после полуночи МСК лимит ещё не обнулился."""
    a, b = new_account(), new_account()
    call("PUT", "/api/test/clock", {"now": "2027-03-15T23:30:00+03:00"})
    c1, _ = transfer(a["accountNumber"], b["accountNumber"], 140000.00)
    call("PUT", "/api/test/clock", {"now": "2027-03-16T00:30:00+03:00"})
    c2, body = transfer(a["accountNumber"], b["accountNumber"], 20000.00)
    call("DELETE", "/api/test/clock")
    return c1 == 202 and c2 == 422, f"23:30 → {c1}; 00:30 следующих суток → {c2} {body}"


def r2():
    """При FAILED возвращается только сумма, комиссия остаётся списанной."""
    a, b, before, t = failed_transfer()
    after = balance(a["accountNumber"])
    return t["status"] == "FAILED" and after == before - Decimal(str(t["commission"])), \
        f"было {before}, стало {after}, комиссия {t['commission']}, статус {t['status']}"


def r3():
    """Уведомление о неуспешном переводе сообщает «выполнен»."""
    a, b, before, t = failed_transfer(15000.00)
    time.sleep(0.5)
    client = call("GET", f"/api/v1/accounts/{a['accountNumber']}")[1]["clientId"]
    notes = call("GET", f"/api/v1/clients/{client}/notifications")[1]
    text = notes[0]["text"] if notes else ""
    return t["status"] == "FAILED" and "выполнен" in text and "не выполнен" not in text, text


# --- автоматизация ------------------------------------------------------------------------------

def a1():
    """Параллельные переводы с одного счёта: списания затирают друг друга."""
    src = new_account("1000.00")
    dst = new_account(client_id=src["clientId"])
    with ThreadPoolExecutor(10) as pool:
        results = list(pool.map(lambda _: transfer(src["accountNumber"], dst["accountNumber"], 600.00), range(10)))
    time.sleep(1.5)
    accepted = sum(1 for c, _ in results if c == 202)
    s, d = balance(src["accountNumber"]), balance(dst["accountNumber"])
    return accepted > 1, f"принято {accepted} из 10 по 600 при остатке 1000; источник {s}, получатель {d}"


def a2():
    """Повторная доставка TransferCreated зачисляет деньги второй раз."""
    conn = pika.BlockingConnection(AMQP)
    ch = conn.channel()
    q = ch.queue_declare("", exclusive=True).method.queue
    ch.queue_bind(q, "transfers", "transfer.created")
    a, b = new_account(), new_account()
    _, t = transfer(a["accountNumber"], b["accountNumber"], 1000.00)
    wait_final(t["transferId"])
    before = balance(b["accountNumber"])
    body = None
    for _ in range(50):
        method, props, raw = ch.basic_get(q, auto_ack=True)
        if raw and json.loads(raw)["transferId"] == t["transferId"]:
            body = raw
            break
        time.sleep(0.1)
    ch.basic_publish("transfers", "transfer.created", body,
                     pika.BasicProperties(content_type="application/json", delivery_mode=2))
    time.sleep(1.5)
    after = balance(b["accountNumber"])
    conn.close()
    return after - before == Decimal("1000.00"), f"получатель до повтора {before}, после {after}"


def a3():
    """Для части сумм с комиссией получатель недополучает 0,01 ₽."""
    a, b = new_account(), new_account()
    _, t = transfer(a["accountNumber"], b["accountNumber"], 100000.00)
    wait_final(t["transferId"])
    before = balance(b["accountNumber"])
    _, t = transfer(a["accountNumber"], b["accountNumber"], 7777.77)
    wait_final(t["transferId"])
    got = balance(b["accountNumber"]) - before
    return got == Decimal("7777.76"), f"перевод 7777.77 (комиссия {t['commission']}), зачислено {got}"


# --- бонус --------------------------------------------------------------------------------------

def b1():
    """Сообщение о неизвестном переводе крутится в очереди и блокирует обработку."""
    conn = pika.BlockingConnection(AMQP)
    ch = conn.channel()
    poison = {"eventId": str(uuid.uuid4()), "eventType": "TransferCreated", "transferId": str(uuid.uuid4()),
              "transferType": "OWN", "fromAccount": "40817810000000000011", "toAccount": "40817810000000000012",
              "amount": 10.00, "commission": 0.00, "totalDebited": 10.00, "currency": "RUB",
              "occurredAt": "2027-03-15T12:00:00+03:00"}
    ch.basic_publish("transfers", "transfer.created", json.dumps(poison).encode(),
                     pika.BasicProperties(content_type="application/json", delivery_mode=2))
    time.sleep(0.5)
    a, b = new_account(), new_account()
    _, t = transfer(a["accountNumber"], b["accountNumber"], 100.00)
    time.sleep(5)
    status = call("GET", f"/api/v1/transfers/{t['transferId']}")[1]["status"]
    dlq = ch.queue_declare("transfers.dlq", passive=True).method.message_count
    conn.close()
    reset()
    return status == "PROCESSING" and dlq == 0, f"обычный перевод через 5 с: {status}; в DLQ {dlq}"


# --- контроль: то, что по ТЗ работает и должно работать -----------------------------------------

def k1():
    """Повтор с тем же Idempotency-Key возвращает тот же перевод и не списывает повторно."""
    a, b = new_account(), new_account()
    key = str(uuid.uuid4())
    c1, t1 = transfer(a["accountNumber"], b["accountNumber"], 500.00, key)
    c2, t2 = transfer(a["accountNumber"], b["accountNumber"], 500.00, key)
    time.sleep(0.3)
    ok = c1 == 202 and c2 == 200 and t1["transferId"] == t2["transferId"] \
        and balance(a["accountNumber"]) == Decimal("999500.00")
    return ok, f"{c1}/{c2}, остаток {balance(a['accountNumber'])}"


def k2():
    """Границы суммы: 9.99 и 300000.01 и 3 знака — 400; 10.00 и 300000.00 (свои счета) — 202."""
    a = new_account("1000000.00")
    own = new_account(client_id=a["clientId"])
    codes = [transfer(a["accountNumber"], own["accountNumber"], x)[0] for x in (9.99, 10.00, 300000.00, 300000.01, 10.001)]
    return codes == [400, 202, 202, 400, 400], str(codes)


def k3():
    """Недостаточно средств — 422 INSUFFICIENT_FUNDS; лимит 149 999.99 — проходит."""
    a, b = new_account("100.00"), new_account()
    c1, body = transfer(a["accountNumber"], b["accountNumber"], 100.01)
    x, y = new_account(), new_account()
    c2, _ = transfer(x["accountNumber"], y["accountNumber"], 149999.99)
    return c1 == 422 and body["code"] == "INSUFFICIENT_FUNDS" and c2 == 202, f"{c1} {body.get('code')}, {c2}"


def k4():
    """Заблокированный счёт: на свой счёт можно, другому клиенту — 422; закрытый получатель — 422."""
    blocked = new_account(status="BLOCKED")
    own = new_account(client_id=blocked["clientId"])
    other = new_account()
    closed = new_account(status="CLOSED")
    c1 = transfer(blocked["accountNumber"], own["accountNumber"], 100.00)[0]
    c2, b2 = transfer(blocked["accountNumber"], other["accountNumber"], 100.00)
    c3, b3 = transfer(other["accountNumber"], closed["accountNumber"], 100.00)
    return (c1, c2, b2["code"], c3, b3["code"]) == (202, 422, "ACCOUNT_BLOCKED", 422, "ACCOUNT_CLOSED"), \
        f"{c1} {c2} {b2['code']} {c3} {b3['code']}"


def k5():
    """Комиссия: свои счета — 0 без лимита; после порога минимум 30 и 1 % с суммы."""
    a = new_account("2000000.00")
    own = new_account(client_id=a["clientId"])
    b = new_account()
    _, t0 = transfer(a["accountNumber"], own["accountNumber"], 250000.00)
    transfer(a["accountNumber"], b["accountNumber"], 100000.00)
    _, t1 = transfer(a["accountNumber"], b["accountNumber"], 1000.00)
    x, y = new_account(), new_account()
    call("PUT", "/api/test/clock", {"now": "2027-03-01T10:00:00+03:00"})
    transfer(x["accountNumber"], y["accountNumber"], 100000.00)
    call("PUT", "/api/test/clock", {"now": "2027-03-02T10:00:00+03:00"})
    _, t2 = transfer(x["accountNumber"], y["accountNumber"], 149000.00)
    call("DELETE", "/api/test/clock")
    got = (Decimal(str(t0["commission"])), Decimal(str(t1["commission"])), Decimal(str(t2["commission"])))
    return got == (Decimal("0"), Decimal("30"), Decimal("1490")) or got == (Decimal("0"), Decimal("30"), Decimal("1490.00")), str(got)


def k6():
    """Битое сообщение уходит в DLQ после 3 попыток."""
    conn = pika.BlockingConnection(AMQP)
    ch = conn.channel()
    before = ch.queue_declare("transfers.dlq", passive=True).method.message_count
    ch.basic_publish("transfers", "transfer.created", b"{not json", pika.BasicProperties(delivery_mode=2))
    time.sleep(1.5)
    after = ch.queue_declare("transfers.dlq", passive=True).method.message_count
    conn.close()
    return after == before + 1, f"DLQ: было {before}, стало {after}"


CONTROLS = {"K1": k1, "K2": k2, "K3": k3, "K4": k4, "K5": k5, "K6": k6}

CHECKS = {"O1": o1, "O2": o2, "O3": o3, "O4": o4, "O5": o5, "R1": r1, "R2": r2, "R3": r3,
          "A1": a1, "A2": a2, "A3": a3, "B1": b1}


def main():
    if sys.argv[1:] == ["controls"]:
        reset()
        bad = 0
        for name, fn in CONTROLS.items():
            try:
                ok, details = fn()
            except Exception as e:  # noqa: BLE001
                ok, details = False, f"ошибка проверки: {e!r}"
            bad += 0 if ok else 1
            print(f"{name}: {'ок' if ok else 'НЕ ТАК, КАК В ТЗ'} — {fn.__doc__.strip()}")
            print(f"    {details}")
        reset()
        sys.exit(1 if bad else 0)
    names = [n.upper() for n in sys.argv[1:]] or list(CHECKS)
    reset()
    failed = 0
    for name in names:
        try:
            ok, details = CHECKS[name]()
        except Exception as e:  # noqa: BLE001
            ok, details = False, f"ошибка проверки: {e!r}"
        failed += 0 if ok else 1
        print(f"{name}: {'воспроизводится' if ok else 'НЕ ВОСПРОИЗВОДИТСЯ'} — {CHECKS[name].__doc__.strip()}")
        print(f"    {details}")
    reset()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
