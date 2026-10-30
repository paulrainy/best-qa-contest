import pytest
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
        if profile.tariff().inner_text() != 'Инвестор':
            pytest.skip('Клиент уже на «Трейдере»')

        with reporting.step('Перейти на тариф «Трейдер»'):
            cabinet.once('dialog', lambda dialog: dialog.accept())
            profile.switch_tariff_button().click()
            expect.set_options(timeout=10_000)  # тариф на стенде меняется не сразу

        with reporting.step('Проверить смену тарифа'):
            expect(cabinet.get_by_role('alert')).to_contain_text('Трейдер')
