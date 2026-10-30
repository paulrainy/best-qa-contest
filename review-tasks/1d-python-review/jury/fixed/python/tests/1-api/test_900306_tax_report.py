from datetime import date

from hamcrest import assert_that, equal_to, has_length, is_

from framework.reporting import Reporting as reporting


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Справки')
class TestTaxReport:

    @reporting.id(900306)
    @reporting.title('Заказ справки НДФЛ за прошлый год')
    def test_order_tax_report(self, invest_api, invest_db, client_with_agreement):
        client, agreement, token = client_with_agreement
        tax_period = date.today().year - 1

        with reporting.step(f'Заказать справку НДФЛ за {tax_period} год'):
            response = invest_api.order_tax_report(tax_period, token)
            assert_that(response.status_code, is_(201), f'Справка не заказана: {response.text}')
            assert_that(response.json()['status'], equal_to('ORDERED'), 'Статус заявки в ответе')

        with reporting.step('Проверить заявку на справку в БД'):
            reports = invest_db.query("SELECT * FROM tax_report WHERE client_id = ?"
                                      " AND date(registered_at) = date('now', 'localtime') ORDER BY id DESC",
                                      client['id'])
            assert_that(reports, has_length(1), 'Заявок на справку за сегодня')
            assert_that(reports[0]['tax_period'], equal_to(tax_period), 'Налоговый период')
            assert_that(reports[0]['status'], equal_to('ORDERED'), 'Статус заявки в БД')
