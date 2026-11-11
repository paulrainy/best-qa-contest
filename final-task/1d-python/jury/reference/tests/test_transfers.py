from decimal import Decimal

from support.amqp import Events
from support.api import require
from support.data import pair, unique_key
from support.polling import wait_final


def test_readiness_and_read_only_connections(api, db):
    assert api.get("/api/v1/health")["status"] == "UP"
    assert db.select("SELECT 1 AS ready")[0]["ready"] == 1


def test_own_transfer_completes_with_exact_balances(api, db, channel):
    source, destination = pair(api)
    with Events.subscribe(channel, "transfer.created") as events:
        created = require(api.transfer(source["accountNumber"], destination["accountNumber"],
                                       Decimal("100.00"), unique_key()), 202)
        event = events.wait(created["transferId"], "TransferCreated")
    final = wait_final(api, created["transferId"])
    assert final["status"] == "COMPLETED"
    assert final["transferType"] == "OWN"
    assert final["amount"] == Decimal("100.00")
    assert final["commission"] == Decimal("0.00")
    assert event["amount"] == Decimal("100.00")
    assert api.get(f"/api/v1/accounts/{source['accountNumber']}")["balance"] == Decimal("999900.00")
    assert api.get(f"/api/v1/accounts/{destination['accountNumber']}")["balance"] == Decimal("100.00")
    postings = db.postings(final["transferId"])
    assert {(p["account_number"], p["direction"], p["posting_type"], p["amount"]) for p in postings} == {
        (source["accountNumber"], "DEBIT", "AMOUNT", Decimal("100.00")),
        (destination["accountNumber"], "CREDIT", "AMOUNT", Decimal("100.00")),
    }
    assert len(postings) == 2
