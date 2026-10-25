"""ОП-03 Создание клиента, одноразовые данные. Дефекты: 03.1–03.5. 03.1 — в data/new_clients.csv (5 000 строк)."""
import common
import jmx

FILE = '03-client-create'

BODY = '''{
  "lastName": "${lastName}",
  "firstName": "${firstName}",
  "middleName": "${middleName}",
  "birthDate": "${birthDate}",
  "gender": "MALE",
  "passport": "${passport}",
  "mobilePhone": "${phone}"
}'''


def plan(fixed):
    if fixed:
        check = jmx.json_assertion('Клиент создан', '$.status', 'ACTIVE')
    else:
        check = jmx.response_assertion('Ответ получен', ['"status"'], assume_success=True)  # 03.2
    create = jmx.http_request('POST /api/v1/clients', 'POST', '/api/v1/clients', body=BODY, children=[check])
    props = common.thread_props(8)
    if not fixed:
        props['duration'] = 3600  # 03.5
    if fixed:
        entry = [common.login('users_op03.csv')]
    else:
        # 03.4: вход в каждой итерации, учётки по кругу
        entry = [common.data('users_op03.csv'), common.login_request()]
    tail = [] if fixed else [jmx.debug_sampler('Debug Sampler')]  # 03.3
    return jmx.test_plan('ОП-03 Создание клиента', variables={'pacing': '20000'}, children=[
        common.defaults(),
        common.headers(),
        common.backend(),
        jmx.thread_group('Thread Group', **props, children=[
            common.start(),
            *entry,
            common.data('new_clients.csv', recycle=False, stop_thread=True),
            jmx.transaction('ОП-03 Создание клиента', children=[common.auth(), create]),
            *tail,
            common.pacing(),
        ]),
    ])
