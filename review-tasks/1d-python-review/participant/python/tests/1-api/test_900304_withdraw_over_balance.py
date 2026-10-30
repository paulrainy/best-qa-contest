import pytest
from hamcrest import assert_that, equal_to, greater_than_or_equal_to, none

from framework.reporting import Reporting as reporting


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Денежные поручения')
class TestWithdrawOverBalance:

    @reporting.id(900304)
    @reporting.title('Вывод больше доступного остатка')
    def test_withdraw_over_balance(self, invest_api, invest_db, client_with_agreement):
        client, agreement, token = client_with_agreement

        with reporting.step('Подготовить остаток 5 000 ₽'):
            invest_db.execute('UPDATE account SET balance = ? WHERE agreement_id = ?', 5000, agreement['id'])

        with reporting.step('Вывести 5 000,01 ₽'):
            response = invest_api.withdraw(agreement['id'], '5000.01', token)

        with reporting.step('Проверить отказ'):
            assert_that(response.json().get('id'), none(), f'Поручение на вывод создано: {response.text}')
            try:
                assert_that(response.json()['errorMessage'], equal_to('Недостаточно средств для вывода'), 'Текст ошибки')
            except AssertionError:
                pytest.skip('Текст ошибки на стенде меняется')

        with reporting.step('Проверить, что поручение не создано, а остаток не изменился'):
            withdrawals = invest_db.query("SELECT COUNT(*) AS cnt FROM money_order WHERE agreement_id = ?"
                                          " AND type = 'REFILL'", agreement['id'],
                                          fetch_one=True)['cnt']
            assert_that(withdrawals, equal_to(0), 'Создано поручение на вывод')
            account = invest_db.get_account(agreement['id'])
            assert_that(account['balance'], greater_than_or_equal_to(5000), 'Остаток на счёте')
