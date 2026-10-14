import pytest
from hamcrest import assert_that, is_

from framework.api.invest_api import InvestApi
from framework.config import Config
from invest.db.invest_db import InvestDb
from invest.steps.clients import create_client, login_client, open_agreement


@pytest.fixture(scope='session')
def invest_api():
    return InvestApi()


@pytest.fixture(scope='session')
def invest_db():
    return InvestDb()


@pytest.fixture(scope='session')
def backoffice_token(invest_api):
    login, password = Config.user('backoffice')
    response = invest_api.backoffice_login(login, password)
    assert_that(response.status_code, is_(200), f'Не удалось войти в бэк-офис: {response.text}')
    return response.json()['token']


@pytest.fixture(scope='session')
def client_defaults():
    """Поля нового клиента по умолчанию."""
    return {'tariff': 'INVESTOR'}


@pytest.fixture
def client(invest_api, backoffice_token, invest_db, client_defaults, request):
    new_client = create_client(invest_api, backoffice_token, defaults=client_defaults)
    request.addfinalizer(lambda: invest_db.delete_client(new_client['id']))
    return new_client


@pytest.fixture
def client_with_agreement(invest_api, backoffice_token, client):
    agreement = open_agreement(invest_api, backoffice_token, client['id'])
    token = login_client(invest_api, client)
    return client, agreement, token
