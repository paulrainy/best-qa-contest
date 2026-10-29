import re

import pytest
from hamcrest import assert_that, equal_to, has_length

from framework.reporting import Reporting as reporting


@reporting.epic('Брокерское обслуживание')
@reporting.feature('Договоры')
class TestOpenAgreement:

    @pytest.mark.smoke
    @reporting.id(900301)
    @reporting.title('Открытие брокерского договора новому клиенту')
    def test_open_broker_agreement(self, invest_api, invest_db, backoffice_token, client):
        with reporting.step('Проверить созданного клиента'):
            db_client = invest_db.get_client_by_login(client['login'])
            assert db_client is not None, f"Клиента {client['login']} нет в БД"
            assert_that(db_client['status'], equal_to('ACTIVE'), 'Статус клиента')
            assert_that(client['tariff'], equal_to('INVESTOR'), 'Тариф нового клиента')

        with reporting.step('Открыть клиенту брокерский договор'):
            response = invest_api.open_agreement(client['id'], 'BROKER', backoffice_token)
            assert response.status_code == 201
            agreement = response.json()

        with reporting.step('Проверить договор в ответе'):
            assert re.fullmatch(r'БД-\d{7}', agreement['number']), f"Номер договора: {agreement['number']}"
            assert_that(agreement['status'], equal_to('ACTIVE'), 'Статус договора')

        with reporting.step('Проверить договор и счёт в БД'):
            agreements = invest_db.get_agreements(client['id'])
            assert_that(agreements, has_length(1), 'У нового клиента должен быть один договор')
            assert_that(agreements[0]['status'], equal_to('ACTIVE'), 'Статус договора в БД')
            account = invest_db.get_account(agreement['id'])
            assert_that(account['balance'], equal_to(0), 'Остаток на новом счёте')
