"""Дашборды Grafana 16–18 задания 1г. Запуск из папки tools:
.venv/bin/python ../1g-load-review/jury/source/monitoring/dashboards.py

Пишет participant/monitoring/NN-*.json (с дефектами) и jury/fixed/monitoring/NN-*.json (исправленные).
Дефекты помечены номерами из ключа. JSON сокращён до полей, которые влияют на вид и запросы.
"""
import json
from pathlib import Path

TASK = Path(__file__).resolve().parents[3]
INFLUX = {'type': 'influxdb', 'uid': 'influxdb-nt'}
PROM = {'type': 'prometheus', 'uid': 'prometheus-nt'}
ZABBIX = {'type': 'alexanderzobnin-zabbix-datasource', 'uid': 'zabbix-nt'}

APP = '"application" =~ /^$application$/'
OPS = '"transaction" =~ /^$transaction$/'
OP01 = 'ОП-01 Поиск клиента по паспорту'


class Board:
    def __init__(self):
        self.panels, self.y = [], 0

    def add(self, title, kind, datasource, targets, unit='short', width=12, height=8, custom=None, thresholds=None,
            options=None):
        last = self.panels[-1]['gridPos'] if self.panels else None
        x = last['x'] + last['w'] if last else 0
        if last and x + width > 24:
            x, self.y = 0, self.y + last['h']
        defaults = {'unit': unit}
        if custom:
            defaults['custom'] = custom
        if thresholds:
            defaults['thresholds'] = {'mode': 'absolute', 'steps': [{'color': 'green', 'value': None},
                                                                   {'color': 'red', 'value': thresholds}]}
        panel = {'id': len(self.panels) + 1, 'type': kind, 'title': title,
                 'gridPos': {'x': x, 'y': self.y, 'w': width, 'h': height}, 'datasource': datasource,
                 'fieldConfig': {'defaults': defaults, 'overrides': []},
                 'options': options or ({'legend': {'displayMode': 'table', 'placement': 'bottom',
                                                    'calcs': ['mean', 'max']}, 'tooltip': {'mode': 'multi'}}
                                        if kind == 'timeseries' else {}),
                 'targets': [{'refId': chr(ord('A') + n), 'datasource': datasource, **t} for n, t in enumerate(targets)]}
        self.panels.append(panel)


def dashboard(uid, title, tags, variables, board, time_from='now-6h'):
    return {'uid': uid, 'title': title, 'tags': tags, 'timezone': 'browser', 'schemaVersion': 39, 'version': 1,
            'editable': True, 'refresh': '30s', 'time': {'from': time_from, 'to': 'now'},
            'templating': {'list': variables}, 'annotations': {'list': []}, 'links': [], 'panels': board.panels}


def influx(query, alias='$tag_transaction', fmt='time_series'):
    return {'query': query, 'rawQuery': True, 'resultFormat': fmt, 'alias': alias}


