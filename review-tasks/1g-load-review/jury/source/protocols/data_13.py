"""Протокол 13: сравнение с эталоном, 07.11.2026, ЕФР 2026.11 против 2026.08.

Что на самом деле произошло (правильный вывод — в ключе):
- ОП-04 выросла на 14 % против эталона — это деградация по 4.3, хотя порог 3 000 мс не превышен;
- ОП-07 выросла на 8 % — в пределах 10 %, это нормально;
- эталон снят при operations 300 млн строк (меньше 80 % прома и на 29 % меньше, чем сейчас) — несопоставим;
- в ОП-08 были ответы 503 (22:40–22:47), в таблице ошибок 0 %;
- ОП-09 в тесте не подавалась;
- CPU efr-api вырос с 32 до 41 % (+28 %) без объяснения.
"""
from pathlib import Path

import numpy as np

import charts
import nt_profile as pf

DAY = '2026-11-07'
START = '22:10'
TOTAL_MIN = 60
CODES = [c for c in pf.CODES if c != 'ОП-09']
BASELINE = {'ОП-01': 412, 'ОП-02': 598, 'ОП-03': 1160, 'ОП-04': 1710, 'ОП-05': 805, 'ОП-06': 1380, 'ОП-07': 5185,
            'ОП-08': 305, 'ОП-10': 515}
ERRORS = {'ОП-01': 0.01, 'ОП-02': 0.01, 'ОП-03': 0.03, 'ОП-04': 0.05, 'ОП-05': 0.02, 'ОП-06': 0.04, 'ОП-07': 0.02,
          'ОП-08': 0.00, 'ОП-10': 0.01}
BURST = (30, 37)  # 503 в ОП-08 22:40–22:47 от 22:10
UTIL = [  # показатель, эталон, тест
    ('CPU efr-api, среднее по 4 серверам, %', 32, 41),
    ('Память efr-api, среднее по 4 серверам, %', 57, 59),
    ('CPU efr-cft-adapter, %', 15, 15),
    ('Память efr-cft-adapter, %', 46, 47),
    ('CPU БД, %', 30, 31),
    ('Память БД, %', 71, 72),
    ('Диск БД, утилизация %', 20, 21),
    ('CPU efr-nt-gen01, %', 46, 47),
    ('CPU efr-nt-gen02, %', 44, 45),
    ('Heap JMeter на генераторах, % от 6 ГБ', 45, 46),
]


def change(old, new):
    return pf.num((new - old) / old * 100, 1).replace('-', '−')


def tables() -> str:
    conditions = [
        ['Релиз', '2026.08', '2026.11'],
        ['Дата теста', '21.08.2026', '07.11.2026'],
        ['Контур, конфигурация', 'EFR-NT, по п. 6.1 методики', 'EFR-NT, по п. 6.1 методики'],
        ['Строк в operations', '300 млн', '420 млн'],
        ['Строк в clients', '11,9 млн', '12,1 млн'],
        ['Длительность', '1 ч на 100 % профиля', '1 ч на 100 % профиля'],
    ]
    out = ['Таблица 1. Условия теста и эталона', pf.table(['Параметр', 'Эталон', 'Тест'], conditions)]
    rows = []
    for code in CODES:
        tgt = pf.target(code, 100)
        rows.append([code, pf.num(tgt), pf.num(tgt * 0.995), pf.num(pf.P95_100[code]), pf.num(pf.THRESHOLD[code]),
                     pf.num(ERRORS[code], 2)])
    out += ['', 'Таблица 2. Бизнес-метрики теста, 22:10–23:10', pf.table(
        ['Операция', 'Заданная, оп/ч', 'Фактическая, оп/ч', 'p95, мс', 'Порог, мс', 'Ошибки, %'], rows)]
    rows = [[c, pf.num(BASELINE[c]), pf.num(pf.P95_100[c]), change(BASELINE[c], pf.P95_100[c])] for c in CODES]
    out += ['', 'Таблица 3. 95-й перцентиль против эталона, мс', pf.table(
        ['Операция', 'Эталон 2026.08', 'Тест 2026.11', 'Изменение, %'], rows)]
    rows = [[n, a, b, change(a, b)] for n, a, b in UTIL]
    out += ['', 'Таблица 4. Утилизация против эталона, среднее за тест', pf.table(
        ['Показатель', 'Эталон', 'Тест', 'Изменение, %'], rows)]
    return '\n'.join(out)


def draw(img: Path) -> list:
    rng = np.random.default_rng(1307)
    t = np.arange(0, TOTAL_MIN, 0.25)
    when = charts.minutes(f'{DAY} {START}', t)
    target = np.full(t.size, sum(pf.target(c, 100) for c in CODES) / 3600)
    burst = (t >= BURST[0]) & (t < BURST[1])
    ok08 = charts.noisy(rng, 2.0, 0.03, t.size)
    e503 = np.where(burst, charts.noisy(rng, 0.24, 0.2, t.size), 0.0)
    ok08 = ok08 - e503
    files = {
        '13-throughput.png': ('Рисунок 1. Интенсивность операций', {
            'Заданная': target, 'Фактическая': charts.noisy(rng, target * 0.995, 0.02, t.size)},
            'оп/с', None, None, None, 'Grafana · JMeter'),
        '13-op08-codes.png': ('Рисунок 2. ОП-08: ответы по кодам', {'200': ok08, '503': e503}, 'ответов/с', None,
                              None, ['#56A64B', '#FF780A'], 'Grafana · JMeter'),
        '13-p95.png': ('Рисунок 3. 95-й перцентиль по окнам: ОП-04 и ОП-07', {
            'ОП-04': charts.noisy(rng, pf.P95_100['ОП-04'] * 0.97, 0.05, t.size),
            'ОП-07': charts.noisy(rng, pf.P95_100['ОП-07'] * 0.97, 0.05, t.size)}, 'мс', None, None, None,
            'Grafana · JMeter'),
    }
    for name, (title, data, unit, threshold, label, colors, source) in files.items():
        charts.panel(img / name, title, when, data, unit, threshold, label, None, colors, source)
    return list(files)
