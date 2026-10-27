"""Подключения к стенду: HTTP API, брокер, БД. Каркас — меняйте как удобно."""
import configparser
import json
import time
from pathlib import Path

import pika
import psycopg
import requests

_cfg = configparser.ConfigParser()
_cfg.read(Path(__file__).with_name("stand.ini"), encoding="utf-8")
CFG = _cfg["stand"]


class Api:
    def __init__(self):
        self.base = CFG["api_url"]
        self.session = requests.Session()

    def get(self, path, **kw):
        return self.session.get(self.base + path, timeout=30, **kw)

    def post(self, path, body=None, **kw):
        return self.session.post(self.base + path, json=body, timeout=30, **kw)

    def put(self, path, body=None, **kw):
        return self.session.put(self.base + path, json=body, timeout=30, **kw)

    def delete(self, path, **kw):
        return self.session.delete(self.base + path, timeout=30, **kw)


def amqp():
    return pika.BlockingConnection(pika.URLParameters(CFG["amqp_url"]))


def db():
    """Подключение к БД стенда по протоколу PostgreSQL (только чтение)."""
    return psycopg.connect(CFG["db_dsn"], autocommit=True)


class Events:
    """Подписка на события обменника transfers через временную очередь. Создавайте ДО действия."""

    def __init__(self, channel, routing_key="transfer.#"):
        self.channel = channel
        self.queue = channel.queue_declare("", exclusive=True, auto_delete=True).method.queue
        channel.queue_bind(self.queue, "transfers", routing_key)

    def wait(self, match, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            method, props, body = self.channel.basic_get(self.queue, auto_ack=True)
            if body is None:
                time.sleep(0.1)
                continue
            event = json.loads(body)
            if match(event):
                return event
        raise AssertionError(f"событие не пришло за {timeout} с")
