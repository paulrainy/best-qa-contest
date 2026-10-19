"""Общие части сценариев 1г — так, как требует методика. Отступления от неё задаются в самих сценариях."""
import jmx

PACING_SCRIPT = '''// Пейсинг: ждём остаток, чтобы итерация длилась ровно pacing мс (методика 3.1)
long pacing = Long.parseLong(vars.get('pacing'))
long started = Long.parseLong(vars.get('iterationStart'))
return Math.max(0L, pacing - (System.currentTimeMillis() - started))'''

START_SCRIPT = '''// Время начала итерации для пейсинга, в результаты не попадает
vars.put('iterationStart', String.valueOf(System.currentTimeMillis()))
SampleResult.setIgnore()'''


def thread_props(threads: int):
    """Число потоков, разгон и длительность через свойства, умолчания — из методики 3.2 и 3.4."""
    return dict(threads=f'${{__P(threads,{threads})}}', rampup=f'${{__P(rampup,{threads})}}',
                duration='${__P(duration,3600)}')


def defaults(connect_timeout=5000, response_timeout=30000, embedded=False, domain='${__P(efr.host)}',
             port='${__P(efr.port,443)}'):
    return jmx.http_defaults('HTTP Request Defaults', domain=domain, port=port, protocol='https',
                             connect_timeout=connect_timeout, response_timeout=response_timeout,
                             content_encoding='UTF-8', embedded=embedded)


def headers(request_id='${__UUID()}', content_type='application/json', extra=()):
    return jmx.header_manager('HTTP Header Manager', [('Content-Type', content_type), ('Accept', content_type),
                                                       ('X-Request-Id', request_id), *extra])


def auth():
    return jmx.header_manager('Authorization', [('Authorization', 'Bearer ${token}')])


def backend():
    return jmx.backend_listener_influx('Backend Listener', 'http://influxdb-nt:8086/write?db=jmeter',
                                       '${__P(application,efr-nt)}')


def start():
    return jmx.jsr223('sampler', 'Начало итерации', START_SCRIPT)


def login_request():
    return jmx.http_request('POST /api/v1/auth/login', 'POST', '/api/v1/auth/login',
                            body='{"login": "${login}", "password": "${password}"}', children=[
                                jmx.json_extractor('JSON Extractor token', 'token', '$.accessToken',
                                                   default='token_NOT_FOUND'),
                                jmx.json_assertion('Токен получен', '$.accessToken', validate=False),
                            ])


def users(file: str, name=None):
    return jmx.csv_data_set(name or file, f'data/{file}', recycle=False, stop_thread=True)


def login(users_file: str):
    """Вход один раз на поток (методика 7.4), учётка — из своего файла сценария (5.1)."""
    return jmx.once_only('Вход', children=[users(users_file), login_request()])


def pacing(script=PACING_SCRIPT):
    return jmx.flow_control_action('Пейсинг', children=[jmx.jsr223('timer', 'Остаток до пейсинга', script)])


def pause(delay=3000, range_=4000.0):
    """Пауза пользователя: по методике 3.3 — 3–7 с, ставится дочерним таймером запроса после паузы."""
    return jmx.uniform_random_timer('Пауза пользователя', delay, range_)


def data(file: str, recycle=True, stop_thread=False, share_mode='shareMode.all', name=None):
    return jmx.csv_data_set(name or file, f'data/{file}', recycle=recycle, stop_thread=stop_thread,
                            share_mode=share_mode)
