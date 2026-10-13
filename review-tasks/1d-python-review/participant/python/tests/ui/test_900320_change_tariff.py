from playwright.sync_api import expect

from framework.reporting import Reporting as reporting
from invest.pages.cabinet import ProfilePage


@reporting.epic('Кабинет инвестора')
@reporting.feature('Тарифы')
class TestCabinetChangeTariff:

    @reporting.id(900320)
    @reporting.title('Смена тарифа в профиле')
    def test_change_tariff(self, cabinet):
        profile = ProfilePage(cabinet).open()
        expect(profile.tariff()).to_have_text('Инвестор')

        with reporting.step('Перейти на тариф «Трейдер»'):
            cabinet.once('dialog', lambda dialog: dialog.accept())
            profile.switch_tariff_button().click()

        with reporting.step('Проверить смену тарифа'):
            expect(cabinet.get_by_role('alert')).to_contain_text('Трейдер')
