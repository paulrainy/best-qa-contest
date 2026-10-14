import pytest
from hamcrest import assert_that, equal_to

from framework.reporting import Reporting as reporting

LOGIN = 'inv_client_lock'
PASSWORD = 'Client#Playground'


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Авторизация')
class TestLoginLock:

    @pytest.mark.xfail(reason='Блокировка иногда не успевает примениться')
    @reporting.id(900310)
    @reporting.title('Блокировка входа после трёх неверных паролей')
    def test_login_lock(self, invest_api, invest_db):
        with reporting.step('Снять блокировку с клиента после прошлых прогонов'):
            invest_db.execute("UPDATE client SET status = 'ACTIVE', failed_logins = 0 WHERE login = ?", LOGIN)

        with reporting.step('Трижды ввести неверный пароль'):
            for attempt in range(1, 4):
                response = invest_api.client_login(LOGIN, 'wrong-password')
                assert_that(response.status_code, equal_to(401), f'Попытка {attempt}: {response.text}')
                assert_that(response.json()['errorMessage'], equal_to('Неверный логин или пароль'),
                            f'Текст ошибки, попытка {attempt}')

        with reporting.step('Войти с верным паролем'):
            response = invest_api.client_login(LOGIN, PASSWORD)
            assert_that(response.status_code, equal_to(423), 'Код ответа')
            assert_that(response.json()['errorMessage'],
                        equal_to('Учётная запись заблокирована. Обратитесь в поддержку'), 'Текст ошибки')

        with reporting.step('Проверить статус клиента в БД'):
            db_client = invest_db.query(f"SELECT status FROM client WHERE login = '{LOGIN}'", fetch_one=True)
            assert_that(db_client['status'], equal_to('LOCKED'), 'Статус клиента')
