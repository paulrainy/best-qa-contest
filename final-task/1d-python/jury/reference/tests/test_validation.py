from decimal import Decimal
from itertools import product

import pytest

from support.api import require
from support.data import pair, unique_key
from support.polling import wait_final
from tests.checks import balances, rejected


@pytest.mark.parametrize("amount,status", [("9.99", 400), ("10.00", 202),
                                          ("300000.00", 202), ("300000.01", 400), ("10.001", 400)],
                         ids=["below", "minimum", "maximum", "above", "precision"])
def test_amount_boundaries(api, db, amount, status):
    source, destination = pair(api)
    response = api.transfer(source["accountNumber"], destination["accountNumber"], Decimal(amount), unique_key())
    if status == 400:
        rejected(response, 400, "VALIDATION_ERROR", api, db, source, destination)
    else:
        transfer = wait_final(api, require(response, 202)["transferId"])
        assert transfer["status"] == "COMPLETED"
        assert transfer["commission"] == Decimal("0.00")
        balances(api, source, destination, str(Decimal("1000000.00") - Decimal(amount)), amount)


@pytest.mark.parametrize("variant", ["missing-source", "missing-destination", "missing-amount",
                                     "source-format", "destination-format", "amount-string", "malformed-json"])
def test_invalid_payload_leaves_money_untouched(api, db, variant):
    source, destination = pair(api)
    payload = {"fromAccount": source["accountNumber"], "toAccount": destination["accountNumber"], "amount": 100}
    if variant.startswith("missing-"):
        del payload[{"missing-source": "fromAccount", "missing-destination": "toAccount",
                     "missing-amount": "amount"}[variant]]
    elif variant == "source-format":
        payload["fromAccount"] = "123"
    elif variant == "destination-format":
        payload["toAccount"] = "not-an-account"
    elif variant == "amount-string":
        payload["amount"] = "100.00"
    response = api.request("POST", "/api/v1/transfers", payload, key=unique_key(),
                           raw="{" if variant == "malformed-json" else None)
    rejected(response, 400, "VALIDATION_ERROR", api, db, source, destination)


@pytest.mark.parametrize("side", ["source", "destination"])
def test_unknown_account_is_404(api, db, side):
    source, destination = pair(api)
    response = api.transfer("99999999999999999999" if side == "source" else source["accountNumber"],
                             "99999999999999999999" if side == "destination" else destination["accountNumber"],
                             Decimal("100.00"), unique_key())
    rejected(response, 404, "ACCOUNT_NOT_FOUND", api, db, source, destination)


@pytest.mark.parametrize("key", [None, "x" * 101], ids=["missing", "too-long"])
def test_invalid_key_is_400(api, db, key):
    source, destination = pair(api)
    rejected(api.transfer(source["accountNumber"], destination["accountNumber"], Decimal("100.00"), key),
             400, "VALIDATION_ERROR", api, db, source, destination)


STATUSES = list(product([True, False], ["ACTIVE", "BLOCKED", "CLOSED"], ["ACTIVE", "BLOCKED", "CLOSED"]))


@pytest.mark.parametrize("own,src_status,dst_status", STATUSES,
                         ids=[f"{'OWN' if own else 'OTHER'}-{src}-{dst}" for own, src, dst in STATUSES])
def test_account_status_matrix(api, db, own, src_status, dst_status):
    source, destination = pair(api, own=own, source_status=src_status, destination_status=dst_status)
    response = api.transfer(source["accountNumber"], destination["accountNumber"], Decimal("100.00"), unique_key())
    if src_status == "ACTIVE" and dst_status != "CLOSED":
        transfer = wait_final(api, require(response, 202)["transferId"])
        assert transfer["status"] == "COMPLETED"
        assert transfer["transferType"] == ("OWN" if own else "OTHER")
        balances(api, source, destination, "999900.00", "100.00")
        assert len(db.postings(transfer["transferId"])) == 2
    else:
        # ТЗ не задаёт приоритет двух одновременно нарушенных правил.
        code = {"ACCOUNT_BLOCKED", "ACCOUNT_CLOSED"} if src_status == "BLOCKED" and dst_status == "CLOSED" else (
            "ACCOUNT_BLOCKED" if src_status == "BLOCKED" else "ACCOUNT_CLOSED")
        rejected(response, 422, code, api, db, source, destination)


def test_self_transfer_is_validation_error(api, db):
    source, destination = pair(api)
    rejected(api.transfer(source["accountNumber"], source["accountNumber"], Decimal("100.00"), unique_key()),
             400, "VALIDATION_ERROR", api, db, source, destination)
