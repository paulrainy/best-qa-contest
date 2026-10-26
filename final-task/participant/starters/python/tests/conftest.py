import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import stand  # noqa: E402


@pytest.fixture(scope="session")
def api():
    return stand.Api()


@pytest.fixture
def channel():
    conn = stand.amqp()
    ch = conn.channel()
    yield ch
    conn.close()


@pytest.fixture(scope="session")
def db():
    conn = stand.db()
    yield conn
    conn.close()
