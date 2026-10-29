import time

import requests
from hamcrest import assert_that, contains_string, equal_to, greater_than

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
            # Запрос на закрытие договора с остатком
            response = requests.post(f"http://localhost:18300/api/v1/agreements/{agreement['id']}/close",
                                     headers={'Authorization': f'Bearer {token}'})

        with reporting.step('Проверить отказ и статус договора'):
            assert_that(response.json()['errorMessage'], contains_string('выведите'), 'Текст ошибки')
            assert_that(response.status_code, equal_to(409), 'Код ответа')
            assert_that(invest_db.get_agreements(client['id'])[0]['status'], equal_to('ACTIVE'), 'Статус договора')
            account = invest_db.get_account(agreement['id'])
            assert_that(account['balance'], greater_than(0), 'Остаток на счёте после отказа')
            agreement_api = invest_api.get_agreement(agreement['id'], token)
            assert_that(agreement_api.status_code, equal_to(200), f'Договор не получен: {agreement_api.text}')
            assert_that(agreement['status'], equal_to('ACTIVE'), 'Статус договора по API после отказа')
