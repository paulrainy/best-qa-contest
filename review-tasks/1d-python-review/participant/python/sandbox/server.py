"""HTTP API сервиса брокерского обслуживания (invest-api)."""
import json
import logging
import re
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CABINET = Path(__file__).parent / 'cabinet'
CONTENT_TYPES = {'.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css'}

from sandbox.db import Database
from sandbox.kafka import CLUSTER_ID, TOPICS, Broker, KafkaError
from sandbox.service import ApiError, InvestService, background

log = logging.getLogger('sandbox')

# (метод, шаблон пути, кто вызывает, обработчик)
ROUTES = [
    ('POST', r'/api/v1/backoffice/login', None, lambda s, _, b: s.backoffice_login(b.get('login'), b.get('password'))),
    ('POST', r'/api/v1/auth/login', None, lambda s, _, b: s.client_login(b.get('login'), b.get('password'))),
    ('POST', r'/api/v1/clients', 'backoffice', lambda s, _, b: (201, s.create_client(b))),
    ('GET', r'/api/v1/clients/(\d+)', 'backoffice', lambda s, m, _: s.describe_client(int(m[1]))),
    ('POST', r'/api/v1/clients/(\d+)/agreements', 'backoffice', lambda s, m, b: (201, s.open_agreement(int(m[1]), b))),
    ('GET', r'/api/v1/profile', 'client', lambda s, m, _: s.describe_client(m.client)),
    ('GET', r'/api/v1/agreements', 'client', lambda s, m, _: s.agreements(m.client)),
    ('GET', r'/api/v1/agreements/(\d+)/orders', 'client', lambda s, m, _: s.orders(m.client, int(m[1]))),
    ('GET', r'/api/v1/tax-reports', 'client', lambda s, m, _: s.tax_reports(m.client)),
    ('GET', r'/api/v1/agreements/(\d+)', 'client', lambda s, m, _: s.agreement(m.client, int(m[1]))),
    ('POST', r'/api/v1/agreements/(\d+)/refill', 'client', lambda s, m, b: (201, s.refill(m.client, int(m[1]), b))),
    ('POST', r'/api/v1/agreements/(\d+)/withdraw', 'client', lambda s, m, b: (201, s.withdraw(m.client, int(m[1]), b))),
    ('POST', r'/api/v1/agreements/(\d+)/close', 'client', lambda s, m, _: s.close_agreement(m.client, int(m[1]))),
    ('GET', r'/api/v1/orders/(\d+)', 'client', lambda s, m, _: s.order(m.client, int(m[1]))),
    ('POST', r'/api/v1/tax-reports', 'client', lambda s, m, b: (201, s.order_tax_report(m.client, b))),
    ('GET', r'/api/v1/tax-reports/(\d+)', 'client', lambda s, m, _: s.tax_report(m.client, int(m[1]))),
    ('PATCH', r'/api/v1/profile/tariff', 'client', lambda s, m, b: s.change_tariff(m.client, b)),
]


class Match:
    def __init__(self, match, client=None):
        self.match = match
        self.client = client

    def __getitem__(self, i):
        return self.match[i]


def make_handler(service: InvestService):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def do_GET(self):
            self.dispatch('GET')

        def do_POST(self):
            self.dispatch('POST')

        def do_PATCH(self):
            self.dispatch('PATCH')

        def dispatch(self, method):
            path = self.path.split('?')[0]
            try:
                length = int(self.headers.get('Content-Length') or 0)
                raw = self.rfile.read(length) if length else b''
                body = json.loads(raw) if raw else {}
                if method == 'GET' and (path == '/cabinet' or path.startswith('/cabinet/')):
                    return self.static(path)
                if path == '/health':
                    return self.send(200, {'service': 'invest-api', 'status': 'UP'})
                if path.startswith('/qa-service/'):
                    return self.qa_service(method, path, body)
                for m, pattern, role, handler in ROUTES:
                    match = re.fullmatch(pattern, path)
                    if m != method or not match:
                        continue
                    token = (self.headers.get('Authorization') or '').removeprefix('Bearer ').strip()
                    ctx = Match(match)
                    if role == 'backoffice':
                        service.backoffice_user(token)
                    elif role == 'client':
                        ctx.client = service.client_id(token)
                    time.sleep(0.1)
                    result = handler(service, ctx, body)
                    status, payload = result if isinstance(result, tuple) else (200, result)
                    return self.send(status, payload)
                raise ApiError(404, 'NOT_FOUND', f'Неизвестный метод API: {method} {path}')
            except ApiError as e:
                self.send(e.status, {'errorCode': e.code, 'errorMessage': e.message})
            except json.JSONDecodeError:
                self.send(400, {'errorCode': 'BAD_REQUEST', 'errorMessage': 'Тело запроса — не JSON'})
            except Exception as e:  # noqa: BLE001
                log.exception('Ошибка песочницы: %s %s', method, path)
                self.send(500, {'errorCode': 'INTERNAL_ERROR', 'errorMessage': str(e)})

        def qa_service(self, method, path, body):
            """HTTP-шлюз к Kafka, как QA Service на стендах банка."""
            try:
                if method == 'GET' and path == '/qa-service/api/kafka/clusters':
                    return self.send(200, {'clusters': [{'id': CLUSTER_ID, 'topics': list(TOPICS)}]})
                if body.get('cluster_id') != CLUSTER_ID:
                    raise KafkaError(404, f"Cluster '{body.get('cluster_id')}' not found")
                if method == 'POST' and path == '/qa-service/api/kafka/subscribe':
                    now = int(time.time())
                    seconds_ago = int(body.get('seconds_ago') or 60)
                    messages = service.kafka.read(body.get('topic'), body.get('from_timestamp', now - seconds_ago),
                                                  body.get('to_timestamp', now), int(body.get('limit') or 100))
                    return self.send(200, {'messages': messages})
                if method == 'POST' and path == '/qa-service/api/kafka/send':
                    message = service.kafka.publish(body.get('topic'), body.get('key'), body.get('value'))
                    return self.send(200, {'partition': message['partition'], 'offset': message['offset']})
                raise KafkaError(404, f'Unknown QA Service method: {method} {path}')
            except KafkaError as e:
                self.send(e.status, {'error': e.message})

        def static(self, path):
            """Веб-кабинет инвестора: одна страница и её скрипт."""
            name = path.removeprefix('/cabinet').strip('/') or 'index.html'
            file = CABINET / name
            if not file.is_file() or file.parent != CABINET:
                file = CABINET / 'index.html'
            data = file.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPES.get(file.suffix, 'text/plain') + '; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def send(self, status, payload):
            data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt, *args):
            log.debug('%s %s', self.address_string(), fmt % args)

    return Handler


def port_busy(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(('localhost', port)) == 0


def start(port: int, db_path: Path) -> ThreadingHTTPServer:
    service = InvestService(Database(db_path), Broker())
    server = ThreadingHTTPServer(('localhost', port), make_handler(service))
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, name='invest-api', daemon=True).start()
    threading.Thread(target=background(0.2, service.execute_orders), name='orders', daemon=True).start()
    threading.Thread(target=background(1.0, service.stand_activity), name='stand', daemon=True).start()
    threading.Thread(target=background(0.5, service.consume), name='consumer', daemon=True).start()
    return server
