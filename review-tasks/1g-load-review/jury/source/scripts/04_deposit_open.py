"""ОП-04 Открытие вклада: продукты, черновик, отправка. Дефекты: 04.1–04.5."""
import common
import jmx

FILE = '04-deposit-open'

AMOUNT_FIXED = '''// Сумма вклада: 40 % — больше 1 000 000 ₽, такие уходят контролёру (методика 2.4)
def rnd = new Random()
long amount = rnd.nextInt(100) < 40 ? 1_000_001 + rnd.nextInt(4_000_000) : 50_000 + rnd.nextInt(950_001)
vars.put('amount', String.valueOf(amount))'''

AMOUNT_BROKEN = '''// Сумма вклада от 50 000 до 1 000 000 ₽
def rnd = new Random()
long amount = 50_000 + rnd.nextInt(950_001)
vars.put('amount', String.valueOf(amount))'''

DRAFT = '''{
  "accountId": "${accountId}",
  "productCode": "${productCode}",
  "amount": ${amount},
  "currency": "RUB",
  "termMonths": 12
}'''


def plan(fixed):
    pause = common.pause() if fixed else common.pause(1000, 2000.0)  # 04.4
    products = jmx.http_request('GET /api/v1/deposits/products', 'GET', '/api/v1/deposits/products', children=[
        jmx.json_extractor('JSON Extractor productCode', 'productCode', "$.products[?(@.currency == 'RUB')].code",
                           default='productCode_NOT_FOUND' if fixed else None),  # 04.2
        jmx.json_assertion('Продукты получены', '$.products[0].code', validate=False),
    ])
    draft = jmx.http_request('POST /api/v1/deposits', 'POST', '/api/v1/deposits', body=DRAFT, children=[
        jmx.jsr223('pre', 'Сумма вклада', AMOUNT_FIXED if fixed else AMOUNT_BROKEN),  # 04.3
        pause,
        jmx.regex_extractor('Regex depositId', 'depositId',
                            '"depositId":"(.+?)"' if fixed else '"depositId":"(.+)"',  # 04.1
                            default='depositId_NOT_FOUND'),
        jmx.json_assertion('Черновик создан', '$.status', 'DRAFT'),
    ])
    submit = jmx.http_request('POST /api/v1/deposits/{depositId}/submit', 'POST',
                              '/api/v1/deposits/${depositId}/submit', body='{}', children=[
                                  common.pause() if fixed else common.pause(1000, 2000.0),
                                  jmx.json_assertion('Вклад отправлен', '$.status', 'ACTIVE|ON_APPROVAL', regex=True),
                              ])
    return jmx.test_plan('ОП-04 Открытие вклада', variables={'pacing': '20000'}, children=[
        common.defaults(),
        common.headers(),
        common.backend(),
        jmx.thread_group('Thread Group', **common.thread_props(16), children=[
            common.start(),
            common.login('users_op04.csv'),
            common.data('accounts.csv'),
            jmx.transaction('ОП-04 Открытие вклада', parent=fixed, children=[  # 04.5
                common.auth(), products, draft, submit]),
            common.pacing(),
        ]),
    ])
