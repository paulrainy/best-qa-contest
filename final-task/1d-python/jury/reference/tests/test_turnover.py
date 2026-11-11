from datetime import date, timedelta
from decimal import Decimal

import pytest

from support.api import require
from support.data import pair, unique_key
from support.polling import wait_final
from tests.checks import clock, completed


@pytest.mark.global_state
def test_turnover_includes_only_completed_on_selected_moscow_date(global_stand, db):
    api = global_stand
    first_day = date(2055, 1, 1)
    for offset in range(200):
        day_a = first_day + timedelta(days=offset * 2)
        day_b = day_a + timedelta(days=1)
        reports = [api.get(f"/api/v1/reports/turnover?date={d}") for d in (day_a, day_b)]
        if all(r["transfersCount"] == 0 for r in reports):
            break
    else:
        pytest.fail("Нет двух свободных дат для изолированной сверки оборота")
    clock(api, f"{day_a}T23:59:00+03:00")
    source, destination = pair(api)
    done_a = completed(api, source, destination, "100.00")
    api.post("/api/test/consumers/accounting/pause")
    cross = require(api.transfer(source["accountNumber"], destination["accountNumber"],
                                 Decimal("200.00"), unique_key()), 202)
    failed_source, failed_destination = pair(api)
    failed = require(api.transfer(failed_source["accountNumber"], failed_destination["accountNumber"],
                                  Decimal("40.00"), unique_key()), 202)
    api.put(f"/api/test/accounts/{failed_destination['accountNumber']}/status", {"status": "CLOSED"})
    clock(api, f"{day_b}T00:01:00+03:00")
    api.post("/api/test/consumers/accounting/resume")
    assert wait_final(api, cross["transferId"])["status"] == "COMPLETED"
    assert wait_final(api, failed["transferId"])["status"] == "FAILED"
    api.post("/api/test/consumers/accounting/pause")
    pending = require(api.transfer(source["accountNumber"], destination["accountNumber"],
                                   Decimal("300.00"), unique_key()), 202)
    assert api.get(f"/api/v1/transfers/{pending['transferId']}")["status"] == "PROCESSING"
    for day, expected_amount, own_id in ((day_a, "100.00", done_a["transferId"]),
                                        (day_b, "200.00", cross["transferId"])):
        report = api.get(f"/api/v1/reports/turnover?date={day}")
        assert report == {"date": str(day), "transfersCount": 1,
                          "totalAmount": Decimal(expected_amount), "totalCommission": Decimal("0.00")}
        rows = db.select("SELECT transfer_id, amount, commission FROM transfers WHERE status = 'COMPLETED' "
                         "AND completed_at >= %s AND completed_at < %s",
                         (f"{day}T00:00:00+03:00", f"{day + timedelta(days=1)}T00:00:00+03:00"))
        assert len(rows) == 1
        assert str(rows[0]["transfer_id"]) == own_id
        assert rows[0]["amount"] == Decimal(expected_amount)
        assert rows[0]["commission"] == Decimal("0.00")
    assert cross["createdAt"].startswith(str(day_a))
    api.post("/api/test/consumers/accounting/resume")
    assert wait_final(api, pending["transferId"])["status"] == "COMPLETED"
