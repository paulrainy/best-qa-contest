from decimal import Decimal

import pytest

from support.api import require
from support.data import pair, unique_key
from support.polling import wait_final, wait_for
from tests.checks import clock, completed


def notification(api, client_id, transfer_id):
    found = wait_for(lambda: [n for n in api.get(f"/api/v1/clients/{client_id}/notifications")
                              if n["transferId"] == transfer_id],
                     lambda rows: len(rows) > 0, f"Уведомление {transfer_id}")
    assert len(found) == 1
    return found[0]


@pytest.mark.global_state
def test_completed_notification_has_correct_recipient_and_format(global_stand, db):
    api = global_stand
    clock(api, "2051-09-15T12:00:00+03:00")
    source, destination = pair(api, own=False)
    completed(api, source, destination, "90000.00")
    final = completed(api, source, destination, "20000.00")
    expected = f"Перевод 20 000,00 ₽ на счёт {destination['accountNumber']} выполнен. Комиссия 100,00 ₽."
    note = notification(api, source["clientId"], final["transferId"])
    assert note["text"] == expected
    assert api.get(f"/api/v1/clients/{destination['clientId']}/notifications") == []
    rows = db.select("SELECT * FROM notifications WHERE transfer_id = %s", (final["transferId"],))
    assert len(rows) == 1
    assert rows[0]["client_id"] == source["clientId"]
    assert rows[0]["text"] == expected


@pytest.mark.global_state
def test_failed_notification_reports_failure(global_stand, db):
    api = global_stand
    clock(api, "2051-10-15T12:00:00+03:00")
    source, destination = pair(api, own=False)
    completed(api, source, destination, "100000.00")
    api.post("/api/test/consumers/accounting/pause")
    pending = require(api.transfer(source["accountNumber"], destination["accountNumber"],
                                   Decimal("40000.00"), unique_key()), 202)
    api.put(f"/api/test/accounts/{destination['accountNumber']}/status", {"status": "CLOSED"})
    api.post("/api/test/consumers/accounting/resume")
    assert wait_final(api, pending["transferId"])["status"] == "FAILED"
    expected = (f"Перевод 40 000,00 ₽ на счёт {destination['accountNumber']} не выполнен. "
                f"Средства 40 400,00 ₽ возвращены на счёт {source['accountNumber']}.")
    assert notification(api, source["clientId"], pending["transferId"])["text"] == expected
    assert api.get(f"/api/v1/clients/{destination['clientId']}/notifications") == []
    rows = db.select("SELECT * FROM notifications WHERE transfer_id = %s", (pending["transferId"],))
    assert len(rows) == 1
    assert rows[0]["client_id"] == source["clientId"]
    assert rows[0]["text"] == expected


def test_unknown_client_is_404_and_existing_without_notifications_is_empty(api):
    client = api.create_account()["clientId"]
    assert api.get(f"/api/v1/clients/{client}/notifications") == []
    unknown = "ABSENT-" + unique_key()
    assert require(api.request("GET", f"/api/v1/clients/{unknown}/notifications"), 404)["code"] == "CLIENT_NOT_FOUND"
