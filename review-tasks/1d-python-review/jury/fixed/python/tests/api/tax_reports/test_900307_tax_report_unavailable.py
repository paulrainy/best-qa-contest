from datetime import datetime

import pytest
from hamcrest import assert_that, equal_to, has_length
from requests import HTTPError

from framework.reporting import Reporting as reporting

CURRENT_YEAR = datetime.now().year


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Справки')
class TestTaxReportUnavailable:

    @reporting.id(900307)
    @reporting.title('Справка НДФЛ за незавершённый год недоступна')
    @pytest.mark.parametrize('tax_period', [CURRENT_YEAR, CURRENT_YEAR + 1], ids=['current_year', 'next_year'])
    def test_tax_report_unavailable(self, invest_api, invest_db, client_with_agreement, tax_period):
        client, agreement, token = client_with_agreement

        with reporting.step(f'Заказать справку за {tax_period} год'):
            with pytest.raises(HTTPError) as error:
                invest_api.order_tax_report(tax_period, token).raise_for_status()
            assert_that(error.value.response.status_code, equal_to(422), 'Код ответа')
            assert_that(error.value.response.json()['errorMessage'],
                        equal_to('Справку можно заказать только за завершённый год'), 'Текст ошибки')

        with reporting.step('Проверить, что заявка на справку не создана'):
            assert_that(invest_db.get_tax_reports(client['id']), has_length(0), 'Заявки на справку в БД')
            reports = invest_api.get_tax_reports(token)
            assert_that(reports.status_code, equal_to(200), f'Список справок: {reports.text}')
            assert_that(reports.json(), has_length(0), 'Справки клиента по API')
