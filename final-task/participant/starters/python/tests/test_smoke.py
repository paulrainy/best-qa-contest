"""Пример: перевод между своими счетами через API, событие в брокере, проводки в БД."""
import time
import uuid
from decimal import Decimal

from stand import Events


def test_own_transfer_is_completed(api, channel, db):
    src = api.post("/api/test/accounts", {"balance": 1000.00}).json()
    dst = api.post("/api/test/accounts", {"clientId": src["clientId"], "balance": 0}).json()
    events = Events(channel)

    r = api.post("/api/v1/transfers", {"fromAccount": src["accountNumber"], "toAccount": dst["accountNumber"],
                                       "amount": 100.00}, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 202, r.text
    transfer_id = r.json()["transferId"]

    for _ in range(100):
        if api.get(f"/api/v1/transfers/{transfer_id}").json()["status"] == "COMPLETED":
            break
        time.sleep(0.1)
    else:
        raise AssertionError("перевод не завершился за 10 с")

    created = events.wait(lambda e: e["transferId"] == transfer_id and e["eventType"] == "TransferCreated")
    assert Decimal(str(created["amount"])) == Decimal("100.00")

    row = db.execute("SELECT SUM(amount) FROM postings WHERE transfer_id = %s AND direction = 'CREDIT'",
                     (transfer_id,)).fetchone()
    assert row[0] == Decimal("100.00")
