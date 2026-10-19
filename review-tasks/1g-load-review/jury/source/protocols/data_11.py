"""Протокол 11: поиск максимума, 05.11.2026, ЕФР 2026.11 на CFTNT.

Что на самом деле произошло (правильный вывод — в ключе):
- до 125 % всё в норме, пул HikariCP заполняется (25 из 40 на экземпляр);
- на 150 % пул почти исчерпан (38 из 40), растёт очередь ожидающих, efr-api отвечает 503 (1,8 % запросов),
  генераторы загружены на 76–78 % (порог 70 %), подано только 88 % заданной интенсивности;
- CPU БД не выше 46 % — не узкое место.
"""
from pathlib import Path

import numpy as np

import charts
import nt_profile as pf

# Ступени: процент, начало измерения (МСК), доля поданной интенсивности, 503 %, 500 %, множитель p95,
# CPU efr-api, CPU адаптера, CPU БД, диск БД, CPU gen01, CPU gen02, HikariCP активных на экземпляр, ожидающих всего
STEPS = [
    (50, '21:12', 0.996, 0.0, 0.02, 0.92, 22, 8, 18, 12, 26, 25, 9, 0),
    (100, '21:26', 0.994, 0.0, 0.03, 1.00, 41, 15, 31, 21, 47, 45, 18, 0),
    (125, '21:41', 0.989, 0.0, 0.04, 1.12, 50, 19, 37, 25, 58, 57, 25, 2),
    (150, '21:56', 0.882, 1.8, 0.08, 1.32, 58, 22, 44, 29, 78, 76, 38, 35),
    (175, '22:12', 0.804, 4.5, 0.15, 1.90, 60, 23, 45, 30, 86, 84, 40, 120),
    (200, '22:28', 0.739, 7.9, 0.27, 2.60, 61, 24, 46, 31, 93, 91, 40, 210),
]
DAY = '2026-11-05'
MEM_APP = [54, 58, 60, 62, 63, 63]  # память серверов efr-api, % (heap 8 из 16 ГБ плюс прочее)
MEM_DB = [71, 72, 72, 73, 73, 73]  # shared_buffers и кэш ОС
MEM_ADAPTER = [44, 47, 49, 50, 51, 51]
MEM_GEN = [38, 46, 51, 57, 61, 64]  # heap JMeter на генераторах, % от 6 ГБ
WARMUP = '21:00'
STEP_MIN = 10
# p95 на 100 %, мс
P95 = {'ОП-01': 420, 'ОП-02': 610, 'ОП-03': 1180, 'ОП-04': 1950, 'ОП-05': 820, 'ОП-06': 1400, 'ОП-07': 5600,
       'ОП-08': 310, 'ОП-09': 2300, 'ОП-10': 520}
# ответы 500 по операциям относительно среднего по ступени
ERR_WEIGHT = {'ОП-01': 0.5, 'ОП-02': 0.6, 'ОП-03': 1.4, 'ОП-04': 1.8, 'ОП-05': 1.2, 'ОП-06': 1.5, 'ОП-07': 0.8,
              'ОП-08': 0.3, 'ОП-09': 0.9, 'ОП-10': 0.6}
# запросов на операцию — для графика ответов
REQUESTS = {'ОП-01': 1, 'ОП-02': 2, 'ОП-03': 1, 'ОП-04': 3, 'ОП-05': 3, 'ОП-06': 2, 'ОП-07': 1, 'ОП-08': 1,
            'ОП-09': 1, 'ОП-10': 1}


def minute_of(clock: str) -> float:
    h, m = map(int, clock.split(':'))
    w_h, w_m = map(int, WARMUP.split(':'))
    return (h * 60 + m) - (w_h * 60 + w_m)


def step_threads(percent):
    return sum(pf.threads(c, percent) for c in pf.CODES)


def step_target(percent):
    return sum(pf.target(c, percent) for c in pf.CODES)


def end_clock(start: str) -> str:
    h, m = map(int, start.split(':'))
    total = h * 60 + m + STEP_MIN
    return f'{total // 60:02d}:{total % 60:02d}'


def p95(code, mult):
    return int(round(P95[code] * mult, -1))


def err500(code, base):
    return base * ERR_WEIGHT[code]


