"""ОП-10 Проверка клиента по спискам финмониторинга, подпись в JSR223. Дефекты: 10.1–10.5."""
import common
import jmx

FILE = '10-fm-check'

BODY = '{"clientId": "${clientId}", "passport": "${passport}", "lists": ["TERRORISM", "MVK"]}'

SIGN_FIXED = '''// X-Signature: HMAC-SHA256 тела запроса на ключе fm.key, в hex (методика 7.11)
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

String body = sampler.getArguments().getArgument(0).getValue()
Mac mac = Mac.getInstance('HmacSHA256')
mac.init(new SecretKeySpec(props.get('fm.key').getBytes('UTF-8'), 'HmacSHA256'))
vars.put('signature', mac.doFinal(body.getBytes('UTF-8')).encodeHex().toString())'''

SIGN_BROKEN = '''// X-Signature: HMAC-SHA256 тела запроса на ключе fm.key, в hex
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

String body = '{"clientId": "${clientId}", "passport": "${passport}", "lists": ["TERRORISM", "MVK"]}'
Mac mac = Mac.getInstance('HmacSHA256')
mac.init(new SecretKeySpec(props.get('fm.key').getBytes('UTF-8'), 'HmacSHA256'))
vars.put('signature', mac.doFinal(body.getBytes('UTF-8')).encodeHex().toString())'''


def plan(fixed):
    if fixed:
        check = jmx.json_assertion('Решение получено', '$.decision', 'CLEAR|MATCH', regex=True)
    else:
        check = jmx.response_assertion('Код 200', ['200'], field=jmx.RESPONSE_CODE, test_type=jmx.EQUALS)  # 10.3
    request = jmx.http_request('POST /api/v1/fm/check', 'POST', '/api/v1/fm/check', body=BODY,
                               keep_alive=fixed, children=[  # 10.5
                                   jmx.jsr223('pre', 'Подпись', SIGN_FIXED if fixed else SIGN_BROKEN,
                                              cache=fixed),  # 10.1, 10.2
                                   jmx.header_manager('Подпись запроса', [('X-Signature', '${signature}')]),
                                   check,
                               ])
    props = common.thread_props(5)
    if not fixed:
        props['rampup'] = '${__P(rampup,1)}'  # 10.4
    return jmx.test_plan('ОП-10 Проверка по спискам финмониторинга', variables={'pacing': '10000'}, children=[
        common.defaults(),
        common.headers(),
        common.backend(),
        jmx.thread_group('Thread Group', **props, children=[
            common.start(),
            common.login('users_op10.csv'),
            common.data('clients.csv'),
            jmx.transaction('ОП-10 Проверка по спискам финмониторинга', children=[common.auth(), request]),
            common.pacing(),
        ]),
    ])
