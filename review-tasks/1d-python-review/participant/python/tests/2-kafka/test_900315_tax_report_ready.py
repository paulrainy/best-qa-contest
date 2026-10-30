from datetime import date

from hamcrest import assert_that, equal_to
from retrying import retry

from framework.reporting import Reporting as reporting
from invest.kafka.topics import Topics


@retry(stop_max_delay=15000)
def wait_report(invest_db, client_id, status):
    """Ждёт, пока справка клиента перейдёт в нужный статус."""
    report = invest_db.query('SELECT * FROM tax_report WHERE client_id = ?', client_id, fetch_one=True)
    assert report['status'] == status, f"Справка: статус {report['status']}, ожидался {status}"
    return report


@reporting.epic('Брокерское обслуживание')
@reporting.feature('События Kafka')
class TestTaxReportReady:

    @reporting.id(900315)
    @reporting.title('Справка НДФЛ готова: ответ СОФР')
    def test_tax_report_ready(self, invest_api, invest_db, kafka, qa_kafka, client_with_agreement):
        client, agreement, token = client_with_agreement

        with reporting.step('Заказать справку НДФЛ за прошлый год'):
            response = invest_api.order_tax_report(date.today().year - 1, token)
            assert_that(response.status_code, equal_to(201), f'Справка не заказана: {response.text}')
            report = response.json()

        with reporting.step('Получить запрос справки из топика СОФР'):
            request = kafka.wait_message(Topics.TAX_REPORT_REQUEST,
                                         lambda value: value['GetTaxReportInfoReq']['ClientId'] == client['id'])
            request = request['GetTaxReportInfoReq']

        with reporting.step('Ответить от имени СОФР: справка готова'):
            file_name = f"ndfl_{client['id']}_{request['TaxPeriod']}.pdf"
            qa_kafka.send(Topics.TAX_REPORT_RESPONSE, 'invest-kafka',
                          {'RequestId': request['RequestId'], 'Status': 'READY', 'FileName': file_name},
                          key=request['RequestId'])

        with reporting.step('Проверить статус справки'):
            db_report = wait_report(invest_db, client['id'], 'READY')
            assert_that(db_report['file_name'], equal_to(file_name), 'Имя файла справки в БД')
            response = invest_api.get_tax_report(report['id'], token)
            assert_that(response.status_code, equal_to(200), f'Справка не получена: {response.text}')
            assert_that(response.json()['status'], equal_to('READY'), 'Статус справки по API')
