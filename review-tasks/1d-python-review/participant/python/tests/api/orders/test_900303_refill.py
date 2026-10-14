import time

import pytest
from hamcrest import assert_that, contains_string, equal_to, is_, is_in

from framework.reporting import Reporting as reporting


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Денежные поручения')
class TestRefill:

    @pytest.mark.smoke
    @reporting.id(900303)
    @reporting.title('Пополнение брокерского счёта')
    def test_refill(self, invest_api, invest_db, client_with_agreement):
        client, agreement, token = client_with_agreement
        executed_before = invest_db.query("SELECT COUNT(*) AS cnt FROM money_order WHERE status = 'EXECUTED'",
                                          fetch_one=True)['cnt']

        with reporting.step('Пополнить счёт на 10 000 ₽'):
            response = invest_api.refill(agreement['id'], 10000, token)
            assert_that(response.status_code, is_(201), f'Поручение не создано: {response.text}')
            assert_that(response.json()['status'], is_in(['NEW', 'EXECUTED']), 'Статус нового поручения')

        with reporting.step('Дождаться исполнения поручения'):
            time.sleep(3)

        with reporting.step('Проверить исполнение поручения и остаток'):
            executed_after = invest_db.query("SELECT COUNT(*) AS cnt FROM money_order WHERE status = 'EXECUTED'",
                                             fetch_one=True)['cnt']
            assert_that(executed_after, equal_to(executed_before + 1), 'Поручение не исполнено')
            balance = invest_api.get_agreement(agreement['id'], token).json()['balance']
            assert_that(balance, contains_string('10000'), 'Остаток по API')
            account = invest_db.query('SELECT balance FROM account WHERE agreement_id = ?', agreement['id'],
                                      fetch_one=True)
            assert_that(account['balance'], equal_to(10000), 'Остаток в БД')
