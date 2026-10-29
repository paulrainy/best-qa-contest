from hamcrest import assert_that, equal_to, has_entries, is_

from framework.reporting import Reporting as reporting
from invest.steps.clients import login_client


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Тарифы')
class TestChangeTariff:

    @reporting.id(900309)
    @reporting.title('Смена тарифа «Инвестор» на «Трейдер»')
    def test_change_tariff(self, invest_api, invest_db, client):
        token = login_client(invest_api, client)

        with reporting.step('Открыть профиль клиента'):
            profile_before = invest_api.get_profile(token)
            assert_that(profile_before.status_code, equal_to(200), f'Профиль не получен: {profile_before.text}')
            assert_that(profile_before.json()['tariff'], equal_to('INVESTOR'), 'Тариф до смены')

        with reporting.step('Сменить тариф на «Трейдер»'):
            response = invest_api.change_tariff('TRADER', token)
            assert_that(response.status_code, is_(200), f'Тариф не сменён: {response.text}')
            assert_that(response.json()['tariff'], equal_to('TRADER'), 'Тариф в ответе')

        with reporting.step('Проверить тариф в БД и в профиле'):
            db_client = invest_db.get_client_by_login(client['login'])
            assert_that(db_client['tariff'], equal_to('TRADER'), 'Тариф в БД')
            history = invest_db.get_tariff_history(client['id'])[0]
            assert_that(history, has_entries(old_tariff='INVESTOR', new_tariff='TRADER'),
                        f'Последняя запись истории смены тарифа: {history}')
            profile = invest_api.get_profile(token)
            assert_that(profile.status_code, equal_to(200), f'Профиль не получен: {profile.text}')
            assert_that(profile.json()['tariff'], equal_to('TRADER'), 'Тариф в профиле после смены')
