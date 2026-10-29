from playwright.sync_api import expect

from framework.reporting import Reporting as reporting
from invest.pages.cabinet import AgreementsPage


@reporting.epic('Кабинет инвестора')
@reporting.feature('Денежные поручения')
class TestCabinetRefill:

    @reporting.id(900317)
    @reporting.title('Пополнение счёта в кабинете')
    def test_refill(self, cabinet, cabinet_client):
        client, agreement = cabinet_client
        agreement_page = AgreementsPage(cabinet).open_agreement(agreement['number'])
        order = agreement_page.order_rows().first

        with reporting.step('Создать поручение на пополнение 10 000 ₽'):
            agreement_page.refill(10000)
            expect(cabinet.get_by_role('alert')).to_have_text('Поручение на пополнение создано')
            expect(order).to_contain_text('Пополнение')
            expect(order.get_by_test_id('order-status')).to_have_text('Новое')

        with reporting.step('Дождаться исполнения поручения'):
            expect(order.get_by_test_id('order-status')).to_have_text('Исполнено', timeout=15_000)

        with reporting.step('Проверить остаток'):
            expect(agreement_page.balance_locator()).to_have_text('10 000,00 ₽')
