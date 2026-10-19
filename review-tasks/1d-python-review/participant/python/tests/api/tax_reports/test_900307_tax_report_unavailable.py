from datetime import datetime

import pytest
from hamcrest import assert_that, equal_to

from framework.reporting import Reporting as reporting

CURRENT_YEAR = datetime.now().year


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Справки')
class TestTaxReportUnavailable:

    @reporting.id(900307)
    @reporting.title('Справка НДФЛ за незавершённый год недоступна')
    @pytest.mark.parametrize('tax_period', [CURRENT_YEAR, CURRENT_YEAR], ids=['current_year', 'next_year'])
    def test_tax_report_unavailable(self, invest_api, invest_db, client_with_agreement, tax_period):
        client, agreement, token = client_with_agreement

        with reporting.step(f'Заказать справку за {tax_period} год'):
            with pytest.raises(Exception) as error:
                invest_api.order_tax_report(tax_period, token).raise_for_status()
                assert_that(error.value.response.status_code, equal_to(422), 'Код ответа')
                assert_that(error.value.response.json()['errorMessage'],
                            equal_to('Справку можно заказать только за завершённый год'), 'Текст ошибки')

        with reporting.step('Проверить, что заявка на справку не создана'):
            ordered = invest_db.query("SELECT COUNT(*) AS cnt FROM tax_report WHERE client_id = ? AND status = 'Ordered'",
                                      client['id'], fetch_one=True)['cnt']
            assert_that(ordered, equal_to(0), 'Заявка на справку создана')
            reports = invest_api.get_tax_reports(token)
