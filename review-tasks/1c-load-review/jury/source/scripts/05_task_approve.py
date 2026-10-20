"""ОП-05 Подтверждение операции контролёром. Дефекты: 05.1–05.5. 05.1 — в data/controllers.csv (6 строк)."""
import common
import jmx

FILE = '05-task-approve'

EXAMPLE = ('Пример ответа: {"tasks": [{"id": "TS-20261104-000187", "type": "DEPOSIT_OPEN", "status": "NEW", '
           '"client": {"id": "CL4471902300417", "fullName": "Петров Илья Сергеевич"}, "amount": 1500000.00}, …]}')


def plan(fixed):
    if fixed:
        task_id = jmx.json_extractor('JSON Extractor taskId', 'taskId', '$.tasks[*].id', default='taskId_NOT_FOUND',
                                     match_no='0')
    else:
        task_id = jmx.regex_extractor('Regex taskId', 'taskId', '"id":"(.+?)"', default='', match_no='0')  # 05.2, 05.3
    tasks = jmx.http_request('GET /api/v1/tasks', 'GET', '/api/v1/tasks', params=[('status', 'NEW')],
                             children=[task_id, jmx.json_assertion('Задачи получены', '$.tasks[0].id', validate=False)],
                             comment=EXAMPLE)
    take = jmx.http_request('POST /api/v1/tasks/{taskId}/take', 'POST', '/api/v1/tasks/${taskId}/take', body='{}',
                            children=[common.pause(),
                                      jmx.json_assertion('Задача взята', '$.status', 'IN_PROGRESS')])
    approve_children = [jmx.json_assertion('Операция подтверждена', '$.status', 'APPROVED')]
    if fixed:
        approve_children.insert(0, common.pause())  # 05.5
    approve = jmx.http_request('POST /api/v1/tasks/{taskId}/approve', 'POST', '/api/v1/tasks/${taskId}/approve',
                               body='{"comment": ""}', children=approve_children)
    steps = [common.start(), jmx.once_only('Вход', children=[
                 common.users('controllers.csv'), common.login_request()]),
             jmx.transaction('ОП-05 Подтверждение операции контролёром', children=[
                 common.auth(), tasks, take, approve])]
    if fixed:
        steps.append(common.pacing())  # 05.4
    else:
        steps = steps[1:]
    return jmx.test_plan('ОП-05 Подтверждение операции контролёром', variables={'pacing': '20000'}, children=[
        common.defaults(),
        common.headers(),
        common.backend(),
        jmx.thread_group('Thread Group', **common.thread_props(6), children=steps),
    ])
