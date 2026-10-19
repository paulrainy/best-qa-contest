"""Протокол 12: стабильность, 06–07.11.2026, ЕФР 2026.11.

Что на самом деле произошло (правильный вывод — в ключе):
- тест шёл 4 ч вместо 8 ч по методике;
- нижняя граница heap (после сборки) выросла с 2,10 до 2,48 ГБ — на 18 %, это утечка по 4.5;
- в 00:35 вручную запущен VACUUM (ANALYZE) operations под нагрузкой — ОП-09 до 00:52 заметно медленнее;
- таблица результатов посчитана за 22:00–02:10, то есть вместе с прогревом.
"""
from pathlib import Path

import numpy as np

import charts
import nt_profile as pf

DAY = '2026-11-06'
START = '22:00'
WARMUP_MIN, TOTAL_MIN = 10, 250
VACUUM = (155, 172)  # 00:35–00:52 от 22:00
LIVE = (2.10, 2.48)  # ГБ, нижняя граница heap в начале и в конце
ERRORS = {'ОП-01': 0.01, 'ОП-02': 0.01, 'ОП-03': 0.04, 'ОП-04': 0.05, 'ОП-05': 0.03, 'ОП-06': 0.04, 'ОП-07': 0.02,
          'ОП-08': 0.01, 'ОП-09': 0.03, 'ОП-10': 0.01}
UTIL = [  # показатель, среднее, максимум
    ('CPU efr-api, среднее по 4 серверам, %', 41, 49),
    ('Память efr-api, среднее по 4 серверам, %', 59, 66),
    ('CPU efr-cft-adapter, %', 15, 19),
    ('CPU БД, %', 31, 52),
    ('Память БД, %', 72, 74),
    ('Диск БД, утилизация %', 22, 64),
    ('CPU efr-nt-gen01, %', 47, 53),
    ('CPU efr-nt-gen02, %', 45, 51),
]


def p95_series(code, t, rng):
    base = pf.P95_100[code] * (1 + 0.06 * t / TOTAL_MIN)  # к концу чуть растёт: сборки мусора чаще
    values = charts.noisy(rng, base, 0.05, t.size)
    if code == 'ОП-09':
        hit = (t >= VACUUM[0]) & (t < VACUUM[1])
        values[hit] *= 1.6
    values[t < WARMUP_MIN] *= 0.93
    return values


def table_p95(code):
    t = np.arange(0, TOTAL_MIN, 0.25)
    values = p95_series(code, t, np.random.default_rng(1206 + int(code[-2:])))
    return int(round(np.percentile(values, 60), -1))  # p95 по отчёту JMeter за весь интервал


def tables() -> str:
    rows = []
    for code in pf.CODES:
        tgt = pf.target(code, 100)
        fact = tgt * (TOTAL_MIN - WARMUP_MIN * 0.5) / TOTAL_MIN * 0.996
        rows.append([code, pf.num(tgt), pf.num(fact), pf.num(table_p95(code)), pf.num(pf.THRESHOLD[code]),
                     pf.num(ERRORS[code], 2)])
    out = ['Таблица 1. Бизнес-метрики за интервал 22:00–02:10', pf.table(
        ['Операция', 'Заданная, оп/ч', 'Фактическая, оп/ч', 'p95, мс', 'Порог, мс', 'Ошибки, %'], rows)]
    out += ['', 'Таблица 2. Утилизация за интервал 22:00–02:10',
            pf.table(['Показатель', 'Среднее', 'Максимум'], [[n, a, m] for n, a, m in UTIL])]
    return '\n'.join(out)


def draw(img: Path) -> list:
    rng = np.random.default_rng(1206)
    t = np.arange(0, TOTAL_MIN, 0.25)
    when = charts.minutes(f'{DAY} {START}', t)
    load = np.where(t < WARMUP_MIN, 0.5, 1.0)
    target = 36000 / 3600 * load
    fact = charts.noisy(rng, target * 0.996, 0.02, t.size)
    live = LIVE[0] + (LIVE[1] - LIVE[0]) * t / TOTAL_MIN + rng.normal(0, 0.01, t.size)
    used = live + (t * 60 % 40) / 40 * 2.6 + rng.normal(0, 0.03, t.size)
    cpu_db = charts.noisy(rng, 31.0, 0.05, t.size)
    cpu_db[(t >= VACUUM[0]) & (t < VACUUM[1])] += 20
    files = {
        '12-throughput.png': ('Рисунок 1. Интенсивность операций', {'Заданная': target, 'Фактическая': fact},
                              'оп/с', None, None, None, 'Grafana · JMeter'),
        '12-p95.png': ('Рисунок 2. 95-й перцентиль по окнам', {
            'ОП-01': p95_series('ОП-01', t, rng), 'ОП-04': p95_series('ОП-04', t, rng),
            'ОП-09': p95_series('ОП-09', t, rng)}, 'мс', None, None, None, 'Grafana · JMeter'),
        '12-heap.png': ('Рисунок 3. Heap efr-api, среднее по экземплярам', {
            'Занято': used, 'После сборки (live data)': live}, 'ГБ', 8, '-Xmx 8 ГБ', None, 'Grafana · Prometheus'),
        '12-cpu.png': ('Рисунок 4. Загрузка CPU', {
            'efr-api, среднее': charts.noisy(rng, 41.0 * load, 0.05, t.size), 'БД efr-nt-db01': cpu_db * load,
            'efr-nt-gen01': charts.noisy(rng, 47.0 * load, 0.04, t.size),
            'efr-nt-gen02': charts.noisy(rng, 45.0 * load, 0.04, t.size)}, '%', None, None, None, 'Grafana · Zabbix'),
    }
    for name, (title, data, unit, threshold, label, colors, source) in files.items():
        ylim = (0, 100) if unit == '%' else ((0, 9) if unit == 'ГБ' else None)
        charts.panel(img / name, title, when, data, unit, threshold, label, ylim, colors, source)
    return list(files)
