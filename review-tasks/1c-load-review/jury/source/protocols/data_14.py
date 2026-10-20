"""Протокол 14: контрольный прогон после исправления EFR-NT-418, 14.11.2026, ЕФР 2026.11 сборка b431.

Что на самом деле произошло (правильный вывод — в ключе):
- EFR-NT-418 (соединения HikariCP не возвращаются в пул) найден в стабильности 12.11 на 5-м часе, а контрольный
  прогон шёл 1 час — исправление им не подтверждено;
- АБС была на заглушке (CFTNT занят), исходный тест — на CFTNT, в «Ограничениях» «Нет»;
- ошибки показаны только суммарно 0,14 %, а у ОП-06 — 2,4 % (рисунок 2);
- журнал 22:00–23:00, графики — 21:00–22:00 (другой запуск);
- рекомендация «увеличить heap» не следует из данных: heap не выше 4,8 из 8 ГБ, нижняя граница ровная.
"""
from pathlib import Path

import numpy as np

import charts
import nt_profile as pf

DAY = '2026-11-14'
CHART_START = '21:00'  # графики выгружены за другой интервал
ERRORS = {'ОП-01': 0.02, 'ОП-02': 0.02, 'ОП-03': 0.05, 'ОП-04': 0.06, 'ОП-05': 0.04, 'ОП-06': 2.4, 'ОП-07': 0.03,
          'ОП-08': 0.01, 'ОП-09': 0.03, 'ОП-10': 0.02}
P95 = {'ОП-01': 415, 'ОП-02': 600, 'ОП-03': 1170, 'ОП-04': 1570, 'ОП-05': 810, 'ОП-06': 1070, 'ОП-07': 5550,
       'ОП-08': 205, 'ОП-09': 2280, 'ОП-10': 515}
UTIL = [
    ('CPU efr-api, среднее по 4 серверам, %', 40, 46),
    ('Память efr-api, среднее по 4 серверам, %', 58, 63),
    ('CPU efr-cft-adapter, %', 13, 16),
    ('Память efr-cft-adapter, %', 46, 48),
    ('CPU БД, %', 30, 36),
    ('Память БД, %', 72, 73),
    ('Диск БД, утилизация %', 21, 27),
    ('CPU efr-nt-gen01, %', 46, 51),
    ('CPU efr-nt-gen02, %', 45, 49),
    ('Heap JMeter на генераторах, % от 6 ГБ', 45, 52),
    ('HikariCP: активных на экземпляр (из 40)', 18, 24),
    ('HikariCP: ожидающих, всего', 0, 0),
]


def total_errors():
    weights = {c: pf.target(c, 100) for c in pf.CODES}
    return sum(ERRORS[c] * w for c, w in weights.items()) / sum(weights.values())


def tables() -> str:
    conditions = [
        ['Сборка efr-api', '2026.11.0-b412', '2026.11.0-b431 (исправление EFR-NT-418)'],
        ['Вид и длительность', 'Стабильность, 8 ч', 'Контрольный прогон, 1 ч'],
        ['Нагрузка', '100 % профиля', '100 % профиля'],
        ['АБС «ЦФТ-Банк»', 'контур CFTNT', 'заглушка АБС (CFTNT занят)'],
        ['Пул HikariCP на экземпляр', '40', '40'],
        ['Строк в operations', '421 млн', '421 млн'],
    ]
    out = ['Таблица 1. Условия исходного теста и контрольного прогона',
           pf.table(['Параметр', 'Стабильность 12.11.2026', 'Контрольный прогон 14.11.2026'], conditions)]
    rows = [[c, pf.num(pf.target(c, 100)), pf.num(pf.target(c, 100) * 0.996), pf.num(P95[c]), pf.num(pf.THRESHOLD[c])]
            for c in pf.CODES]
    rows.append(['Ошибки, всего', '', '', '', pf.num(total_errors(), 2) + ' %'])
    out += ['', 'Таблица 2. Бизнес-метрики контрольного прогона', pf.table(
        ['Операция', 'Заданная, оп/ч', 'Фактическая, оп/ч', 'p95, мс', 'Порог, мс'], rows)]
    out += ['', 'Таблица 3. Утилизация за контрольный прогон',
            pf.table(['Показатель', 'Среднее', 'Максимум'], [[n, a, m] for n, a, m in UTIL])]
    return '\n'.join(out)


def draw(img: Path) -> list:
    rng = np.random.default_rng(1414)
    t = np.arange(0, 60, 0.25)
    when = charts.minutes(f'{DAY} {CHART_START}', t)
    active = charts.noisy(rng, 18.0, 0.08, t.size)
    pending = np.zeros(t.size)
    errors = {c: np.clip(charts.noisy(rng, ERRORS[c], 0.35, t.size), 0, None) for c in ('ОП-04', 'ОП-06', 'ОП-08')}
    errors['Остальные, среднее'] = np.clip(charts.noisy(rng, 0.03, 0.4, t.size), 0, None)
    live = 2.1 + rng.normal(0, 0.01, t.size)
    used = live + (t * 60 % 40) / 40 * 2.6 + rng.normal(0, 0.03, t.size)
    files = {
        '14-hikari.png': ('Рисунок 1. Пул соединений HikariCP', {'Активные, среднее на экземпляр': active,
                                                                  'Ожидающие, всего': pending},
                          'соединений', 40, 'maximumPoolSize = 40', None, 'Grafana · Prometheus'),
        '14-errors.png': ('Рисунок 2. Доля ошибок по операциям', errors, '%', None, None, None, 'Grafana · JMeter'),
        '14-heap.png': ('Рисунок 3. Heap efr-api, среднее по экземплярам', {'Занято': used,
                                                                            'После сборки (live data)': live},
                        'ГБ', 8, '-Xmx 8 ГБ', None, 'Grafana · Prometheus'),
    }
    for name, (title, data, unit, threshold, label, colors, source) in files.items():
        ylim = (0, 9) if unit == 'ГБ' else ((0, 4) if unit == '%' else None)
        charts.panel(img / name, title, when, data, unit, threshold, label, ylim, colors, source)
    return list(files)
