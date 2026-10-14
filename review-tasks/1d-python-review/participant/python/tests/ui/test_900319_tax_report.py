from datetime import date

from playwright.sync_api import expect

from framework.reporting import Reporting as reporting
from invest.pages.cabinet import TaxReportsPage


@reporting.epic('Кабинет инвестора')
@reporting.feature('Справки')
class TestCabinetTaxReport:

    @reporting.id(900319)
    @reporting.title('Заказ справки НДФЛ в кабинете')
    def test_order_tax_report(self, cabinet):
        year = date.today().year - 1
        reports_page = TaxReportsPage(cabinet).open()

        with reporting.step(f'Заказать справку за {year} год'):
            reports_page.order(year)
            expect(cabinet.get_by_role('alert')).to_have_text(f'Справка за {year} год заказана')

        with reporting.step('Проверить справку в списке'):
            cabinet.screenshot(path=f'build/screenshots/tax_report_{year}.png', full_page=True)
