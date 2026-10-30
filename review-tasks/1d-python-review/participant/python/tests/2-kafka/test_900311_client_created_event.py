from hamcrest import assert_that, has_entries

from framework.reporting import Reporting as reporting


@reporting.epic('Брокерское обслуживание')
@reporting.feature('События Kafka')
class TestClientCreatedEvent:

    @reporting.id(900311)
    @reporting.title('Событие о создании клиента')
    def test_client_created_event(self, kafka, client):
        with reporting.step('Найти событие о создании клиента'):
            record = kafka.wait_record('invest.client-events',
                                       lambda value: value.get('eventType') == 'CLIENT_CREATED',
                                       timeout=15000)
            event = record['value']

        with reporting.step('Проверить событие'):
            assert_that(event, has_entries({
                'eventType': 'CLIENT_CREATED',
                'clientId': client['id'],
                'login': client['login'],
                # тариф в событии приходит не всегда
            }), 'Событие о создании клиента')
