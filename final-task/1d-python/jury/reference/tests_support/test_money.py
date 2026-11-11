import json
from decimal import Decimal

from support.api import encode_json


def test_decimal_is_sent_as_exact_json_number():
    body = encode_json({"amount": Decimal("1234567890123456.01"), "note": "счёт"})
    decoded = json.loads(body, parse_float=Decimal)
    assert decoded["amount"] == Decimal("1234567890123456.01")
    assert isinstance(decoded["amount"], Decimal)
    assert decoded["note"] == "счёт"
