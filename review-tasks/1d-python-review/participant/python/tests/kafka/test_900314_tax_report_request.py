from datetime import date, datetime

import pytest
from hamcrest import assert_that, equal_to
from requests import HTTPError

from framework.reporting import Reporting as reporting


@reporting.epic('Брокерское обслуживание')
@reporting.feature('События Kafka')
class TestTaxReportRequest:

    @reporting.id(900314)
    @reporting.title('Запрос справки НДФЛ уходит в СОФР')
    def test_tax_report_request(self, invest_api, kafka, client_with_agreement):
        client, agreement, token = client_with_agreement
        tax_period = str(date.today().year - 1)

        with reporting.step(f'Заказать справку НДФЛ за {tax_period} год'):
            response = invest_api.order_tax_report(int(tax_period), token)
            assert_that(response.status_code, equal_to(201), f'Справка не заказана: {response.text}')

        with reporting.step('Найти запрос справки в топике СОФР'):
            try:
                message = kafka.wait_message('sofr.get-tax-report-info-request',
                                             lambda value: value['GetTaxReportInfoReq']['TaxPeriod'] == tax_period)
            except HTTPError:
                pytest.skip('Топик СОФР недоступен на стенде')
            request = message['GetTaxReportInfoReq']

        with reporting.step('Проверить запрос'):
            request_time = datetime.fromisoformat(request['RequestTime'])
            assert_that(request_time.date(), equal_to(date.today()), 'Дата запроса')
