import pytest
from hamcrest import assert_that, is_

from framework.api.invest_api import InvestApi
from invest.db.invest_db import InvestDb
from invest.steps.clients import create_client, login_client, open_agreement

BACKOFFICE_LOGIN = 'bo_operator1'
BACKOFFICE_PASSWORD = 'Oper1#Playground'


@pytest.fixture(scope='session')
def invest_api():
    return InvestApi()


@pytest.fixture(scope='session')
def invest_db():
    return InvestDb()


@pytest.fixture(scope='session')
def backoffice_token(invest_api):
    response = invest_api.backoffice_login(BACKOFFICE_LOGIN, BACKOFFICE_PASSWORD)
    assert_that(response.status_code, is_(200), f'Не удалось войти в бэк-офис: {response.text}')
    return response.json()['token']


@pytest.fixture
def client(invest_api, backoffice_token, invest_db, request):
    new_client = create_client(invest_api, backoffice_token)
    request.addfinalizer(invest_db.delete_autotest_clients)
    return new_client


@pytest.fixture
def client_with_agreement(invest_api, backoffice_token, client):
    agreement = open_agreement(invest_api, backoffice_token, client['id'])
    token = login_client(invest_api, client)
    return client, agreement, token
