"""Клиент QA Service: чтение и отправка сообщений Kafka через HTTP. Прямого доступа к Kafka со стендов нет."""
import json
import logging

import allure
import requests

from framework.config import Config

log = logging.getLogger('qa_service')


class QAServiceKafkaClient:

    def __init__(self, base_url: str = None, timeout: int = 30):
        self.base_url = (base_url or Config.qa_service_url()).rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.trust_env = False

    def _post(self, path: str, payload: dict) -> dict:
        response = self.session.post(f'{self.base_url}{path}', json=payload, timeout=self.timeout)
        log.info('POST %s %s -> %s %s', path, payload, response.status_code, response.text[:300])
        response.raise_for_status()
        return response.json()

    def get_clusters(self) -> list:
        response = self.session.get(f'{self.base_url}/api/kafka/clusters', timeout=self.timeout)
        response.raise_for_status()
        return response.json()['clusters']

    def subscribe(self, topic: str, cluster_id: str, seconds_ago: int = 60, limit: int = 100) -> dict:
        """Сообщения топика за последние seconds_ago секунд, не больше limit, по возрастанию offset.
        Если топика нет, QA Service отвечает 400 и requests бросает HTTPError."""
        return self._post('/api/kafka/subscribe', {'topic': topic, 'cluster_id': cluster_id,
                                                   'seconds_ago': seconds_ago, 'limit': limit})

    def send(self, topic: str, cluster_id: str, value: dict, key: str = None) -> dict:
        with allure.step(f'Отправить сообщение в топик {topic}'):
            allure.attach(json.dumps(value, ensure_ascii=False, indent=2), name=topic,
                          attachment_type=allure.attachment_type.JSON)
            return self._post('/api/kafka/send', {'topic': topic, 'cluster_id': cluster_id, 'key': key, 'value': value})
