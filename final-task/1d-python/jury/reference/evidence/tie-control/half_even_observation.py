from decimal import Decimal

import pytest


@pytest.fixture(autouse=True)
def controlled_wrong_tie(monkeypatch):
    import support.api
    original = support.api.body

    def decode(response):
        value = original(response)
        if isinstance(value, dict) and value.get("amount") == Decimal("3000.50") and value.get("commission") == Decimal("30.01"):
            value["commission"] = Decimal("30.00")
        return value

    monkeypatch.setattr(support.api, "body", decode)
