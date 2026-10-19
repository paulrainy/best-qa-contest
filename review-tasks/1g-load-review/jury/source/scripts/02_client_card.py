"""ОП-02 Просмотр карточки клиента. Дефекты: 02.1–02.5."""
import common
import jmx

FILE = '02-client-card'


def plan(fixed):
    card = jmx.http_request('GET /api/v1/clients/{clientId}', 'GET', '/api/v1/clients/${clientId}', children=[
        jmx.json_assertion('Карточка открыта', '$.clientId', '${clientId}'),
    ])
    accounts_children = [jmx.json_assertion('Счета получены', '$.accounts')]
    if fixed:
        accounts_children.insert(0, common.pause())
    accounts = jmx.http_request('GET /api/v1/clients/{clientId}/accounts', 'GET',
                                '/api/v1/clients/${clientId}/accounts', children=accounts_children)
    steps = [common.auth(), card, accounts]
    if not fixed:
        steps.append(common.pause())  # 02.2: таймер на уровне транзакции — пауза перед каждым запросом
    request_id = '${__UUID()}' if fixed else '7f3c2a9e-51d4-4b8e-9a1f-2c6d8e0b4f17'  # 02.5
    timeouts = {} if fixed else {'connect_timeout': None, 'response_timeout': None}  # 02.4
    return jmx.test_plan('ОП-02 Просмотр карточки клиента', variables={'pacing': '15000'}, children=[
        common.defaults(**timeouts),
        common.headers(request_id=request_id),
        common.backend(),
        jmx.thread_group('Thread Group', **common.thread_props(33), children=[
            common.start(),
            common.login('users_op02.csv'),
            common.data('clients.csv', share_mode='shareMode.all' if fixed else 'shareMode.thread'),  # 02.3
            jmx.transaction('ОП-02 Просмотр карточки клиента', include_timers=not fixed, children=steps),  # 02.1
            common.pacing(),
        ]),
    ])
