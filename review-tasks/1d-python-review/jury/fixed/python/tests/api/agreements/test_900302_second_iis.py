from hamcrest import assert_that, equal_to, has_length

from framework.reporting import Reporting as reporting
from invest.steps.clients import open_agreement


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Договоры')
class TestSecondIis:

    @reporting.id(900302)
    @reporting.title('Второй ИИС не открывается')
    def test_second_iis_rejected(self, invest_api, invest_db, backoffice_token, client):
        with reporting.step('Открыть клиенту ИИС'):
            open_agreement(invest_api, backoffice_token, client['id'], 'IIS')

        with reporting.step('Попробовать открыть второй ИИС'):
            response = invest_api.open_agreement(client['id'], 'IIS', backoffice_token)

        with reporting.step('Проверить отказ'):
            assert_that(response.status_code, equal_to(409), f'Код ответа: {response.text}')
            assert_that(response.json()['errorMessage'], equal_to('У клиента уже есть действующий ИИС'), 'Текст ошибки')

        with reporting.step('Проверить договоры клиента в БД'):
            iis = [a for a in invest_db.get_agreements(client['id']) if a['type'] == 'IIS']
            assert_that(iis, has_length(1), 'ИИС у клиента')
