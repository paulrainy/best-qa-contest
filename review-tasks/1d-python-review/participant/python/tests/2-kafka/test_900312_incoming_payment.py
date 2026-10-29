import time
import uuid
from datetime import datetime

import pytest
from hamcrest import assert_that, equal_to, greater_than

from framework.reporting import Reporting as reporting
from invest.kafka.topics import Topics


@reporting.epic('Брокерское обслуживание')
@reporting.feature('События Kafka')
class TestIncomingPayment:

    @pytest.mark.smoke
    @reporting.id(900312)
    @reporting.title('Поступление из ЦФТ зачисляется на брокерский счёт')
    def test_incoming_payment(self, kafka, qa_kafka, invest_db, client_with_agreement):
        client, agreement, token = client_with_agreement

        with reporting.step('Отправить поступление 1 000 ₽ из ЦФТ'):
            payment = {
                'PaymentId': str(uuid.uuid4()),
                'AgreementNumber': agreement['number'],
                'Amount': '1000.00',
                'Currency': 'RUB',
                'PaymentTime': datetime.now().isoformat(timespec='milliseconds'),
            }
            qa_kafka.send(Topics.INCOMING_PAYMENTS, kafka.cluster_id, payment)
            time.sleep(2)

        with reporting.step('Проверить событие об исполнении поручения'):
            messages = kafka.read_messages(Topics.MONEY_ORDERS)
            print(f'[KAFKA] события: {messages}')
            event = messages[-1]['value']
            assert_that(event['agreementNumber'], equal_to(agreement['number']), 'Договор в событии')
            assert_that(event['status'], equal_to('EXECUTED'), 'Статус поручения')
            assert_that(event['amount'], equal_to('1000.00'), 'Сумма')
            assert_that(event['source'], equal_to('CFT'), 'Источник поручения')

        with reporting.step('Проверить остаток в БД'):
            account = invest_db.get_account(agreement['id'])
            assert_that(account['balance'], greater_than(0), 'Остаток на счёте')
