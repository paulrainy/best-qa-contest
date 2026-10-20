"""ОП-06 Закрытие вклада, одноразовые данные. Дефекты: 06.1–06.5."""
import common
import jmx

FILE = '06-deposit-close'

CLOSE_DATE_GROOVY = '''// Дата закрытия — сегодня
vars.put('closeDate', java.time.LocalDate.now().toString())'''

CLOSE_DATE_BEANSHELL = '''import java.text.SimpleDateFormat;
import java.util.Date;
vars.put("closeDate", new SimpleDateFormat("yyyy-MM-dd").format(new Date()));'''


def plan(fixed):
    deposit = jmx.http_request('GET /api/v1/deposits/{depositId}', 'GET', '/api/v1/deposits/${depositId}', children=[
        jmx.json_assertion('Вклад открыт', '$.status', 'ACTIVE'),
    ])
    close_children = [common.pause()]
    if fixed:
        close_children += [jmx.jsr223('pre', 'Дата закрытия', CLOSE_DATE_GROOVY),
                           jmx.json_assertion('Вклад закрыт', '$.status', 'CLOSED')]  # 06.2
    else:
        close_children.append(jmx.beanshell_pre('Дата закрытия', CLOSE_DATE_BEANSHELL))  # 06.4
    close = jmx.http_request('POST /api/v1/deposits/{depositId}/close', 'POST', '/api/v1/deposits/${depositId}/close',
                             body='{"reason": "CLIENT_REQUEST", "closeDate": "${closeDate}"}', children=close_children)
    steps = [common.login('users_op06.csv'),
             common.data('deposits_to_close.csv', recycle=not fixed, stop_thread=fixed),  # 06.1
             jmx.transaction('ОП-06 Закрытие вклада', children=[common.auth(), deposit, close])]
    if fixed:
        steps = [common.start(), *steps, common.pacing()]
    else:
        steps.insert(0, jmx.constant_throughput_timer('Constant Throughput Timer', 3.0))  # 06.3: 3 в минуту на поток
    return jmx.test_plan('ОП-06 Закрытие вклада', variables={'pacing': '20000'}, children=[
        common.defaults(embedded=not fixed),  # 06.5
        common.headers(),
        common.backend(),
        jmx.thread_group('Thread Group', **common.thread_props(10), children=steps),
    ])
