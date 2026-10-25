"""ОП-07 Выписка по счёту за 12 месяцев. Дефекты: 07.1–07.5. Ловушка: Response Timeout 60 000."""
import common
import jmx

FILE = '07-statement'


def plan(fixed):
    period = 'P-365D' if fixed else 'P-30D'  # 07.1
    children = [jmx.json_assertion('Выписка получена', '$.accountId', '${accountId}')]
    if not fixed:
        children.append(jmx.duration_assertion('Duration Assertion', 800))  # 07.3
    statement = jmx.http_request('GET /api/v1/accounts/{accountId}/statement', 'GET',
                                 '/api/v1/accounts/${accountId}/statement',
                                 params=[('from', f'${{__timeShift(yyyy-MM-dd,,{period},,)}}'),
                                         ('to', '${__time(yyyy-MM-dd,)}')], children=children)
    props = common.thread_props(8)
    if not fixed:
        props['threads'] = '${__P(threads,4)}'  # 07.2
    listeners = [common.backend()]
    if not fixed:
        listeners.append(jmx.summary_report('Summary Report'))  # 07.4
    name = 'ОП-07 Выписка по счёту за 12 месяцев' if fixed else 'Выписка'  # 07.5
    return jmx.test_plan('ОП-07 Выписка по счёту за 12 месяцев', variables={'pacing': '40000'}, children=[
        common.defaults(response_timeout=60000),
        common.headers(),
        *listeners,
        jmx.thread_group('Thread Group', **props, children=[
            common.start(),
            common.login('users_op07.csv'),
            common.data('accounts.csv'),
            jmx.transaction(name, children=[common.auth(), statement]),
            common.pacing(),
        ]),
    ])
