from hamcrest import assert_that, has_entries

from framework.reporting import Reporting as reporting
from invest.kafka.topics import Topics


@reporting.epic('Брокерское обслуживание')
@reporting.feature('События Kafka')
class TestClientCreatedEvent:

    @reporting.id(900311)
    @reporting.title('Событие о создании клиента')
    def test_client_created_event(self, kafka, client):
        with reporting.step('Найти событие о создании клиента'):
            event = kafka.wait_message(Topics.CLIENT_EVENTS, lambda value: value.get('login') == client['login'])

        with reporting.step('Проверить событие'):
            assert_that(event, has_entries({
                'eventType': 'CLIENT_CREATED',
                'clientId': client['id'],
                'tariff': 'INVESTOR',
            }), 'Событие о создании клиента')
