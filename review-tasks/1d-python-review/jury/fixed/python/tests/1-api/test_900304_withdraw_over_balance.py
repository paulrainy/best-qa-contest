from hamcrest import assert_that, equal_to

from framework.reporting import Reporting as reporting


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Денежные поручения')
class TestWithdrawOverBalance:

    @reporting.id(900304)
    @reporting.title('Вывод больше доступного остатка')
    def test_withdraw_over_balance(self, invest_api, invest_db, client_with_agreement):
        client, agreement, token = client_with_agreement

        with reporting.step('Подготовить остаток 5 000 ₽'):
            refill = invest_api.refill(agreement['id'], 5000, token)
            assert_that(refill.status_code, equal_to(201), f'Поручение на пополнение не создано: {refill.text}')
            invest_db.wait_order_status(refill.json()['id'], 'EXECUTED')

        with reporting.step('Вывести 5 000,01 ₽'):
            response = invest_api.withdraw(agreement['id'], '5000.01', token)

        with reporting.step('Проверить отказ'):
            assert_that(response.status_code, equal_to(422), f'Код ответа: {response.text}')
            assert_that(response.json()['errorMessage'], equal_to('Недостаточно средств для вывода'), 'Текст ошибки')

        with reporting.step('Проверить, что поручение не создано, а остаток не изменился'):
            withdrawals = invest_db.query("SELECT COUNT(*) AS cnt FROM money_order WHERE agreement_id = ?"
                                          " AND type = 'WITHDRAW'", agreement['id'], fetch_one=True)['cnt']
            assert_that(withdrawals, equal_to(0), 'Создано поручение на вывод')
            account = invest_db.get_account(agreement['id'])
            assert_that(account['balance'], equal_to(5000), 'Остаток на счёте')
