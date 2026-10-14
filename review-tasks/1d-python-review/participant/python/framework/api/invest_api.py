"""Клиент API сервиса брокерского обслуживания (invest-api). Методы возвращают requests.Response как есть."""
import json
import logging

import allure
import requests

from framework.config import Config

log = logging.getLogger('invest_api')


class InvestApi:

    def __init__(self, host: str = None, timeout: int = 30):
        self.host = (host or Config.api_url()).rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({'accept': 'application/json', 'Content-Type': 'application/json'})

    def _request(self, method: str, path: str, token: str = None, body: dict = None) -> requests.Response:
        headers = {'Authorization': f'Bearer {token}'} if token else {}
        response = self.session.request(method, self.host + path, json=body, headers=headers, timeout=self.timeout)
        log.info('%s %s -> %s %s', method, path, response.status_code, response.text[:500])
        allure.attach(
            f'{method} {self.host}{path}\n\n{json.dumps(body, ensure_ascii=False, indent=2) if body else ""}'
            f'\n\nОтвет {response.status_code}:\n{response.text}',
            name=f'{method} {path}', attachment_type=allure.attachment_type.TEXT)
        return response

    # авторизация
    def backoffice_login(self, login: str, password: str) -> requests.Response:
        return self._request('POST', '/api/v1/backoffice/login', body={'login': login, 'password': password})

    def client_login(self, login: str, password: str) -> requests.Response:
        return self._request('POST', '/api/v1/auth/login', body={'login': login, 'password': password})

    # бэк-офис
    def create_client(self, body: dict, token: str) -> requests.Response:
        return self._request('POST', '/api/v1/clients', token, body)

    def get_client(self, client_id: int, token: str) -> requests.Response:
        return self._request('GET', f'/api/v1/clients/{client_id}', token)

    def open_agreement(self, client_id: int, agreement_type: str, token: str) -> requests.Response:
        return self._request('POST', f'/api/v1/clients/{client_id}/agreements', token, {'type': agreement_type})

    # клиент
    def get_profile(self, token: str) -> requests.Response:
        return self._request('GET', '/api/v1/profile', token)

    def get_agreements(self, token: str) -> requests.Response:
        return self._request('GET', '/api/v1/agreements', token)

    def get_agreement(self, agreement_id: int, token: str) -> requests.Response:
        return self._request('GET', f'/api/v1/agreements/{agreement_id}', token)

    def refill(self, agreement_id: int, amount, token: str) -> requests.Response:
        return self._request('POST', f'/api/v1/agreements/{agreement_id}/refill', token, {'amount': str(amount)})

    def withdraw(self, agreement_id: int, amount, token: str) -> requests.Response:
        return self._request('POST', f'/api/v1/agreements/{agreement_id}/withdraw', token, {'amount': str(amount)})

    def close_agreement(self, agreement_id: int, token: str) -> requests.Response:
        return self._request('POST', f'/api/v1/agreements/{agreement_id}/close', token)

    def get_order(self, order_id: int, token: str) -> requests.Response:
        return self._request('GET', f'/api/v1/orders/{order_id}', token)

    def order_tax_report(self, tax_period: int, token: str) -> requests.Response:
        return self._request('POST', '/api/v1/tax-reports', token, {'taxPeriod': tax_period})

    def get_tax_reports(self, token: str) -> requests.Response:
        return self._request('GET', '/api/v1/tax-reports', token)

    def get_tax_report(self, report_id: int, token: str) -> requests.Response:
        return self._request('GET', f'/api/v1/tax-reports/{report_id}', token)

    def change_tariff(self, tariff: str, token: str) -> requests.Response:
        return self._request('PATCH', '/api/v1/profile/tariff', token, {'tariff': tariff})
