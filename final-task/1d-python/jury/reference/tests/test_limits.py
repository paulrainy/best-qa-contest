from decimal import Decimal

import pytest

from support.api import require
from support.data import pair, unique_key
from support.polling import wait_final
from tests.checks import balances, clock, completed, exhaust_threshold, limits

pytestmark = pytest.mark.global_state


@pytest.mark.parametrize("amount,accepted,source_balance,destination_balance", [
    ("149999.99", True, "748500.01", "249999.99"),
    ("150000.00", True, "748500.00", "250000.00"),
    ("150000.01", False, "900000.00", "100000.00"),
], ids=["below", "exact", "above"])
def test_daily_limit_boundaries(global_stand, db, amount, accepted, source_balance, destination_balance):
    api = global_stand
    source, destination = pair(api, own=False)
    exhaust_threshold(api, source, destination)
    response = api.transfer(source["accountNumber"], destination["accountNumber"], Decimal(amount), unique_key())
    if accepted:
        final = wait_final(api, require(response, 202)["transferId"])
        assert final["status"] == "COMPLETED"
        assert final["commission"] == Decimal("1500.00")
    else:
        assert require(response, 422)["code"] == "DAILY_LIMIT_EXCEEDED"
        assert db.select("SELECT COUNT(*) AS n FROM transfers WHERE from_account = %s",
                         (source["accountNumber"],))[0]["n"] == 1
    balances(api, source, destination, source_balance, destination_balance)
    assert limits(api, source)["dailyUsed"] == (Decimal(amount) if accepted else Decimal("0.00"))


def test_moscow_midnight_resets_daily_limit(global_stand):
    api = global_stand
    source, destination = pair(api, own=False)
    clock(api, "2051-04-15T23:59:00+03:00")
    first = completed(api, source, destination, "150000.00")
    assert first["commission"] == Decimal("500.00")
    assert limits(api, source)["dailyUsed"] == Decimal("150000.00")
    clock(api, "2051-04-16T00:01:00+03:00")
    assert limits(api, source)["dailyUsed"] == Decimal("0.00")
    second = completed(api, source, destination, "10.00")
    assert second["commission"] == Decimal("30.00")
    assert limits(api, source)["dailyUsed"] == Decimal("10.00")
    balances(api, source, destination, "849460.00", "150010.00")


def test_calendar_month_resets_free_threshold(global_stand):
    api = global_stand
    source, destination = pair(api, own=False)
    clock(api, "2051-04-30T23:59:00+03:00")
    completed(api, source, destination, "100000.00")
    assert limits(api, source)["monthUsed"] == Decimal("100000.00")
    clock(api, "2051-05-01T00:01:00+03:00")
    assert limits(api, source)["monthUsed"] == Decimal("0.00")
    assert limits(api, source)["monthFreeRemaining"] == Decimal("100000.00")
    assert completed(api, source, destination, "100.00")["commission"] == Decimal("0.00")
    balances(api, source, destination, "899900.00", "100100.00")


def test_failed_transfer_releases_usage(global_stand):
    api = global_stand
    source, destination = pair(api, own=False)
    clock(api, "2051-06-15T12:00:00+03:00")
    completed(api, source, destination, "100000.00")
    api.post("/api/test/consumers/accounting/pause")
    pending = require(api.transfer(source["accountNumber"], destination["accountNumber"],
                                   Decimal("40000.00"), unique_key()), 202)
    assert limits(api, source)["dailyUsed"] == Decimal("140000.00")
    assert limits(api, source)["monthUsed"] == Decimal("140000.00")
    api.put(f"/api/test/accounts/{destination['accountNumber']}/status", {"status": "CLOSED"})
    api.post("/api/test/consumers/accounting/resume")
    assert wait_final(api, pending["transferId"])["status"] == "FAILED"
    assert limits(api, source)["dailyUsed"] == Decimal("100000.00")
    assert limits(api, source)["monthUsed"] == Decimal("100000.00")
    api.put(f"/api/test/accounts/{destination['accountNumber']}/status", {"status": "ACTIVE"})
    assert completed(api, source, destination, "50000.00")["commission"] == Decimal("500.00")
    assert limits(api, source)["dailyUsed"] == Decimal("150000.00")
    balances(api, source, destination, "849500.00", "150000.00")
