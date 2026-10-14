import time

from hamcrest import assert_that, equal_to

from framework.reporting import Reporting as reporting


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Договоры')
class TestCloseWithBalance:

    @reporting.id(900308)
    @reporting.title('Договор с остатком не закрывается')
    def test_close_with_balance(self, invest_api, invest_db, client_with_agreement):
        client, agreement, token = client_with_agreement

        with reporting.step('Пополнить счёт на 1 000 ₽'):
            response = invest_api.refill(agreement['id'], 1000, token)
            assert_that(response.status_code, equal_to(201), f'Поручение не создано: {response.text}')
            order = response.json()
            deadline = time.monotonic() + 15
            while invest_api.get_order(order['id'], token).json()['status'] != 'EXECUTED':
                assert time.monotonic() < deadline, f"Поручение {order['id']} не исполнено за 15 секунд"
                time.sleep(0.5)

        with reporting.step('Закрыть договор'):
            response = invest_api.close_agreement(agreement['id'], token)

        with reporting.step('Проверить отказ и статус договора'):
            assert_that(response.status_code, equal_to(409), f'Код ответа: {response.text}')
            assert_that(response.json()['errorMessage'], equal_to('Для закрытия договора выведите денежные средства'),
                        'Текст ошибки')
            assert_that(invest_db.get_agreements(client['id'])[0]['status'], equal_to('ACTIVE'), 'Статус договора')
            agreement_api = invest_api.get_agreement(agreement['id'], token)
            assert_that(agreement_api.json()['status'], equal_to('ACTIVE'), 'Статус договора по API')
            account = invest_db.get_account(agreement['id'])
            assert_that(account['balance'], equal_to(1000), 'Остаток на счёте')