def jmeter(fixed):
    b = Board()
    b.add('Активные потоки', 'timeseries', INFLUX, [influx(
        f'SELECT max("maxAT") FROM "jmeter" WHERE {APP} AND "transaction" = \'internal\' AND $timeFilter '
        'GROUP BY time($__interval) fill(null)', alias='Потоки')])
    time_filter = ' AND $timeFilter' if fixed else ''  # 16.4
    b.add('Интенсивность по операциям', 'timeseries', INFLUX, [influx(
        f'SELECT sum("count") FROM "jmeter" WHERE {APP} AND "statut" = \'all\' AND {OPS}{time_filter} '
        'GROUP BY time($__interval), "transaction" fill(0)')], unit='short')
    if fixed:
        mean = ('SELECT sum("w") / sum("c") FROM (SELECT "avg" * "count" AS "w", "count" AS "c" FROM "jmeter" '
                f'WHERE {APP} AND "statut" = \'ok\' AND {OPS} AND $timeFilter GROUP BY "transaction") '
                'WHERE $timeFilter GROUP BY time($__interval), "transaction" fill(null)')
    else:
        mean = (f'SELECT mean("avg") FROM "jmeter" WHERE {APP} AND "statut" = \'ok\' AND {OPS} AND $timeFilter '
                'GROUP BY time($__interval), "transaction" fill(null)')  # 16.1
    b.add('Среднее время отклика', 'timeseries', INFLUX, [influx(mean)], unit='ms')
    b.add('95-й перцентиль по окнам', 'timeseries', INFLUX, [influx(
        f'SELECT max("pct95.0") FROM "jmeter" WHERE {APP} AND "statut" = \'ok\' AND {OPS} AND $timeFilter '
        'GROUP BY time($__interval), "transaction" fill(null)')], unit='ms')
    if not fixed:  # 16.2
        b.add('95-й перцентиль за тест', 'stat', INFLUX, [influx(
            f'SELECT mean("pct95.0") FROM "jmeter" WHERE {APP} AND "statut" = \'ok\' AND {OPS} AND $timeFilter '
            'GROUP BY "transaction"')], unit='ms',
            options={'reduceOptions': {'calcs': ['lastNotNull'], 'fields': '', 'values': False},
                     'textMode': 'value_and_name', 'colorMode': 'value'})
    b.add('95-й перцентиль ОП-01', 'timeseries', INFLUX, [influx(
        f'SELECT max("pct95.0") FROM "jmeter" WHERE {APP} AND "statut" = \'ok\' AND "transaction" = \'{OP01}\' '
        'AND $timeFilter GROUP BY time($__interval) fill(null)', alias='p95 ОП-01')], unit='ms',
        custom={'thresholdsStyle': {'mode': 'line'}}, thresholds=800 if fixed else 1000)  # 16.5
    status = 'ko' if fixed else 'ok'  # 16.3
    b.add('Ошибки по операциям', 'timeseries', INFLUX, [influx(
        f'SELECT sum("count") FROM "jmeter" WHERE {APP} AND "statut" = \'{status}\' AND {OPS} AND $timeFilter '
        'GROUP BY time($__interval), "transaction" fill(0)')], unit='short')
    b.add('Таблица операций', 'table', INFLUX, [
        influx(f'SELECT sum("count") AS "Запросов" FROM "jmeter" WHERE {APP} AND "statut" = \'all\' AND {OPS} '
               'AND $timeFilter GROUP BY "transaction"', fmt='table'),
        influx(f'SELECT max("pct95.0") AS "Худший p95 окна, мс" FROM "jmeter" WHERE {APP} AND "statut" = \'ok\' '
               f'AND {OPS} AND $timeFilter GROUP BY "transaction"', fmt='table'),
        influx(f'SELECT sum("count") AS "Ошибок" FROM "jmeter" WHERE {APP} AND "statut" = \'ko\' AND {OPS} '
               'AND $timeFilter GROUP BY "transaction"', fmt='table'),
    ], width=24, options={'showHeader': True})
    variables = [
        {'name': 'application', 'label': 'Тест', 'type': 'query', 'datasource': INFLUX,
         'query': 'SHOW TAG VALUES FROM "jmeter" WITH KEY = "application"', 'refresh': 2, 'multi': False},
        {'name': 'transaction', 'label': 'Операция', 'type': 'query', 'datasource': INFLUX,
         'query': 'SHOW TAG VALUES FROM "jmeter" WITH KEY = "transaction" WHERE "application" =~ /^$application$/',
         'regex': '/^ОП-/', 'refresh': 2, 'multi': True, 'includeAll': True},
    ]
    return dashboard('efr-nt-jmeter', 'ЕФР НТ — JMeter', ['efr', 'nt', 'jmeter'], variables, b)


def prom(expr, legend):
    return {'expr': expr, 'legendFormat': legend, 'range': True}


