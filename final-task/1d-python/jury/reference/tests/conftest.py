import pytest

from support.amqp import channel_connection
from support.api import Api
from support.data import global_scope
from support.db import Db


@pytest.fixture
def api(stand_config, pytestconfig):
    with Api(stand_config, trace=pytestconfig.getoption("--http-log")) as client:
        yield client


@pytest.fixture
def db(stand_config):
    with Db(stand_config) as connection:
        yield connection


@pytest.fixture
def channel(stand_config):
    with channel_connection(stand_config) as connection:
        yield connection


@pytest.fixture
def global_stand(api):
    with global_scope(api):
        yield api
