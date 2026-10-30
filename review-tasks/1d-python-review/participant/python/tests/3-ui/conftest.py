import pytest

from framework.config import Config
from invest.pages.cabinet import LoginPage
from invest.steps.clients import create_client, open_agreement


@pytest.fixture(scope='session')
def base_url():
    return Config.api_url()


@pytest.fixture
def cabinet_client(invest_api, backoffice_token, client_defaults):
    """Клиент с брокерским договором, под которым UI-тест входит в кабинет."""
    client = create_client(invest_api, backoffice_token, defaults=client_defaults)
    agreement = open_agreement(invest_api, backoffice_token, client['id'])
    return client, agreement


@pytest.fixture
def cabinet(page, cabinet_client):
    """Кабинет, открытый под клиентом cabinet_client."""
    client, agreement = cabinet_client
    page.goto('/cabinet/')
    LoginPage(page).login(client['login'], client['password'])
    return page
