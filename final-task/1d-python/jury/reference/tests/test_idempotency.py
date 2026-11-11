from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from support.api import require
from support.data import pair, unique_key
from tests.checks import balances, clock, completed


def test_same_body_returns_original_without_second_debit(api, db):
    source, destination = pair(api)
    key = unique_key()
    first = completed(api, source, destination, "100", key)
    repeat = require(api.transfer(source["accountNumber"], destination["accountNumber"], Decimal("100.00"), key), 200)
    assert repeat["transferId"] == first["transferId"]
    assert repeat["status"] == "COMPLETED"
    balances(api, source, destination, "999900.00", "100.00")
    assert db.select("SELECT COUNT(*) AS n FROM transfers WHERE idempotency_key = %s", (key,))[0]["n"] == 1
    assert len(db.postings(first["transferId"])) == 2


def test_different_body_returns_409(api, db):
    source, destination = pair(api)
    key = unique_key()
    first = completed(api, source, destination, "100.00", key)
    result = require(api.transfer(source["accountNumber"], destination["accountNumber"], Decimal("101.00"), key), 409)
    assert result["code"] == "IDEMPOTENCY_CONFLICT"
    balances(api, source, destination, "999900.00", "100.00")
    assert len(db.postings(first["transferId"])) == 2
    assert db.select("SELECT COUNT(*) AS n FROM transfers WHERE idempotency_key = %s", (key,))[0]["n"] == 1


def test_key_is_global_across_clients(api, db):
    source, destination = pair(api)
    other_source, other_destination = pair(api)
    key = unique_key()
    completed(api, source, destination, "100.00", key)
    result = require(api.transfer(other_source["accountNumber"], other_destination["accountNumber"],
                                  Decimal("100.00"), key), 409)
    assert result["code"] == "IDEMPOTENCY_CONFLICT"
    balances(api, other_source, other_destination, "1000000.00", "0.00")
    assert db.select("SELECT COUNT(*) AS n FROM transfers WHERE from_account = %s",
                     (other_source["accountNumber"],))[0]["n"] == 0


@pytest.mark.global_state
def test_expired_key_creates_new_operation(global_stand, db):
    api = global_stand
    source, destination = pair(api)
    clock(api, "2051-07-15T12:00:00+03:00")
    key = unique_key()
    first = completed(api, source, destination, "100.00", key)
    expiry = datetime.fromisoformat(first["createdAt"]) + timedelta(hours=24, minutes=1)
    clock(api, expiry.isoformat())
    assert datetime.fromisoformat(api.get("/api/test/clock")["now"]) >= expiry
    second = completed(api, source, destination, "100.00", key)
    assert second["transferId"] != first["transferId"]
    assert api.get(f"/api/v1/transfers/{first['transferId']}")["status"] == "COMPLETED"
    balances(api, source, destination, "999800.00", "200.00")
    assert db.select("SELECT COUNT(*) AS n FROM transfers WHERE idempotency_key = %s", (key,))[0]["n"] == 2
    assert len(db.postings(first["transferId"])) == len(db.postings(second["transferId"])) == 2
