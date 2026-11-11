import json
from contextlib import AbstractContextManager
from decimal import Decimal
from pathlib import Path

import requests


def encode_json(value):
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Сумма должна быть конечным числом")
        return format(value, "f")
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(k) + ":" + encode_json(v) for k, v in value.items()) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(encode_json(v) for v in value) + "]"
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def body(response):
    return response.json(parse_float=Decimal)


def require(response, status):
    assert response.status_code == status, (
        f"{response.request.method} {response.url}: HTTP{response.status_code}, "
        f"ожидался {status}: {response.text}")
    return body(response)


class Api(AbstractContextManager):
    def __init__(self, config, trace=None):
        self.base_url = config.http_url.rstrip("/")
        self.timeout_s = config.http_timeout_s
        self.trace = Path(trace) if trace else None
        self.session = requests.Session()

    def __exit__(self, *exc):
        self.session.close()

    def request(self, method, path, payload=None, *, key=None, raw=None):
        headers = {"Content-Type": "application/json"}
        if key is not None:
            headers["Idempotency-Key"] = key
        data = raw if raw is not None else (encode_json(payload) if payload is not None else None)
        response = self.session.request(method, self.base_url + path, headers=headers,
                                        data=data.encode("utf-8") if data is not None else None,
                                        timeout=self.timeout_s)
        if self.trace:
            self.trace.parent.mkdir(parents=True, exist_ok=True)
            with self.trace.open("a", encoding="utf-8") as output:
                output.write(encode_json({"method": method, "path": path, "key": key,
                                          "request": data, "status": response.status_code,
                                          "response": response.text}) + "\n")
        return response

    def get(self, path):
        return require(self.request("GET", path), 200)

    def post(self, path, payload=None):
        return require(self.request("POST", path, payload), 200)

    def put(self, path, payload):
        return require(self.request("PUT", path, payload), 200)

    def delete(self, path):
        return require(self.request("DELETE", path), 200)

    def create_account(self, balance=Decimal("1000000.00"), client_id=None, status="ACTIVE"):
        payload = {"balance": balance, "status": status}
        if client_id is not None:
            payload["clientId"] = client_id
        return require(self.request("POST", "/api/test/accounts", payload), 201)

    def transfer(self, src, dst, amount, key):
        return self.request("POST", "/api/v1/transfers",
                            {"fromAccount": src, "toAccount": dst, "amount": amount}, key=key)
