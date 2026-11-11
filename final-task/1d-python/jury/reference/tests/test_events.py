from datetime import datetime
from decimal import Decimal
from uuid import UUID

from support.amqp import Events
from support.api import require
from support.data import pair, unique_key
from support.polling import wait_final
from tests.checks import balances


def test_created_event_and_postings_match_own_transfer(api, db, channel):
    source, destination = pair(api, own=False)
    with Events.subscribe(channel, "transfer.created") as events:
        created = require(api.transfer(source["accountNumber"], destination["accountNumber"],
                                       Decimal("123.45"), unique_key()), 202)
        event = events.wait(created["transferId"], "TransferCreated")
    assert str(UUID(event["eventId"])) == event["eventId"]
    assert datetime.fromisoformat(event["occurredAt"]).utcoffset() is not None
    assert {key: event[key] for key in ("eventType", "transferId", "transferType", "fromAccount", "toAccount",
                                       "amount", "commission", "totalDebited", "currency")} == {
        "eventType": "TransferCreated", "transferId": created["transferId"], "transferType": "OTHER",
        "fromAccount": source["accountNumber"], "toAccount": destination["accountNumber"],
        "amount": Decimal("123.45"), "commission": Decimal("0.00"), "totalDebited": Decimal("123.45"),
        "currency": "RUB",
    }
    assert wait_final(api, created["transferId"])["status"] == "COMPLETED"
    postings = db.postings(created["transferId"])
    assert len(postings) == 2
    assert {(p["account_number"], p["direction"], p["posting_type"], p["amount"]) for p in postings} == {
        (source["accountNumber"], "DEBIT", "AMOUNT", Decimal("123.45")),
        (destination["accountNumber"], "CREDIT", "AMOUNT", Decimal("123.45")),
    }
    balances(api, source, destination, "999876.55", "123.45")
