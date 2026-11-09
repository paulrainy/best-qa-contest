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
import operation_counts as oc

DAY = '2026-11-07'
START = '22:10'
TOTAL_MIN = 60
CODES = [c for c in pf.CODES if c != 'ОП-09']
PALETTE = [charts.COLORS[pf.CODES.index(c)] for c in CODES]  # цвет операции тот же, что в других протоколах
DELIVERED = pf.delivered(0.995, 1307, CODES)
BASELINE = {'ОП-01': 412, 'ОП-02': 598, 'ОП-03': 1160, 'ОП-04': 1710, 'ОП-05': 805, 'ОП-06': 1380, 'ОП-07': 5185,
            'ОП-08': 305, 'ОП-10': 515}
ERROR_TARGETS = {'ОП-01': 0.01, 'ОП-02': 0.01, 'ОП-03': 0.03, 'ОП-04': 0.05, 'ОП-05': 0.02, 'ОП-06': 0.04, 'ОП-07': 0.02,
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
    ('Память efr-nt-gen01, %', 57, 58),
    ('Память efr-nt-gen02, %', 55, 56),
    ('Heap JMeter на генераторах, % от 6 ГБ', 45, 46),
]


def change(old, new):
    return pf.num((new - old) / old * 100, 1).replace('-', '−')


def operation_counts():
    counts = {code: oc.make_counts(pf.target(code, 100) * DELIVERED[code], TOTAL_MIN,
                                  ERROR_TARGETS[code], 1307 + i) for i, code in enumerate(CODES)}
    # 100 ответов 503 только в 22:40–22:47; в таблице они намеренно скрыты (Д13.4).
    positions = range(BURST[0] * 4, BURST[1] * 4)
    burst = [counts['ОП-08'][i].total for i in positions]
    failed = oc.split_counts(oc.Counts(sum(burst), http503=100), burst, seed=1337)
    for i, row in zip(positions, failed):
        counts['ОП-08'][i] = row
    return counts


def tables() -> str:
    counts = operation_counts()
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
        rows.append([code, pf.num(tgt), pf.num(oc.combine(counts[code]).total), pf.num(pf.P95_100[code]),
                     pf.num(pf.THRESHOLD[code]), pf.num(oc.error_summary(counts[code], include503=False)[0], 2)])
    out += ['', 'Таблица 2. Бизнес-метрики теста, 22:10–23:10', pf.table(
        ['Операция', 'Заданная, оп/ч', 'Фактическая, оп/ч', 'p95, мс', 'Порог, мс', 'Ошибки, %'], rows)]
    rows = [[c, pf.num(BASELINE[c]), pf.num(pf.P95_100[c]), change(BASELINE[c], pf.P95_100[c])] for c in CODES]
    out += ['', 'Таблица 3. 95-й перцентиль против эталона, мс', pf.table(
        ['Операция', 'Эталон 2026.08', 'Тест 2026.11', 'Изменение, %'], rows)]
    rows = [[n, a, b, change(a, b)] for n, a, b in UTIL]
    out += ['', 'Таблица 4. Утилизация против эталона, среднее за тест', pf.table(
        ['Показатель', 'Эталон', 'Тест', 'Изменение, %'], rows)]
    out += ['', 'Таблица 5. CPU и память ОС по серверам, среднее за тест', pf.table(
        ['Сервер', 'Метрика', 'Эталон, %', 'Тест, %', 'Изменение, %'], charts.server_comparison(UTIL))]
    return '\n'.join(out)


def prose() -> list:
    """Фразы текста протокола с числами из данных: charts.py --check ищет их в исходнике слово в слово."""
    # Как в таблице 2: 503 у ОП-08 не учтены (Д13.4).
    max_error = pf.num(max(oc.error_summary(windows, include503=False)[0]
                           for windows in operation_counts().values()), 2)
    growth = {c: (pf.P95_100[c] - BASELINE[c]) / BASELINE[c] * 100 for c in CODES}
    top = max(growth, key=growth.get)
    return [
        f'наибольший рост p95 — у {top}, {pf.num(growth[top])} %, при пороге {pf.num(pf.THRESHOLD[top])} мс '
        f'{top} выполняется за {pf.num(pf.P95_100[top])} мс. Доля ошибок не выше {max_error} %',
        f'доля ошибок не выше {max_error} %. Время операций выросло против эталона на '
        f'{pf.num(min(growth.values()))}–{pf.num(growth[top])} %',
    ]


def draw(img: Path) -> list:
    rng = np.random.default_rng(1307)
    t = np.arange(0, TOTAL_MIN, 0.25)
    when = charts.minutes(f'{DAY} {START}', t)
    target = np.full(t.size, sum(pf.target(c, 100) for c in CODES) / 3600)
    counts = operation_counts()
    e503 = np.array([row.http503 / 15 for row in counts['ОП-08']])
    ok08 = np.array([row.successful / 15 for row in counts['ОП-08']])
    files = {
        '13-throughput.png': ('Рисунок 1. Интенсивность операций', {
            'Заданная': target, 'Фактическая': oc.throughput(counts)},
            'оп/с', None, None, None, 'Grafana · JMeter'),
        '13-op08-codes.png': ('Рисунок 2. ОП-08: ответы по кодам', {'200': ok08, '503': e503}, 'ответов/с', None,
                              None, ['#56A64B', '#FF780A'], 'Grafana · JMeter'),
        '13-p95.png': ('Рисунок 3. 95-й перцентиль по окнам', {
            c: charts.noisy(rng, pf.P95_100[c] * 0.97, 0.05, t.size) for c in CODES}, 'мс', None, None, PALETTE,
            'Grafana · JMeter'),
    }
    for name, (title, data, unit, threshold, label, colors, source) in files.items():
        charts.panel(img / name, title, when, data, unit, threshold, label, None, colors, source, summarize=unit != 'мс')
    errors = {c: oc.error_values(counts[c]) for c in CODES}
    charts.panel(img / '13-errors.png', 'Рисунок 4. Доля ошибок по операциям', when, errors, '%',
                 colors=PALETTE, source='Grafana · JMeter',
                 summary_values={c: oc.error_summary(counts[c]) for c in CODES})
    metrics = charts.util_series(UTIL, t.size, seed=1307, column=2)
    return [*files, '13-errors.png', *charts.server_panels(img, 13, when, metrics, 5)]
