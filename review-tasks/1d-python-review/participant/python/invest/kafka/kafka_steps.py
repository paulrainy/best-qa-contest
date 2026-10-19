import logging
import time
import uuid
from datetime import datetime

from framework.config import Config
from invest.kafka.topics import Topics

log = logging.getLogger('kafka')


class KafkaSteps:
    """Чтение и отправка сообщений Kafka через QA Service."""

    def __init__(self, qa_kafka):
        self.qa_kafka = qa_kafka
        self.cluster_id = Config.kafka_cluster()

    def read_messages(self, topic, seconds_ago=60):
        return self.qa_kafka.subscribe(topic, self.cluster_id, seconds_ago=seconds_ago)['messages']

    def wait_record(self, topic, condition, timeout=15):
        """Ждёт сообщение, для которого condition(value) истинно, и возвращает его целиком: key и value."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for message in reversed(self.read_messages(topic)):
                if condition(message['value']):
                    return message
            log.info('В топике %s пока нет нужного сообщения', topic)
            time.sleep(0.5)
        raise AssertionError(f'Сообщение в топике {topic} не пришло за {timeout} с')

    def wait_message(self, topic, condition, timeout=15):
        """Ждёт сообщение, для которого condition(value) истинно, и возвращает его value."""
        return self.wait_record(topic, condition, timeout)['value']

    def send_payment(self, agreement_number, amount, payment_id=None):
        """Поступление на брокерский счёт — так его присылает ЦФТ."""
        payment = {
            'PaymentId': payment_id or str(uuid.uuid4()),
            'AgreementNumber': agreement_number,
            'Amount': f'{amount:.2f}',
            'Currency': 'RUB',
            'PaymentTime': datetime.now().isoformat(timespec='milliseconds'),
        }
        self.qa_kafka.send(Topics.INCOMING_PAYMENTS, self.cluster_id, payment, key=agreement_number)
        return payment
