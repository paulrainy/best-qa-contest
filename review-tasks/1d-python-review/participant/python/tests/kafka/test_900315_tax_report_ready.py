from datetime import date

from hamcrest import assert_that, equal_to

from framework.reporting import Reporting as reporting
from invest.kafka.topics import Topics


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
            db_report = invest_db.wait_tax_report_status(report['id'], 'READY')
            assert_that(db_report['file_name'], equal_to(file_name), 'Имя файла справки в БД')
            api_report = invest_api.get_tax_report(report['id'], token).json()
            assert_that(api_report['status'], equal_to('READY'), 'Статус справки по API')
