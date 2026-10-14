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
    def test_withdraw_trader(self, invest_api, invest_db, backoffice_token, request):
        with reporting.step('Создать клиента на тарифе «Трейдер» с брокерским договором'):
            client = create_client(invest_api, backoffice_token, tariff='TRADER')
            request.addfinalizer(lambda: invest_db.delete_client(client['id']))
            agreement = open_agreement(invest_api, backoffice_token, client['id'])
            token = login_client(invest_api, client)

        with reporting.step('Пополнить счёт на 10 000 ₽'):
            refill = invest_api.refill(agreement['id'], 10000, token)
            assert_that(refill.status_code, is_(201), f'Поручение на пополнение не создано: {refill.text}')
            invest_db.wait_order_status(refill.json()['id'], 'EXECUTED')

        with reporting.step('Вывести 3 000 ₽'):
            response = invest_api.withdraw(agreement['id'], 3000, token)
            assert_that(response.status_code, is_(201), f'Поручение на вывод не создано: {response.text}')

        with reporting.step('Проверить исполнение вывода без комиссии'):
            order = invest_db.wait_order_status(response.json()['id'], 'EXECUTED')
            assert_that(order['commission'], equal_to(0), 'На тарифе «Трейдер» вывод без комиссии')
            account = invest_db.get_account(agreement['id'])
            assert_that(account['balance'], equal_to(7000), 'Остаток после вывода')
