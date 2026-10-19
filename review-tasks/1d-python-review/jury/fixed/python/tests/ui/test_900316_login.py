from playwright.sync_api import expect

from framework.reporting import Reporting as reporting
from invest.pages.cabinet import AgreementsPage, LoginPage


@reporting.epic('Кабинет инвестора')
@reporting.feature('Вход')
class TestCabinetLogin:

    @reporting.id(900316)
    @reporting.title('Вход в кабинет и список договоров')
    def test_login_and_agreements(self, page, cabinet_client):
        client, agreement = cabinet_client

        with reporting.step('Открыть кабинет и войти'):
            page.goto('/cabinet/')
            LoginPage(page).login(client['login'], client['password'])
            full_name = f"{client['lastName']} {client['firstName']} {client['middleName']}"
            expect(page.get_by_test_id('client-name')).to_have_text(full_name)

        with reporting.step('Проверить договор в списке'):
            row = AgreementsPage(page).row(agreement['number'])
            expect(row).to_contain_text('Брокерский договор')
            expect(row.get_by_test_id('agreement-row-balance')).to_have_text('0,00 ₽')