def tables() -> str:
    rows = []
    for pct, start, share, *_ in STEPS:
        tgt = step_target(pct)
        rows.append([f'{pct} %', f'{start}–{end_clock(start)}', step_threads(pct), pf.num(tgt), pf.num(tgt * share),
                     pf.num(share * 100, 1)])
    out = ['Таблица 1. Ступени теста', pf.table(
        ['Ступень', 'Измерение, МСК', 'Потоков', 'Заданная, оп/ч', 'Фактическая, оп/ч', 'Подано, %'], rows)]
    head = ['Операция'] + [f'{s[0]} %' for s in STEPS]
    rng = np.random.default_rng(511)
    rows = [[c] + [pf.num(min(100.0, s[2] * 100 + rng.normal(0, 0.6)), 1) for s in STEPS] for c in pf.CODES]
    out += ['', 'Таблица 2. Фактическая интенсивность по операциям, % от заданной', pf.table(head, rows)]
    head = ['Операция', 'Порог, мс'] + [f'{s[0]} %' for s in STEPS]
    rows = [[c, pf.num(pf.THRESHOLD[c])] + [pf.num(p95(c, s[5])) for s in STEPS] for c in pf.CODES]
    out += ['', 'Таблица 3. 95-й перцентиль времени операции по ступеням, мс', pf.table(head, rows)]
    head = ['Операция'] + [f'{s[0]} %' for s in STEPS]
    rows = [[c] + [pf.num(err500(c, s[4]), 2) for s in STEPS] for c in pf.CODES]
    out += ['', 'Таблица 4. Доля ошибок по операциям, %', pf.table(head, rows)]
    names = ['CPU efr-api, среднее по 4 серверам, %', 'CPU efr-cft-adapter, %', 'CPU БД, %', 'Диск БД, утилизация %',
             'CPU efr-nt-gen01, %', 'CPU efr-nt-gen02, %', 'HikariCP: активных на экземпляр (из 40)',
             'HikariCP: ожидающих, всего']
    rows = [[name] + [s[6 + n] for s in STEPS] for n, name in enumerate(names)]
    rows.insert(1, ['Память efr-api, среднее по 4 серверам, %'] + [m for m in MEM_APP])
    rows.insert(3, ['Память efr-cft-adapter, %'] + [m for m in MEM_ADAPTER])
    rows.insert(5, ['Память БД, %'] + [m for m in MEM_DB])
    rows.insert(10, ['Heap JMeter на генераторах, % от 6 ГБ'] + [m for m in MEM_GEN])
    out += ['', 'Таблица 5. Утилизация по ступеням', pf.table(['Показатель'] + [f'{s[0]} %' for s in STEPS], rows)]
    return '\n'.join(out)


def series(rng):
    """Ряды по 15 с: прогрев 10 мин на 50 %; каждая ступень — разгон 1 поток/с, затем 10 мин измерения."""
    blocks = [(0, STEP_MIN, STEPS[0], 0.0)]
    for s in STEPS:
        ramp_min = step_threads(s[0]) / 60  # разгон 1 поток в секунду (методика 3.4)
        blocks.append((minute_of(s[1]) - ramp_min, ramp_min, s, 1.0))
        blocks.append((minute_of(s[1]), STEP_MIN, s, 0.0))
    t, rows = [], []
    for start, length, s, rising in blocks:
        n = max(1, int(length * 4))
        for i in range(n):
            t.append(start + i / 4)
            pct, _, share, e503, e500, mult, cpu_app, cpu_ad, cpu_db, disk, g1, g2, act, pend = s
            ramp = (i + 1) / n if rising else 1.0
            target = step_target(pct) / 3600
            delivered = target * share * ramp
            requests = sum(pf.target(c, pct) * REQUESTS[c] for c in pf.CODES) / 3600 * share * ramp
            rows.append([target, *charts.noisy(rng, [delivered], 0.02), charts.noisy(rng, requests * (1 - e503 / 100), 0.02),
                         max(0.0, charts.noisy(rng, requests * e503 / 100, 0.15)) if e503 else 0.0,
                         max(0.0, charts.noisy(rng, requests * e500 / 100, 0.6)),
                         *charts.noisy(rng, [cpu_app, cpu_db, g1, g2], 0.04),
                         min(40.0, charts.noisy(rng, act, 0.04)), max(0.0, charts.noisy(rng, pend, 0.12)) if pend else 0.0])
        if not rising:
            t.append(start + length)
            rows.append([np.nan] * 11)
    return charts.minutes(f'{DAY} {WARMUP}', t), np.array(rows, dtype=float)


def draw(img: Path) -> list:
    rng = np.random.default_rng(1105)
    t, a = series(rng)
    files = {
        '11-throughput.png': ('Рисунок 1. Интенсивность операций', {'Заданная': a[:, 0], 'Фактическая': a[:, 1]},
                              'оп/с', None, None, None, 'Grafana · JMeter'),
        '11-codes.png': ('Рисунок 2. Ответы по кодам', {'200': a[:, 2], '503': a[:, 3], '500': a[:, 4]},
                         'ответов/с', None, None, ['#56A64B', '#FF780A', '#F2495C'], 'Grafana · JMeter'),
        '11-hikari.png': ('Рисунок 3. Пул соединений HikariCP', {'Активные, среднее на экземпляр': a[:, 9],
                                                                  'Ожидающие, всего': a[:, 10]},
                          'соединений', 40, 'maximumPoolSize = 40', None, 'Grafana · Prometheus'),
        '11-cpu.png': ('Рисунок 4. Загрузка CPU', {'efr-api, среднее': a[:, 5], 'БД efr-nt-db01': a[:, 6],
                                                   'efr-nt-gen01': a[:, 7], 'efr-nt-gen02': a[:, 8]},
                       '%', 70, 'порог генератора 70 %', None, 'Grafana · Zabbix'),
    }
    for name, (title, data, unit, threshold, label, colors, source) in files.items():
        ylim = (0, 105) if unit == '%' else None
        charts.panel(img / name, title, t, data, unit, threshold, label, ylim, colors, source)
    return list(files)
