from hamcrest import assert_that, is_

from framework.generate_data import GenerateData


def create_client(invest_api, backoffice_token, tariff=None, extra=None, defaults=None):
    """Создаёт клиента через API бэк-офиса. По умолчанию — тариф «Инвестор»."""
    body = {**GenerateData().client(), **(defaults or {}), **(extra or {})}
    if tariff:
        body['tariff'] = tariff
    response = invest_api.create_client(body, backoffice_token)
    assert_that(response.status_code, is_(201), f'Клиент не создан: {response.text}')
    return {**response.json(), 'password': body['password']}


def login_client(invest_api, client):
    response = invest_api.client_login(client['login'], client['password'])
    assert_that(response.status_code, is_(200), f"Клиент {client['login']} не смог войти: {response.text}")
    return response.json()['token']


def open_agreement(invest_api, backoffice_token, client_id, agreement_type='BROKER'):
    response = invest_api.open_agreement(client_id, agreement_type, backoffice_token)
    assert_that(response.status_code, is_(201), f'Договор {agreement_type} не открыт: {response.text}')
    return response.json()
