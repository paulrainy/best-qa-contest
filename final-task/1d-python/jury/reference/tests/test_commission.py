from decimal import Decimal

import pytest

from support.data import pair
from tests.checks import balances, clock, completed, exhaust_threshold

pytestmark = pytest.mark.global_state


def test_threshold_crossing_charges_only_excess(global_stand):
    api = global_stand
    clock(api, "2051-03-15T12:00:00+03:00")
    source, destination = pair(api, own=False)
    first = completed(api, source, destination, "90000.00")
    assert first["commission"] == Decimal("0.00")
    crossing = completed(api, source, destination, "20000.00")
    assert crossing["commission"] == Decimal("100.00")
    balances(api, source, destination, "889900.00", "110000.00")


@pytest.mark.parametrize("amount,commission,source_balance,destination_balance", [
    ("10.00", "30.00", "899960.00", "100010.00"),
    ("3456.78", "34.57", "896508.65", "103456.78"),
    ("3000.50", "30.01", "896969.49", "103000.50"),
    ("150000.00", "1500.00", "748500.00", "250000.00"),
], ids=["minimum", "half-up", "half-up-tie", "maximum"])
def test_minimum_half_up_and_maximum_after_threshold(global_stand, amount, commission,
                                                    source_balance, destination_balance):
    api = global_stand
    source, destination = pair(api, own=False)
    exhaust_threshold(api, source, destination)
    final = completed(api, source, destination, amount)
    assert final["commission"] == Decimal(commission)
    balances(api, source, destination, source_balance, destination_balance)
