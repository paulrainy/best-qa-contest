"""Kafka песочницы: топики в памяти, одна партиция на топик. Тесты работают с ней через HTTP-шлюз QA Service."""
import threading
import time

CLUSTER_ID = 'invest-kafka'

TOPICS = (
    'invest.client-events',             # сервис → события по клиентам
    'invest.money-orders',              # сервис → статусы денежных поручений
    'cft.incoming-payments',            # ЦФТ → сервис: поступления на брокерские счета
    'sofr.get-tax-report-info-request',  # сервис → СОФР: запрос справки НДФЛ
    'sofr.get-tax-report-info-response',  # СОФР → сервис: справка готова
)


class KafkaError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class Broker:

    def __init__(self):
        self.lock = threading.Lock()
        self.topics = {name: [] for name in TOPICS}

    def topic(self, name: str) -> list:
        if name not in self.topics:
            raise KafkaError(400, f"Topic '{name}' does not exist in cluster {CLUSTER_ID}")
        return self.topics[name]

    def publish(self, topic: str, key, value) -> dict:
        with self.lock:
            messages = self.topic(topic)
            message = {'topic': topic, 'partition': 0, 'offset': len(messages),
                       'timestamp': int(time.time() * 1000), 'key': key, 'value': value}
            messages.append(message)
            return message

    def read(self, topic: str, from_timestamp: int = None, to_timestamp: int = None, limit: int = 100) -> list:
        """Последние limit сообщений в окне [from_timestamp; to_timestamp] (секунды), по возрастанию offset."""
        with self.lock:
            messages = list(self.topic(topic))
        if from_timestamp is not None:
            messages = [m for m in messages if m['timestamp'] >= from_timestamp * 1000]
        if to_timestamp is not None:
            messages = [m for m in messages if m['timestamp'] <= to_timestamp * 1000 + 999]
        return messages[-limit:] if limit else messages

    def read_from(self, topic: str, offset: int) -> list:
        with self.lock:
            return list(self.topic(topic)[offset:])
