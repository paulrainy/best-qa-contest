from hamcrest import assert_that, contains_string, equal_to, greater_than, is_not

from framework.reporting import Reporting as reporting
from invest.steps.clients import open_agreement


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Договоры')
class TestSecondIis:

    @reporting.id(900302)
    @reporting.title('Второй ИИС не открывается')
    def second_iis_rejected(self, invest_api, invest_db, backoffice_token, client):
        with reporting.step('Открыть клиенту ИИС'):
            first_iis = open_agreement(invest_api, backoffice_token, client['id'], 'IIS')
            assert_that(first_iis['clientId'], equal_to(client['id']), 'Клиент первого ИИС')
            assert_that(first_iis['type'], equal_to('IIS'), 'Тип первого договора')
            assert_that(first_iis['status'], equal_to('ACTIVE'), 'Статус первого ИИС')

        with reporting.step('Проверить предусловие в БД'):
            agreements_before = invest_db.get_agreements(client['id'])
            assert_that(len(agreements_before), equal_to(1), 'Число договоров до запроса')
            assert_that(agreements_before[0]['id'], equal_to(first_iis['id']), 'Первый ИИС в БД')

        with reporting.step('Попробовать открыть второй ИИС'):
            response = invest_api.open_agreement(client['id'], 'IIS', backoffice_token)
            print(response.status_code, response.text)

        with reporting.step('Проверить отказ'):
            assert_that(response.status_code, is_not(201), 'Второй ИИС не должен открываться')
            assert_that(response.json()['errorMessage'], contains_string('ИИС'), 'Текст ошибки')

        with reporting.step('Проверить договоры клиента после отказа'):
            agreements_after = invest_db.get_agreements(client['id'])
            iis = [a for a in agreements_after if a['type'] == 'IIS']
            assert_that(len(iis), greater_than(0), 'Число ИИС после отказа')
            first_after = next(a for a in iis if a['id'] == first_iis['id'])
            assert_that(first_after['status'], equal_to('ACTIVE'), 'Первый ИИС остался действующим')
            assert_that(first_after['number'], equal_to(first_iis['number']), 'Номер первого ИИС не изменился')
