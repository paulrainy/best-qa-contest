"""ОП-08 Запрос остатка в АБС, SOAP, открытая модель. Дефекты: Д08.1–Д08.5, номера из ключа. Ловушка: Precise Throughput Timer."""
import common
import jmx

FILE = '08-cft-balance'

ENVELOPE = '''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:acc="http://cft.efr.example/account">
  <soapenv:Header/>
  <soapenv:Body>
    <acc:GetAccountBalanceRequest>
      <acc:AccountNumber>${accountNumber}</acc:AccountNumber>
      <acc:RequestTime>${requestTime}</acc:RequestTime>
      <acc:RequestId>${__UUID()}</acc:RequestId>
    </acc:GetAccountBalanceRequest>
  </soapenv:Body>
</soapenv:Envelope>'''

TIME_FIXED = '''// Время запроса для АБС, с часовым поясом
vars.put('requestTime', java.time.OffsetDateTime.now().toString())'''

# JMeter подставляет функцию в текст до компиляции, Groovy видит готовую строку в двойных кавычках:
# скрипт компилируется и кэшируется со временем первого вызова (Д08.4, проверено в JMeter 5.6.3).
TIME_BROKEN = '''// Время запроса для АБС
vars.put('requestTime', "${__time(yyyy-MM-dd'T'HH:mm:ss.SSSXXX,)}")'''


def plan(fixed):
    if fixed:
        checks = [jmx.response_assertion('ResultCode 0', ['<ResultCode>0</ResultCode>']),
                  jmx.response_assertion('Нет soap:Fault', ['Fault>'], test_type=jmx.SUBSTRING | jmx.NOT)]
    else:
        checks = [jmx.response_assertion('ResultCode', ['<ResultCode>'])]  # Д08.5
    balance = jmx.http_request('POST /cft/AccountService', 'POST', '/cft/AccountService', body=ENVELOPE, children=[
        jmx.jsr223('pre', 'Время запроса', TIME_FIXED if fixed else TIME_BROKEN),  # Д08.4
        *checks,
    ])
    headers = [('Content-Type', 'text/xml; charset=UTF-8' if fixed else 'application/xml')]  # Д08.1
    if fixed:
        headers.append(('SOAPAction', 'GetAccountBalance'))  # Д08.2
    else:
        headers.append(('Authorization', 'Basic bnRfY2Z0Ok50LUNmdC0yMDI2'))  # Д08.3
    headers.append(('X-Request-Id', '${__UUID()}'))
    config = [common.defaults(domain='${__P(cft.host)}', port='${__P(cft.port,8443)}'),
              jmx.header_manager('HTTP Header Manager', headers)]
    if fixed:
        config.append(jmx.auth_manager('HTTP Authorization Manager', 'https://${__P(cft.host)}', 'nt_cft',
                                       '${__P(cft.password)}'))
    return jmx.test_plan('ОП-08 Запрос остатка в АБС', children=[
        *config,
        common.backend(),
        jmx.thread_group('Thread Group', **common.thread_props(20), children=[
            jmx.precise_throughput_timer('Precise Throughput Timer', 7200, duration='${__P(duration,3600)}'),
            common.data('accounts.csv'),
            jmx.transaction('ОП-08 Запрос остатка в АБС', children=[balance]),
        ]),
    ])
