from hamcrest import assert_that, equal_to, is_

from framework.reporting import Reporting as reporting
from invest.kafka.topics import Topics

PAYMENT_ID = 'CFT-PAY-900313-0001'


@reporting.epic('Брокерское обслуживание')
@reporting.feature('События Kafka')
class TestDuplicatePayment:

    @reporting.id(900313)
    @reporting.title('Повторно доставленное поступление не зачисляется дважды')
    def test_duplicate_payment(self, kafka, invest_db, client_with_agreement):
        client, agreement, token = client_with_agreement

        with reporting.step('Отправить поступление 1 000 ₽ из ЦФТ'):
            kafka.send_payment(agreement['number'], 1000, payment_id=PAYMENT_ID)
            kafka.wait_message(Topics.MONEY_ORDERS, lambda value: value['agreementId'] == agreement['id']
                               and value['status'] == 'EXECUTED')

        with reporting.step('Отправить то же поступление повторно'):
            kafka.send_payment(agreement['number'], 1000, payment_id=PAYMENT_ID)

        with reporting.step('Проверить, что деньги зачислены один раз'):
            assert_that(invest_db.get_account(agreement['id'])['balance'], equal_to(1000), 'Остаток на счёте')
            assert_that(len(invest_db.get_orders(agreement['id'])) == 1, is_(True))
