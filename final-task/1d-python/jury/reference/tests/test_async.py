from decimal import Decimal

import pytest

from support.api import require
from support.data import pair, unique_key
from support.polling import wait_final
from tests.checks import balances, clock, completed

pytestmark = pytest.mark.global_state


def test_processing_on_pause_completes_after_resume(global_stand, db):
    api = global_stand
    source, destination = pair(api)
    api.post("/api/test/consumers/accounting/pause")
    created = require(api.transfer(source["accountNumber"], destination["accountNumber"],
                                   Decimal("100.00"), unique_key()), 202)
    assert api.get(f"/api/v1/transfers/{created['transferId']}")["status"] == "PROCESSING"
    balances(api, source, destination, "999900.00", "0.00")
    assert len(db.postings(created["transferId"])) == 1
    api.post("/api/test/consumers/accounting/resume")
    assert wait_final(api, created["transferId"])["status"] == "COMPLETED"
    balances(api, source, destination, "999900.00", "100.00")
    postings = db.postings(created["transferId"])
    assert len(postings) == 2
    assert sum(p["direction"] == "CREDIT" for p in postings) == 1


def test_failed_transfer_refunds_amount_and_commission(global_stand, db):
    api = global_stand
    clock(api, "2051-08-15T12:00:00+03:00")
    source, destination = pair(api, own=False)
    completed(api, source, destination, "100000.00")
    balances(api, source, destination, "900000.00", "100000.00")
    api.post("/api/test/consumers/accounting/pause")
    created = require(api.transfer(source["accountNumber"], destination["accountNumber"],
                                   Decimal("40000.00"), unique_key()), 202)
    assert created["commission"] == Decimal("400.00")
    balances(api, source, destination, "859600.00", "100000.00")
    api.put(f"/api/test/accounts/{destination['accountNumber']}/status", {"status": "CLOSED"})
    api.post("/api/test/consumers/accounting/resume")
    final = wait_final(api, created["transferId"])
    assert final["status"] == "FAILED"
    assert final["failReason"] == "RECIPIENT_ACCOUNT_CLOSED"
    balances(api, source, destination, "900000.00", "100000.00")
    postings = db.postings(created["transferId"])
    assert len(postings) == 3
    assert {(p["account_number"], p["direction"], p["posting_type"], p["amount"]) for p in postings} == {
        (source["accountNumber"], "DEBIT", "AMOUNT", Decimal("40000.00")),
        (source["accountNumber"], "DEBIT", "COMMISSION", Decimal("400.00")),
        (source["accountNumber"], "CREDIT", "REFUND", Decimal("40400.00")),
    }
