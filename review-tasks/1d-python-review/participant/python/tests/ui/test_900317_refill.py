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

        with reporting.step('Создать поручение на пополнение 10 000 ₽'):
            agreement_page.refill(10000)
            expect(cabinet.get_by_role('alert')).to_have_text('Поручение на пополнение создано')
            expect(agreement_page.order_rows().first).to_contain_text('Пополнение')

        with reporting.step('Дождаться исполнения поручения'):
            cabinet.wait_for_timeout(5000)

        with reporting.step('Проверить остаток и статус поручения'):
            assert agreement_page.balance() == '10 000,00 ₽'
            expect(agreement_page.order_rows().first.get_by_test_id('order-status')).to_have_text('Исполнено',
                                                                                                 timeout=15_000)
