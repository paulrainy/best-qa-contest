"""Протокол 15: hotfix efr-cft-adapter 3.8.3, сравнение с эталоном на заглушке АБС, 19.11.2026.

Что на самом деле произошло (правильный вывод — в ключе):
- заглушка АБС отвечает за 0 мс, а по 6.4 — 120 мс и 400 мс: «ускорение» ОП-04, ОП-06, ОП-08 дала заглушка;
- 38 таймаутов ОП-08 не включены в ошибки: вместе с 38 прочими ошибками это 1,19 % — больше 1 %;
- ОП-08 подано 6 400 оп/ч — 88,9 % заданной (меньше 95 %), а в выводе «нагрузка подана»;
- ОП-08 сравнивается с порогом 800 мс вместо 600 мс;
- в заключении нет решения, можно ли в пром.
Заглушка АБС как таковая допустима: CFTNT недоступен, это указано в «Ограничениях» (ловушка).
"""
from pathlib import Path

import numpy as np

import charts
import nt_profile as pf
import operation_counts as oc

DAY = '2026-11-19'
START = '22:10'
BASE = {'ОП-01': 418, 'ОП-02': 605, 'ОП-03': 1175, 'ОП-04': 1940, 'ОП-05': 815, 'ОП-06': 1395, 'ОП-07': 5580,
        'ОП-08': 310, 'ОП-09': 2290, 'ОП-10': 518}
TEST = {'ОП-01': 421, 'ОП-02': 611, 'ОП-03': 1182, 'ОП-04': 1560, 'ОП-05': 818, 'ОП-06': 1060, 'ОП-07': 5610,
        'ОП-08': 200, 'ОП-09': 2310, 'ОП-10': 522}
ERROR_TARGETS = {'ОП-01': 0.01, 'ОП-02': 0.02, 'ОП-03': 0.04, 'ОП-04': 0.05, 'ОП-05': 0.03, 'ОП-06': 0.04, 'ОП-07': 0.02,
          'ОП-08': 0.6, 'ОП-09': 0.03, 'ОП-10': 0.01}
TIMEOUTS = {'ОП-08': 38}
FACT_08 = 6400
UTIL = [
    ('CPU efr-api, среднее по 4 серверам, %', 41, 40),
    ('Память efr-api, среднее по 4 серверам, %', 59, 60),
    ('CPU efr-cft-adapter, %', 15, 12),
    ('Память efr-cft-adapter, %', 47, 46),
    ('CPU БД, %', 31, 30),
    ('Память БД, %', 72, 72),
    ('Диск БД, утилизация %', 21, 22),
    ('CPU efr-nt-gen01, %', 47, 46),
    ('CPU efr-nt-gen02, %', 45, 45),
    ('Память efr-nt-gen01, %', 58, 57),
    ('Память efr-nt-gen02, %', 56, 56),
    ('Heap JMeter на генераторах, % от 6 ГБ', 46, 47),
]
DELIVERED = pf.delivered(0.996, 1519)
THRESHOLD = dict(pf.THRESHOLD, **{'ОП-08': 800})  # дефект Д15.5


def change(old, new):
    return pf.num((new - old) / old * 100, 1).replace('-', '−')


def operation_counts():
    return {code: oc.make_counts(FACT_08 if code == 'ОП-08' else pf.target(code, 100) * DELIVERED[code],
                                60, ERROR_TARGETS[code], 1519 + i,
                                timeouts=TIMEOUTS.get(code, 0), other_errors=38 if code == 'ОП-08' else None)
            for i, code in enumerate(pf.CODES)}


