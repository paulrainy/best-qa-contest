from contextlib import contextmanager
from decimal import Decimal
from uuid import uuid4


@contextmanager
def global_scope(api):
    try:
        yield api
    finally:
        errors = []
        for action in (lambda: api.post("/api/test/consumers/accounting/resume"),
                       lambda: api.post("/api/test/consumers/notifications/resume"),
                       lambda: api.delete("/api/test/clock")):
            try:
                action()
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise ExceptionGroup("Не удалось полное восстановление стенда", errors)


def unique_key():
    return f"python-{uuid4()}"


def pair(api, *, own=True, balance=Decimal("1000000.00"),
         source_status="ACTIVE", destination_status="ACTIVE"):
    source = api.create_account(balance=balance, status=source_status)
    destination = api.create_account(balance=Decimal("0.00"),
                                     client_id=source["clientId"] if own else None,
                                     status=destination_status)
    return source, destination
