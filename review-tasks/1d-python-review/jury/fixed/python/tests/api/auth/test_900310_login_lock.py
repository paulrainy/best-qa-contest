from hamcrest import assert_that, equal_to

from framework.reporting import Reporting as reporting


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Авторизация')
class TestLoginLock:

    @reporting.id(900310)
    @reporting.title('Блокировка входа после трёх неверных паролей')
    def test_login_lock(self, invest_api, invest_db, client):
        with reporting.step('Трижды ввести неверный пароль'):
            for attempt in range(1, 4):
                response = invest_api.client_login(client['login'], 'wrong-password')
                assert_that(response.status_code, equal_to(401), f'Попытка {attempt}: {response.text}')
                assert_that(response.json()['errorMessage'], equal_to('Неверный логин или пароль'),
                            f'Текст ошибки, попытка {attempt}')

        with reporting.step('Войти с верным паролем'):
            response = invest_api.client_login(client['login'], client['password'])
            assert_that(response.status_code, equal_to(423), 'Код ответа')
            assert_that(response.json()['errorMessage'],
                        equal_to('Учётная запись заблокирована. Обратитесь в поддержку'), 'Текст ошибки')

        with reporting.step('Проверить статус клиента в БД'):
            assert_that(invest_db.get_client_by_login(client['login'])['status'], equal_to('LOCKED'), 'Статус клиента')
