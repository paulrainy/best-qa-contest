"""ОП-01 Поиск клиента по паспорту. Дефекты: 01.1–01.5 (см. раскладку в ключе)."""
import common
import jmx

FILE = '01-client-search'

BROKEN_PACING = '''// Пейсинг 15 с между итерациями
return Long.parseLong(vars.get('pacing'))'''


def plan(fixed):
    props = common.thread_props(42)
    if not fixed:
        props['rampup'] = '${__P(rampup,1)}'  # 01.1
    if fixed:
        check = jmx.json_assertion('Клиент найден', '$.clients[0].clientId', '${clientId}')
    else:
        check = jmx.response_assertion('Код 200', ['200'], field=jmx.RESPONSE_CODE, test_type=jmx.EQUALS)  # 01.3
    search = jmx.http_request('POST /api/v1/clients/search', 'POST', '/api/v1/clients/search',
                              body='{"documentType": "PASSPORT_RF", "passport": "${passport}"}',
                              keep_alive=fixed, children=[check])  # 01.2
    listeners = [common.backend()]
    if not fixed:
        listeners.append(jmx.view_results_tree('View Results Tree'))  # 01.5
    return jmx.test_plan('ОП-01 Поиск клиента по паспорту', variables={'pacing': '15000'}, children=[
        common.defaults(),
        common.headers(),
        *listeners,
        jmx.thread_group('Thread Group', **props, children=[
            common.start(),
            common.login('users_op01.csv'),
            common.data('clients.csv'),
            jmx.transaction('ОП-01 Поиск клиента по паспорту', children=[common.auth(), search]),
            common.pacing() if fixed else common.pacing(BROKEN_PACING),  # 01.4
        ]),
    ])
