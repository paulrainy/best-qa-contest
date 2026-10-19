"""Протокол 12: стабильность, 06–07.11.2026, ЕФР 2026.11.

Что на самом деле произошло (правильный вывод — в ключе):
- тест шёл 4 ч вместо 8 ч по методике;
- нижняя граница heap (после сборки) выросла с 2,1 до 2,5 ГБ — на 17–18 %, это утечка по 4.5;
- в 00:35 вручную запущен VACUUM (ANALYZE) operations под нагрузкой — ОП-09 и CPU БД до 00:52 заметно выше;
- таблицы результатов посчитаны за 22:00–02:10, то есть вместе с прогревом.

Таблицы считаются из тех же рядов, что и графики: p95 — 95-й перцентиль значений по окнам, утилизация — среднее
и максимум ряда.
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
# показатель, уровень на 100 %, разброс; на прогреве — половина
UTIL = [
    ('CPU efr-api, среднее по 4 серверам, %', 41, 0.05),
    ('Память efr-api, среднее по 4 серверам, %', 59, 0.02),
    ('CPU efr-cft-adapter, %', 15, 0.06),
    ('Память efr-cft-adapter, %', 47, 0.02),
    ('CPU БД, %', 31, 0.05),
    ('Память БД, %', 72, 0.01),
    ('Диск БД, утилизация %', 22, 0.08),
    ('CPU efr-nt-gen01, %', 47, 0.04),
    ('CPU efr-nt-gen02, %', 45, 0.04),
    ('Heap JMeter на генераторах, % от 6 ГБ', 46, 0.05),
]
T = np.arange(0, TOTAL_MIN, 0.25)
LOAD = np.where(T < WARMUP_MIN, 0.5, 1.0)
VAC = (T >= VACUUM[0]) & (T < VACUUM[1])


def p95(code):
    rng = np.random.default_rng(1206 + int(code[-2:]))
    base = pf.P95_100[code] * (1 + 0.06 * T / TOTAL_MIN)  # к концу чуть растёт: сборки мусора чаще
    values = charts.noisy(rng, base, 0.05, T.size)
    if code == 'ОП-09':
        values[VAC] *= 1.6
    values[T < WARMUP_MIN] *= 0.93
    return values


def util(n):
    name, level, spread = UTIL[n]
    rng = np.random.default_rng(1260 + n)
    values = charts.noisy(rng, level, spread, T.size)
    if 'Память' not in name and 'Heap' not in name:
        values = values * LOAD
    if name == 'CPU БД, %':
        values[VAC] += 20
    if name == 'Диск БД, утилизация %':
        values[VAC] += 40
    return values


def tables() -> str:
    rows = []
    for code in pf.CODES:
        tgt = pf.target(code, 100)
        fact = tgt * (TOTAL_MIN - WARMUP_MIN * 0.5) / TOTAL_MIN * 0.996
        rows.append([code, pf.num(tgt), pf.num(fact), pf.num(int(round(np.percentile(p95(code), 95), -1))),
                     pf.num(pf.THRESHOLD[code]), pf.num(ERRORS[code], 2)])
    out = ['Таблица 1. Бизнес-метрики за интервал 22:00–02:10', pf.table(
        ['Операция', 'Заданная, оп/ч', 'Фактическая, оп/ч', 'p95, мс', 'Порог, мс', 'Ошибки, %'], rows)]
    rows = [[name, round(float(np.mean(util(n)))), round(float(np.max(util(n))))] for n, (name, _, _) in enumerate(UTIL)]
    out += ['', 'Таблица 2. Утилизация за интервал 22:00–02:10', pf.table(['Показатель', 'Среднее', 'Максимум'], rows)]
    return '\n'.join(out)


def draw(img: Path) -> list:
    rng = np.random.default_rng(1206)
    when = charts.minutes(f'{DAY} {START}', T)
    target = 36000 / 3600 * LOAD
    fact = charts.noisy(rng, target * 0.996, 0.02, T.size)
    live = LIVE[0] + (LIVE[1] - LIVE[0]) * T / TOTAL_MIN + rng.normal(0, 0.01, T.size)
    used = live + (T * 60 % 40) / 40 * 2.6 + rng.normal(0, 0.03, T.size)
    names = {0: 'efr-api, среднее', 4: 'БД efr-nt-db01', 7: 'efr-nt-gen01', 8: 'efr-nt-gen02'}
    files = {
        '12-throughput.png': ('Рисунок 1. Интенсивность операций', {'Заданная': target, 'Фактическая': fact},
                              'оп/с', None, None, None, 'Grafana · JMeter'),
        '12-p95.png': ('Рисунок 2. 95-й перцентиль по окнам', {c: p95(c) for c in ('ОП-01', 'ОП-04', 'ОП-09')},
                       'мс', None, None, None, 'Grafana · JMeter'),
        '12-heap.png': ('Рисунок 3. Heap efr-api, среднее по экземплярам', {
            'Занято': used, 'После сборки (live data)': live}, 'ГБ', 8, '-Xmx 8 ГБ', None, 'Grafana · Prometheus'),
        '12-cpu.png': ('Рисунок 4. Загрузка CPU', {label: util(n) for n, label in names.items()}, '%', None, None,
                       None, 'Grafana · Zabbix'),
    }
    for name, (title, data, unit, threshold, label, colors, source) in files.items():
        ylim = (0, 100) if unit == '%' else ((0, 9) if unit == 'ГБ' else None)
        charts.panel(img / name, title, when, data, unit, threshold, label, ylim, colors, source)
    return list(files)