def app(fixed):
    sel = 'job="efr-api", instance=~"$instance"'
    b = Board()
    fn = 'increase' if fixed else 'rate'  # 17.1
    b.add('Запросов за интервал', 'timeseries', PROM, [prom(
        f'sum by (uri) ({fn}(http_server_requests_seconds_count{{{sel}}}[$__interval]))', '{{uri}}')], unit='short')
    b.add('Интенсивность, запросов/с', 'timeseries', PROM, [prom(
        f'sum(rate(http_server_requests_seconds_count{{{sel}}}[1m]))', 'Все API')], unit='reqps')
    inner = f'rate(http_server_requests_seconds_bucket{{{sel}}}[5m])'
    quantile = f'histogram_quantile(0.95, sum by (le, uri) ({inner}))' if fixed else \
        f'histogram_quantile(0.95, {inner})'  # 17.2
    b.add('p95 по API, все экземпляры', 'timeseries', PROM, [prom(quantile, '{{uri}}')], unit='s')
    b.add('Ошибки 5xx', 'timeseries', PROM, [prom(
        f'sum by (uri, status) (increase(http_server_requests_seconds_count{{{sel}, status=~"5.."}}[$__interval]))',
        '{{uri}} {{status}}')], unit='short')
    stacking = {'mode': 'none'} if fixed else {'mode': 'normal', 'group': 'A'}  # 17.3
    b.add('Heap по экземплярам', 'timeseries', PROM, [prom(
        f'sum by (instance) (jvm_memory_used_bytes{{{sel}, area="heap"}})', '{{instance}}')], unit='bytes',
        custom={'stacking': stacking, 'thresholdsStyle': {'mode': 'line'}}, thresholds=8589934592)
    b.add('Нижняя граница heap', 'timeseries', PROM, [prom(
        f'max by (instance) (jvm_gc_live_data_size_bytes{{{sel}}})', '{{instance}}')], unit='bytes')
    b.add('HikariCP: активные соединения', 'timeseries', PROM, [prom(
        f'sum by (instance) (hikaricp_connections_active{{{sel}}})', '{{instance}}')], unit='short',
        custom={'thresholdsStyle': {'mode': 'line'}}, thresholds=40)
    if fixed:  # 17.5
        b.add('HikariCP: ожидающие соединения', 'timeseries', PROM, [prom(
            f'sum by (instance) (hikaricp_connections_pending{{{sel}}})', '{{instance}}')], unit='short')
    b.add('Ожидание соединения HikariCP', 'timeseries', PROM, [prom(
        f'max by (instance) (rate(hikaricp_connections_acquire_seconds_sum{{{sel}}}[5m]) / '
        f'rate(hikaricp_connections_acquire_seconds_count{{{sel}}}[5m]))', '{{instance}}')],
        unit='s' if fixed else 'ms')  # 17.4
    variables = [{'name': 'instance', 'label': 'Экземпляр', 'type': 'query', 'datasource': PROM,
                  'query': {'query': 'label_values(jvm_memory_used_bytes{job="efr-api"}, instance)', 'refId': 'V'},
                  'refresh': 2, 'multi': True, 'includeAll': True}]
    return dashboard('efr-nt-api', 'ЕФР НТ — efr-api', ['efr', 'nt', 'prometheus'], variables, b)


def zbx(item, host='$host', trends='default'):
    return {'queryType': '0', 'group': {'filter': 'EFR-NT'}, 'host': {'filter': host}, 'application': {'filter': ''},
            'itemTag': {'filter': ''}, 'item': {'filter': item}, 'functions': [],
            'options': {'showDisabledItems': False, 'skipEmptyValues': False, 'useTrends': trends,
                        'disableDataAlignment': False}}


def servers(fixed):
    b = Board()
    b.add('Загрузка CPU, %', 'timeseries', ZABBIX, [zbx('CPU utilization' if fixed else 'CPU idle time')],  # 18.1
          unit='percent', custom={'thresholdsStyle': {'mode': 'line'}}, thresholds=70)
    if fixed:
        b.add('Память, занято %', 'timeseries', ZABBIX, [zbx('Memory utilization')], unit='percent')
    else:
        b.add('Память, занято', 'timeseries', ZABBIX, [zbx('Available memory')], unit='bytes')  # 18.5
    disk_host = 'efr-nt-db01' if fixed else '/efr-nt-app.*/'  # 18.3
    b.add('Диск', 'timeseries', ZABBIX, [zbx('/sd[a-z]: Disk utilization/', host=disk_host)], unit='percent')
    b.add('Сеть, входящий трафик', 'timeseries', ZABBIX,
          [zbx('/Interface .*: Bits received/', trends='default' if fixed else 'true')], unit='bps')  # 18.4
    b.add('Load average (1m)', 'timeseries', ZABBIX, [zbx('Load average (1m avg)')], unit='short')
    b.add('Свободное место, %', 'timeseries', ZABBIX, [zbx('/FS \\[.*\\]: Space: Available, in %/')], unit='percent')
    regex = '/efr-nt-(app|int|db|gen).*/' if fixed else '/efr-nt-(app|int|db).*/'  # 18.2
    variables = [{'name': 'host', 'label': 'Сервер', 'type': 'query', 'datasource': ZABBIX,
                  'query': {'queryType': 'host', 'group': 'EFR-NT', 'host': '/.*/', 'application': '', 'itemTag': '',
                            'item': ''},
                  'regex': regex, 'refresh': 1, 'multi': True, 'includeAll': True}]
    return dashboard('efr-nt-servers', 'ЕФР НТ — серверы (Zabbix)', ['efr', 'nt', 'zabbix'], variables, b)


BOARDS = {'16-jmeter-influxdb': jmeter, '17-efr-api-prometheus': app, '18-servers-zabbix': servers}

if __name__ == '__main__':
    for name, build in BOARDS.items():
        for fixed, folder in ((False, TASK / 'participant' / 'monitoring'), (True, TASK / 'jury' / 'fixed' / 'monitoring')):
            folder.mkdir(parents=True, exist_ok=True)
            text = json.dumps(build(fixed), ensure_ascii=False, indent=2) + '\n'
            (folder / f'{name}.json').write_text(text, encoding='utf-8')
    print('Готово:', ', '.join(BOARDS))
