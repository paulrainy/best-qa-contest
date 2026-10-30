from playwright.sync_api import expect

from framework.reporting import Reporting as reporting
from invest.pages.cabinet import LoginPage


@reporting.epic('Кабинет инвестора')
@reporting.feature('Вход')
class TestCabinetLogin:

    @reporting.id(900316)
    @reporting.title('Вход в кабинет и список договоров')
    def test_login_and_agreements(self, page, cabinet_client):
        client, agreement = cabinet_client

        with reporting.step('Открыть кабинет и войти'):
            page.goto('http://localhost:18300/cabinet/')
            LoginPage(page).login(client['login'], client['password'])
            page.wait_for_load_state('networkidle')
            expect(page.get_by_test_id('client-name')).to_contain_text(client['lastName'])

        with reporting.step('Проверить договор в списке'):
            row = page.get_by_test_id('agreement-row').first
            expect(row.locator('td').nth(1)).not_to_be_empty()
            expect(row.get_by_test_id('agreement-row-balance')).to_have_text('0,00 ₽')
