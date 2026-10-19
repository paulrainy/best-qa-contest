"""ОП-09 Отчёт отделения за день, JDBC. Дефекты: 09.1–09.5."""
import common
import jmx

FILE = '09-branch-report'

QUERY = '''SELECT o.operation_type, o.status, count(*) AS cnt, sum(o.amount) AS total
FROM operations o
WHERE o.branch_id = ?
  AND o.created_at >= ?::date
  AND o.created_at <  ?::date + interval '1 day'
GROUP BY o.operation_type, o.status
ORDER BY o.operation_type, o.status'''

QUERY_INLINE = '''SELECT o.operation_type, o.status, count(*) AS cnt, sum(o.amount) AS total
FROM operations o
WHERE o.branch_id = ${branch_id}
  AND o.created_at >= '${op_date}'::date
  AND o.created_at <  '${op_date}'::date + interval '1 day'
GROUP BY o.operation_type, o.status
ORDER BY o.operation_type, o.status'''


def plan(fixed):
    if fixed:
        report = jmx.jdbc_request('SELECT отчёт отделения', 'efr', QUERY, query_type='Prepared Select Statement',
                                  args='${branch_id},${op_date},${op_date}', types='INTEGER,DATE,DATE', children=[
                                      jmx.response_assertion('Отчёт получен', ['operation_type']),
                                  ])
    else:
        report = jmx.jdbc_request('SELECT отчёт отделения', 'efr', QUERY_INLINE,
                                  query_type='Select Statement')  # 09.2, 09.4
    return jmx.test_plan('ОП-09 Отчёт отделения за день', variables={'pacing': '10000' if fixed else '1000'}, children=[  # 09.3
        jmx.user_variables('Дата отчёта', {'op_date': '${__timeShift(yyyy-MM-dd,,P-1D,,)}'}),
        jmx.jdbc_config('JDBC Connection Configuration', 'efr', 'jdbc:postgresql://${__P(db.host)}:5432/efr',
                        'efr_report' if fixed else 'efr', '${__P(db.password)}',  # 09.5
                        10 if fixed else 1),  # 09.1
        common.backend(),
        jmx.thread_group('Thread Group', **common.thread_props(3), children=[
            common.start(),
            common.data('branches.csv'),
            jmx.transaction('ОП-09 Отчёт отделения за день', children=[report]),
            common.pacing(),
        ]),
    ])
