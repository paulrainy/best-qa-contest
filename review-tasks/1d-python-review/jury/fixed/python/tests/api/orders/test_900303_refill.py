import pytest
from hamcrest import assert_that, equal_to, is_

from framework.reporting import Reporting as reporting


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Денежные поручения')
class TestRefill:

    @pytest.mark.smoke
    @reporting.id(900303)
    @reporting.title('Пополнение брокерского счёта')
    def test_refill(self, invest_api, invest_db, client_with_agreement):
        client, agreement, token = client_with_agreement

        with reporting.step('Пополнить счёт на 10 000 ₽'):
            response = invest_api.refill(agreement['id'], 10000, token)
            assert_that(response.status_code, is_(201), f'Поручение не создано: {response.text}')
            order = response.json()
            assert_that(order['status'], equal_to('NEW'), 'Статус нового поручения')

        with reporting.step('Дождаться исполнения поручения'):
            invest_db.wait_order_status(order['id'], 'EXECUTED')

        with reporting.step('Проверить остаток'):
            balance = invest_api.get_agreement(agreement['id'], token).json()['balance']
            assert_that(balance, equal_to('10000.00'), 'Остаток по API')
            account = invest_db.get_account(agreement['id'])
            assert_that(account['balance'], equal_to(10000), 'Остаток в БД')
