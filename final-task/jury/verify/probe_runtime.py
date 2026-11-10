#!/usr/bin/env python3
"""Проверяет готовый процесс: HTTP, AMQP, H2-консоль, PG SELECT и запрет записи."""
import argparse
import json
import sys
from urllib.request import Request, urlopen
import base64
import pika
import psycopg
from stand_client import Client


def probe():
    api = Client()
    assert api.call('GET', '/api/v1/health')['status'] == 'UP'
    api.call('POST', '/api/test/reset', {})
    with urlopen('http://localhost:18400/metrics', timeout=10) as r:
        assert b'stand_db_transfers_rows 30000' in r.read()
    connection = pika.BlockingConnection(pika.URLParameters('amqp://guest:guest@localhost:5672/%2F'))
    try:
        ch = connection.channel()
        queue = ch.queue_declare('', exclusive=True, auto_delete=True).method.queue
        ch.queue_bind(queue, 'transfers', routing_key='probe.runtime')
        ch.basic_publish('transfers', 'probe.runtime', b'runtime-ok')
        method, properties, body = ch.basic_get(queue, auto_ack=True)
        assert method is not None and body == b'runtime-ok'
    finally:
        connection.close()
    with psycopg.connect('host=localhost port=19402 dbname=stand user=qa password=qa sslmode=disable', autocommit=True) as db:
        assert db.execute('SELECT COUNT(*) FROM transfers').fetchone()[0] == 30000
        try:
            db.execute("UPDATE accounts SET balance=balance WHERE account_number='40817810000000000011'")
        except psycopg.Error:
            pass
        else:
            raise AssertionError('PG connection permits writes')
    for url, content in [('http://localhost:19401/', b'H2'), ('http://localhost:15672/', b'dojo')]:
        auth = base64.b64encode(b'guest:guest').decode()
        with urlopen(Request(url, headers={'Authorization': 'Basic ' + auth}), timeout=10) as r:
            assert r.status == 200 and content.lower() in r.read().lower(), url
    # Загрузка самого архива Dojo проверяется статически; ресурс JS — через HTTP.
    with urlopen('http://localhost:15672/dojo/dojo/dojo.js', timeout=10) as r:
        assert r.status == 200 and len(r.read()) > 1000
    return {'python': sys.version.split()[0], 'health': 'UP', 'AMQP': 'publish/read', 'PG': 'SELECT only', 'consoles': 'H2+Qpid+Dojo', 'history': 30000}


if __name__ == '__main__':
    print(json.dumps(probe(), ensure_ascii=False))
