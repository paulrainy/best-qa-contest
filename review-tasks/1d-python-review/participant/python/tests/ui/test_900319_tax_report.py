import pytest

from framework.reporting import Reporting as reporting
from invest.pages.cabinet import TaxReportsPage


@pytest.fixture
def browser_context_args(browser_context_args):
    return {**browser_context_args, 'base_url': 'http://localhost:18300'}


@reporting.epic('Кабинет инвестора')
@reporting.feature('Справки')
class TestCabinetTaxReport:

    @reporting.id(900319)
    @reporting.title('Заказ справки НДФЛ в кабинете')
    def test_order_tax_report(self, cabinet):
        year = 2025
        cabinet.goto('/cabinet/#/tax-reports')
        reports_page = TaxReportsPage(cabinet)

        with reporting.step(f'Заказать справку за {year} год'):
            reports_page.order(year)
            assert cabinet.get_by_role('alert').inner_text() == f'Справка за {year} год заказана'

        with reporting.step('Проверить справку в списке'):
            cabinet.screenshot(path=f'build/screenshots/tax_report_{year}.png', full_page=True)
