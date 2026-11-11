from types import SimpleNamespace

import pytest

from support.db import Db


def test_db_connection_closes_when_scenario_raises():
    connection = SimpleNamespace(closed=False)

    def close():
        connection.closed = True

    connection.close = close
    with pytest.raises(ValueError, match="scenario failure"):
        with Db(SimpleNamespace(database={}), connect=lambda **kwargs: connection):
            raise ValueError("scenario failure")
    assert connection.closed is True


def test_db_rejects_write_before_sending_it():
    with Db(SimpleNamespace(database={}), connect=lambda **kwargs: SimpleNamespace(close=lambda: None)) as db:
        with pytest.raises(ValueError, match="SELECT"):
            db.select("DELETE FROM transfers")
