from decimal import Decimal

from support.api import body, require
from support.data import unique_key
from support.polling import wait_final


def completed(api, source, destination, amount, key=None):
    created = require(api.transfer(source["accountNumber"], destination["accountNumber"],
                                   Decimal(amount), key or unique_key()), 202)
    result = wait_final(api, created["transferId"])
    assert result["status"] == "COMPLETED", result
    return result


def balances(api, source, destination, source_balance, destination_balance):
    assert api.get(f"/api/v1/accounts/{source['accountNumber']}")["balance"] == Decimal(source_balance)
    assert api.get(f"/api/v1/accounts/{destination['accountNumber']}")["balance"] == Decimal(destination_balance)


def rejected(response, status, code, api, db, source, destination):
    result = require(response, status)
    assert result["code"] in ({code} if isinstance(code, str) else code), result
    assert result["message"]
    balances(api, source, destination, str(source["balance"]), str(destination["balance"]))
    assert db.select("SELECT COUNT(*) AS n FROM transfers WHERE from_account = %s OR from_account = %s",
                     (source["accountNumber"], destination["accountNumber"]))[0]["n"] == 0
    assert db.select("SELECT COUNT(*) AS n FROM postings WHERE transfer_id IS NOT NULL "
                     "AND (account_number = %s OR account_number = %s)",
                     (source["accountNumber"], destination["accountNumber"]))[0]["n"] == 0


def limits(api, source):
    return api.get(f"/api/v1/clients/{source['clientId']}/limits")


def clock(api, now):
    api.put("/api/test/clock", {"now": now})


def exhaust_threshold(api, source, destination):
    clock(api, "2051-03-14T12:00:00+03:00")
    initial = completed(api, source, destination, "100000.00")
    assert initial["commission"] == Decimal("0.00")
    clock(api, "2051-03-15T12:00:00+03:00")
