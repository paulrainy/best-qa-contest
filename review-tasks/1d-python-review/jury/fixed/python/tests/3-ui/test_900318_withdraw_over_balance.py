from hamcrest import assert_that, empty
from playwright.sync_api import expect

from framework.reporting import Reporting as reporting
from invest.pages.cabinet import AgreementsPage
from invest.steps.clients import login_client


@reporting.epic('Кабинет инвестора')
@reporting.feature('Денежные поручения')
class TestCabinetWithdrawOverBalance:

    @reporting.id(900318)
    @reporting.title('Вывод больше остатка в кабинете')
    def test_withdraw_over_balance(self, cabinet, cabinet_client, invest_api, invest_db):
        client, agreement = cabinet_client

        with reporting.step('Подготовить остаток 5 000 ₽'):
            token = login_client(invest_api, client)
            order = invest_api.refill(agreement['id'], 5000, token).json()
            invest_db.wait_order_status(order['id'], 'EXECUTED')

        with reporting.step('Открыть договор'):
            agreement_page = AgreementsPage(cabinet).open_agreement(agreement['number'])
            expect(agreement_page.balance_locator()).to_have_text('5 000,00 ₽')

        with reporting.step('Вывести 5 000,01 ₽'):
            agreement_page.withdraw('5000,01')

        with reporting.step('Проверить отказ'):
            expect(cabinet.get_by_role('alert')).to_have_text('Недостаточно средств для вывода')
            withdrawals = [o for o in invest_db.get_orders(agreement['id']) if o['type'] == 'WITHDRAW']
            assert_that(withdrawals, empty(), 'Поручение на вывод создано')

        with reporting.step('Проверить историю и остаток после обновления страницы'):
            cabinet.reload()
            expect(agreement_page.order_rows()).to_have_count(1)
            expect(agreement_page.order_rows().filter(has_text='Вывод')).to_have_count(0)
            expect(agreement_page.balance_locator()).to_have_text('5 000,00 ₽')
