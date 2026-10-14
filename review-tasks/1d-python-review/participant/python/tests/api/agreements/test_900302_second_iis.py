from hamcrest import assert_that, is_not

from framework.reporting import Reporting as reporting
from invest.steps.clients import open_agreement


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Договоры')
class TestSecondIis:

    @reporting.id(900302)
    @reporting.title('Второй ИИС не открывается')
    def second_iis_rejected(self, invest_api, backoffice_token, client):
        with reporting.step('Открыть клиенту ИИС'):
            open_agreement(invest_api, backoffice_token, client['id'], 'IIS')

        with reporting.step('Попробовать открыть второй ИИС'):
            response = invest_api.open_agreement(client['id'], 'IIS', backoffice_token)
            print(response.status_code, response.text)

        with reporting.step('Проверить, что второй ИИС не открыт'):
            assert_that(response.status_code, is_not(201), 'Второй ИИС не должен открываться')
