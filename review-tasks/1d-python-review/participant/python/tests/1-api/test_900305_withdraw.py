import pytest
from hamcrest import assert_that, equal_to, is_

from framework.reporting import Reporting as reporting
from invest.steps.clients import create_client, login_client, open_agreement


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Денежные поручения')
class TestWithdraw:

    @pytest.mark.smoke
    @reporting.id(900305)
    @reporting.title('Вывод средств на тарифе «Трейдер»')
    def test_withdraw_trader(self, invest_api, invest_db, client_defaults, request):
        with reporting.step('Создать клиента на тарифе «Трейдер» с брокерским договором'):
            login = invest_api.backoffice_login('bo_operator1', 'Oper1#Playground')
            assert_that(login.status_code, is_(200), f'Не удалось войти в бэк-офис: {login.text}')
            backoffice_token = login.json()['token']
            client_defaults['tariff'] = 'TRADER'
            client = create_client(invest_api, backoffice_token, defaults=client_defaults)
            request.addfinalizer(lambda: invest_db.delete_client(client['id']))
            agreement = open_agreement(invest_api, backoffice_token, client['id'])
            token = login_client(invest_api, client)

        with reporting.step('Пополнить счёт на 10 000 ₽'):
            refill = invest_api.refill(agreement['id'], 10000, token).json()
            invest_db.wait_order_status(refill['id'], 'EXECUTED')

        with reporting.step('Вывести 3 000 ₽'):
            response = invest_api.withdraw(agreement['id'], 3000, token)
            assert_that(response.status_code, is_(201), f'Поручение на вывод не создано: {response.text}')

        with reporting.step('Проверить исполнение вывода без комиссии'):
            order = invest_db.query("SELECT * FROM money_order WHERE type = 'WITHDRAW' ORDER BY created_at DESC LIMIT 1",
                                    fetch_one=True)
            invest_db.wait_order_status(order['id'], 'EXECUTED')
            assert_that(order['commission'], equal_to(0), 'На тарифе «Трейдер» вывод без комиссии')
