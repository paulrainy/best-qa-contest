import pytest

from framework.config import Config
from invest.pages.cabinet import LoginPage
from invest.steps.clients import create_client, open_agreement


@pytest.fixture(scope='session')
def base_url():
    return Config.api_url()


@pytest.fixture(scope='session')
def cabinet_client(invest_api, backoffice_token):
    """Клиент с брокерским договором, под которым UI-тесты входят в кабинет."""
    client = create_client(invest_api, backoffice_token)
    agreement = open_agreement(invest_api, backoffice_token, client['id'])
    return client, agreement


@pytest.fixture
def cabinet(page, cabinet_client):
    """Кабинет, открытый под клиентом cabinet_client."""
    client, agreement = cabinet_client
    page.goto('/cabinet/')
    LoginPage(page).login(client['login'], client['password'])
    return page
