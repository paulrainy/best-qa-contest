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
            invest_db.set_balance(agreement['id'], 5000)

        with reporting.step('Вывести 5 000,01 ₽'):
            response = invest_api.withdraw(agreement['id'], '5000.01', token)

        with reporting.step('Проверить отказ'):
            assert_that(response.status_code, equal_to(422), f'Код ответа: {response.text}')
            assert_that(response.json()['errorMessage'], equal_to('Недостаточно средств для вывода'), 'Текст ошибки')

        with reporting.step('Проверить, что поручение не создано, а остаток не изменился'):
            assert_that(invest_db.count_today_orders(agreement['id']), equal_to(0), 'Создано поручение на вывод')
            account = invest_db.get_account(agreement['id'])
            assert_that(account['balance'], equal_to(5000), 'Остаток на счёте')
