from hamcrest import assert_that, equal_to, is_

from framework.reporting import Reporting as reporting
from invest.steps.clients import login_client


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Тарифы')
class TestChangeTariff:

    @reporting.id(900309)
    @reporting.title('Смена тарифа «Инвестор» на «Трейдер»')
    def test_change_tariff(self, invest_api, invest_db, client):
        token = login_client(invest_api, client)

        with reporting.step('Сменить тариф на «Трейдер»'):
            response = invest_api.change_tariff('TRADER', token)
            assert_that(response.status_code, is_(200), f'Тариф не сменён: {response.text}')
            assert_that(response.json()['tariff'], equal_to('TRADER'), 'Тариф в ответе')

        with reporting.step('Проверить тариф и историю смены в БД'):
            db_client = invest_db.get_client_by_login(client['login'])
            assert_that(db_client['tariff'], equal_to('TRADER'), 'Тариф в БД')
            history = invest_db.get_tariff_history(client['id'])
            assert_that(any(h['old_tariff'] == 'INVESTOR' and h['new_tariff'] == 'TRADER' for h in history), is_(True))
