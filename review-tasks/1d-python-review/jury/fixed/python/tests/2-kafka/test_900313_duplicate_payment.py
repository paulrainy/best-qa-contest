import uuid

from hamcrest import assert_that, equal_to, has_length

from framework.reporting import Reporting as reporting
from invest.kafka.topics import Topics


@reporting.epic('Брокерское обслуживание')
@reporting.feature('События Kafka')
class TestDuplicatePayment:

    @reporting.id(900313)
    @reporting.title('Повторно доставленное поступление не зачисляется дважды')
    def test_duplicate_payment(self, kafka, invest_db, client_with_agreement):
        client, agreement, token = client_with_agreement
        payment_id = str(uuid.uuid4())

        with reporting.step('Отправить поступление 1 000 ₽ из ЦФТ'):
            kafka.send_payment(agreement['number'], 1000, payment_id=payment_id)
            kafka.wait_message(Topics.MONEY_ORDERS, lambda value: value['agreementId'] == agreement['id']
                               and value['status'] == 'EXECUTED')
            assert_that(invest_db.get_account(agreement['id'])['balance'], equal_to(1000),
                        'Остаток после первого зачисления')

        with reporting.step('Отправить то же поступление повторно'):
            kafka.send_payment(agreement['number'], 1000, payment_id=payment_id)

        with reporting.step('Дождаться, пока сервис обработает повтор'):
            # Сообщения одного договора обрабатываются по порядку: раз контрольное поступление зачислено,
            # повтор перед ним уже обработан
            kafka.send_payment(agreement['number'], 1)
            kafka.wait_message(Topics.MONEY_ORDERS, lambda value: value['agreementId'] == agreement['id']
                               and value['amount'] == '1.00' and value['status'] == 'EXECUTED')

        with reporting.step('Проверить, что деньги зачислены один раз'):
            assert_that(invest_db.get_account(agreement['id'])['balance'], equal_to(1001),
                        'Остаток на счёте: 1 000 ₽ и контрольный 1 ₽')
            refills = [o for o in invest_db.get_orders(agreement['id']) if o['amount'] == 1000]
            assert_that(refills, has_length(1), 'Поручений на пополнение на 1 000 ₽')
            events = [m['value'] for m in kafka.read_messages(Topics.MONEY_ORDERS)
                      if m['value']['agreementId'] == agreement['id'] and m['value']['status'] == 'EXECUTED'
                      and m['value']['amount'] == '1000.00']
            assert_that(events, has_length(1), 'Событий EXECUTED на 1 000 ₽ по договору')
