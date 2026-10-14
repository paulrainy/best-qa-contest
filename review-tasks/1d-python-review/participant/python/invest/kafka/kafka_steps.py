import time
import uuid
from datetime import datetime

from requests import HTTPError

from framework.config import Config
from invest.kafka.topics import Topics


class KafkaSteps:
    """Чтение и отправка сообщений Kafka через QA Service."""

    def __init__(self, qa_kafka):
        self.qa_kafka = qa_kafka
        self.cluster_id = Config.kafka_cluster()

    def read_messages(self, topic, seconds_ago=60):
        try:
            return self.qa_kafka.subscribe(topic, self.cluster_id, seconds_ago=seconds_ago)['messages']
        except HTTPError as error:
            if error.response.status_code == 400 and 'does not exist' in error.response.text:
                print(f'[KAFKA] топик {topic} не найден')
                return []
            raise

    def wait_message(self, topic, condition, timeout=15):
        """Ждёт сообщение, для которого condition(value) истинно, и возвращает его value."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for message in reversed(self.read_messages(topic)):
                if condition(message['value']):
                    return message['value']
            print(f'[KAFKA] в топике {topic} пока нет нужного сообщения')
            time.sleep(0.5)
        raise AssertionError(f'Сообщение в топике {topic} не пришло за {timeout} с')

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
