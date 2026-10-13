import time

import pytest
from hamcrest import assert_that, equal_to

from framework.reporting import Reporting as reporting
from invest.kafka.topics import Topics


@reporting.epic('Брокерское обслуживание')
@reporting.feature('События Kafka')
class TestIncomingPayment:

    @pytest.mark.smoke
    @reporting.id(900312)
    @reporting.title('Поступление из ЦФТ зачисляется на брокерский счёт')
    def test_incoming_payment(self, kafka, invest_db, client_with_agreement):
        client, agreement, token = client_with_agreement

        with reporting.step('Отправить поступление 1 000 ₽ из ЦФТ'):
            kafka.send_payment(agreement['number'], 1000)
            time.sleep(2)

        with reporting.step('Проверить событие об исполнении поручения'):
            event = kafka.read_messages(Topics.MONEY_ORDERS)[-1]['value']
            assert_that(event['agreementNumber'], equal_to(agreement['number']), 'Договор в событии')
            assert_that(event['status'], equal_to('EXECUTED'), 'Статус поручения')
            assert_that(event['amount'], equal_to('1000.00'), 'Сумма')
            assert_that(event['source'], equal_to('CFT'), 'Источник поручения')

        with reporting.step('Проверить остаток в БД'):
            account = invest_db.get_account(agreement['id'])
            assert_that(account['balance'], equal_to(1000), 'Остаток на счёте')
