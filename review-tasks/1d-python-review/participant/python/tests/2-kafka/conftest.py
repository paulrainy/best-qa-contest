import pytest

from framework.kafka.qa_service import QAServiceKafkaClient
from invest.kafka.kafka_steps import KafkaSteps


@pytest.fixture(scope='session')
def qa_kafka():
    return QAServiceKafkaClient()


@pytest.fixture(scope='session')
def kafka(qa_kafka):
    return KafkaSteps(qa_kafka)
