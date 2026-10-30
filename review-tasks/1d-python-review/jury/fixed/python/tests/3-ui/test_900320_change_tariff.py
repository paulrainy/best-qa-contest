from hamcrest import assert_that, equal_to
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
            with cabinet.expect_event('dialog') as dialog_info:
                profile.switch_tariff_button().click()
            assert_that(dialog_info.value.message, equal_to('Сменить тариф на «Трейдер»?'), 'Текст окна подтверждения')

        with reporting.step('Проверить смену тарифа'):
            expect(cabinet.get_by_role('alert')).to_have_text('Тариф изменён на «Трейдер»')
            expect(profile.tariff()).to_have_text('Трейдер')