def tables() -> str:
    counts = operation_counts()
    conditions = [
        ['Версия efr-cft-adapter', '3.8.2', '3.8.3 (hotfix)'],
        ['Дата', '16.11.2026', '19.11.2026'],
        ['АБС «ЦФТ-Банк»', 'контур CFTNT', 'заглушка АБС'],
        ['Строк в operations', '421 млн', '422 млн'],
        ['Нагрузка, длительность', '100 % профиля, 1 ч', '100 % профиля, 1 ч'],
    ]
    out = ['Таблица 1. Условия теста и эталона', pf.table(['Параметр', 'Эталон', 'Тест'], conditions)]
    stubs = [['АБС «ЦФТ-Банк»', 'GetAccountBalance', '0'], ['АБС «ЦФТ-Банк»', 'OpenDeposit, CloseDeposit', '0'],
             ['fm-check', 'check', '200'], ['СМЭВ', 'проверка паспорта', '300']]
    out += ['', 'Таблица 2. Задержки заглушек в тесте', pf.table(['Заглушка', 'Метод', 'Задержка, мс'], stubs)]
    rows = []
    for c in pf.CODES:
        tgt = pf.target(c, 100)
        fact = oc.combine(counts[c]).total
        rows.append([c, pf.num(tgt), pf.num(fact), pf.num(TEST[c]), pf.num(THRESHOLD[c]), pf.num(oc.error_summary(counts[c], include_timeouts=False)[0], 2),
                     TIMEOUTS.get(c, 0)])
    out += ['', 'Таблица 3. Бизнес-метрики теста, 22:10–23:10', pf.table(
        ['Операция', 'Заданная, оп/ч', 'Фактическая, оп/ч', 'p95, мс', 'Порог, мс', 'Ошибки, %', 'Таймауты, шт.'],
        rows)]
    rows = [[c, pf.num(BASE[c]), pf.num(TEST[c]), change(BASE[c], TEST[c])] for c in pf.CODES]
    out += ['', 'Таблица 4. 95-й перцентиль против эталона, мс', pf.table(
        ['Операция', 'Эталон 3.8.2', 'Тест 3.8.3', 'Изменение, %'], rows)]
    rows = [[n, a, b, change(a, b)] for n, a, b in UTIL]
    out += ['', 'Таблица 5. Утилизация против эталона, среднее за тест', pf.table(
        ['Показатель', 'Эталон', 'Тест', 'Изменение, %'], rows)]
    out += ['', 'Таблица 6. CPU и память ОС по серверам, среднее за тест', pf.table(
        ['Сервер', 'Метрика', 'Эталон, %', 'Тест, %', 'Изменение, %'], charts.server_comparison(UTIL))]
    return '\n'.join(out)


def prose() -> list:
    """Фразы текста протокола с числами из данных: charts.py --check ищет их в исходнике слово в слово."""
    via_abs = ('ОП-08', 'ОП-06', 'ОП-04')  # идут в АБС: таблица 2 задержек заглушек
    faster = {c: (BASE[c] - TEST[c]) / BASE[c] * 100 for c in via_abs}
    cpu = next((old, new) for name, old, new in UTIL if name == 'CPU efr-cft-adapter, %')
    # Как в таблице 3: таймауты не учтены (Д15.3).
    error_08 = oc.error_summary(operation_counts()['ОП-08'], include_timeouts=False)[0]
    return [
        f'уменьшилось на {pf.num(min(faster.values()))}–{pf.num(max(faster.values()))} %',
        'ускорил операции через АБС: ' + ', '.join(f'{c} — на {pf.num(faster[c])} %' for c in via_abs),
        f'CPU efr-cft-adapter снизился на {pf.num((cpu[0] - cpu[1]) / cpu[0] * 100)} %',
        f'Доля ошибок ОП-08 — {pf.num(error_08, 2)} %',
    ]


def draw(img: Path) -> list:
    rng = np.random.default_rng(1519)
    t = np.arange(0, 60, 0.25)
    when = charts.minutes(f'{DAY} {START}', t)
    counts = operation_counts()
    files = {
        '15-op08-throughput.png': ('Рисунок 1. ОП-08: интенсивность', {
            'Заданная': np.full(t.size, 2.0), 'Фактическая': np.array([row.total / 15 for row in counts['ОП-08']])},
            'оп/с', None, None, None, 'Grafana · JMeter'),
        '15-p95.png': ('Рисунок 2. 95-й перцентиль по окнам', {
            c: charts.noisy(rng, TEST[c] * 0.97, 0.05, t.size) for c in pf.CODES},
            'мс', None, None, None, 'Grafana · JMeter'),
    }
    for name, (title, data, unit, threshold, label, colors, source) in files.items():
        ylim = (0, 2.5) if unit == 'оп/с' else None
        charts.panel(img / name, title, when, data, unit, threshold, label, ylim, colors, source, summarize=unit != 'мс')
    target = sum(pf.target(c, 100) for c in pf.CODES) / 3600
    charts.panel(img / '15-throughput.png', 'Рисунок 3. Интенсивность всех операций', when, {
        'Заданная': np.full(t.size, target),
        'Фактическая': oc.throughput(counts)}, 'оп/с', source='Grafana · JMeter')
    # Намеренно не учтены таймауты, как в таблице: Д15.3.
    charts.panel(img / '15-errors.png', 'Рисунок 4. Доля ошибок по операциям', when,
                 {c: oc.error_values(counts[c], include_timeouts=False) for c in pf.CODES}, '%', source='Grafana · JMeter',
                 summary_values={c: oc.error_summary(counts[c], include_timeouts=False) for c in pf.CODES})
    metrics = charts.util_series(UTIL, t.size, seed=1519, column=2)
    return [*files, '15-throughput.png', '15-errors.png',
            *charts.server_panels(img, 15, when, metrics, 5)]
