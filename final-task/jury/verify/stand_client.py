"""Минимальный HTTP-клиент служебных проверок; только стандартная библиотека."""
import json
import time
import uuid
from decimal import Decimal
from urllib.request import Request, urlopen
from urllib.error import HTTPError


class Client:
    def __init__(self, base='http://localhost:18400'):
        self.base = base

    def call(self, method, path, body=None, status=200, headers=None):
        data = None if body is None else json.dumps(body).encode()
        req = Request(self.base + path, data=data, method=method, headers={'Content-Type': 'application/json', **(headers or {})})
        try:
            response = urlopen(req, timeout=30)
        except HTTPError as exc:
            response = exc
        with response:
            raw = response.read().decode()
            assert response.status == status, f'{method} {path}: HTTP {response.status}, expected {status}: {raw}'
            return json.loads(raw, parse_float=Decimal)

    def account(self, client=None, balance=1000000):
        body = {'balance': balance}
        if client: body['clientId'] = client
        return self.call('POST', '/api/test/accounts', body, 201)

    def transfer(self, a, b, amount, key=None):
        return self.call('POST', '/api/v1/transfers', {'fromAccount': a['accountNumber'], 'toAccount': b['accountNumber'], 'amount': amount}, 202, {'Idempotency-Key': key or str(uuid.uuid4())})

    def final(self, transfer):
        identity = transfer['transferId']
        until = time.monotonic() + 10
        while time.monotonic() < until:
            result = self.call('GET', '/api/v1/transfers/' + identity)
            if result['status'] in ('COMPLETED', 'FAILED'): return result
            time.sleep(.03)
        raise AssertionError('timeout transferId=' + identity)

    def balance(self, account):
        return self.call('GET', '/api/v1/accounts/' + account['accountNumber'])['balance']
