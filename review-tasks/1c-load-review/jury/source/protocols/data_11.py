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
MEM_GEN_OS = [[42, 55, 62, 68, 72, 75], [40, 53, 60, 66, 70, 73]]
WARMUP = '21:00'
STEP_MIN = 10
# p95 на 100 %, мс. От прогона сравнения с эталоном (nt_profile.P95_100) отличается на 1–3 %,
# как отличаются два прогона в разные дни
P95 = {'ОП-01': 410, 'ОП-02': 600, 'ОП-03': 1190, 'ОП-04': 1930, 'ОП-05': 830, 'ОП-06': 1390, 'ОП-07': 5650,
       'ОП-08': 300, 'ОП-09': 2320, 'ОП-10': 510}
# ответы 500 по операциям относительно среднего по ступени
ERR_WEIGHT = {'ОП-01': 0.5, 'ОП-02': 0.6, 'ОП-03': 1.4, 'ОП-04': 1.8, 'ОП-05': 1.2, 'ОП-06': 1.5, 'ОП-07': 0.8,
              'ОП-08': 0.3, 'ОП-09': 0.9, 'ОП-10': 0.6}
# запросов на операцию — для графика ответов
REQUESTS = {'ОП-01': 1, 'ОП-02': 2, 'ОП-03': 1, 'ОП-04': 3, 'ОП-05': 3, 'ОП-06': 2, 'ОП-07': 1, 'ОП-08': 1,
            'ОП-09': 1, 'ОП-10': 1}
# 503 отдаёт efr-api: ОП-08 идёт в адаптер АБС, ОП-09 — напрямую в БД, у них 503 нет
NOT_API = ('ОП-08', 'ОП-09')
SIDE = 0.25  # эти операции идут мимо пула efr-api: их время растёт вчетверо слабее, чем у остальных


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


def growth(code, mult):
    """Рост p95 на ступени: множитель ступени, для операций мимо пула efr-api — его четверть."""
    return 1 + (mult - 1) * SIDE if code in NOT_API else mult


def p95(code, mult):
    return int(round(P95[code] * growth(code, mult), -1))


def err500(code, base):
    return base * ERR_WEIGHT[code]


def op_shares():
    """Доля поданной интенсивности по операциям, % от заданной, по ступеням.

    У операций небольшой разброс вокруг доли ступени. Сумма по операциям, взвешенная по заданной
    интенсивности, даёт фактическую интенсивность таблицы 1.
    """
    rng = np.random.default_rng(1102)
    result = []
    for pct, _, share, *_ in STEPS:
        weights = np.array([pf.target(c, pct) for c in pf.CODES])
        room = min(0.7, 100 - share * 100)
        spread = rng.uniform(-room, room, len(pf.CODES))
        spread -= (spread * weights).sum() / weights.sum()
        values = np.round(np.minimum(share * 100 + spread, 100.0), 1)
        fact, limit = weights.sum() * share, weights.sum() * 0.0002
        for _ in range(100):  # остаток после округления до 0,1 % убираем шагами по 0,1 %
            rest = fact - (weights * values).sum() / 100
            if abs(rest) <= limit:
                break
            step = 0.1 if rest > 0 else -0.1
            fits = [n for n in np.argsort(-weights)
                    if weights[n] * 0.001 <= 2 * abs(rest) and values[n] + step <= 100.0]
            if not fits:
                break
            values[fits[0]] = round(values[fits[0]] + step, 1)
        result.append(dict(zip(pf.CODES, values)))
    return result


def tables() -> str:
    rows = []
    for pct, start, share, *_ in STEPS:
        tgt = step_target(pct)
        rows.append([f'{pct} %', f'{start}–{end_clock(start)}', step_threads(pct), pf.num(tgt), pf.num(tgt * share),
                     pf.num(share * 100, 1)])
    out = ['Таблица 1. Ступени теста', pf.table(
        ['Ступень', 'Измерение, МСК', 'Потоков', 'Заданная, оп/ч', 'Фактическая, оп/ч', 'Подано, %'], rows)]
    head = ['Операция'] + [f'{s[0]} %' for s in STEPS]
    # Общая и пооперационная интенсивности описывают один и тот же профиль.
    shares = op_shares()
    rows = [[c] + [pf.num(step[c], 1) for step in shares] for c in pf.CODES]
    out += ['', 'Таблица 2. Фактическая интенсивность по операциям, % от заданной', pf.table(head, rows)]
    head = ['Операция', 'Порог, мс'] + [f'{s[0]} %' for s in STEPS]
    rows = [[c, pf.num(pf.THRESHOLD[c])] + [pf.num(p95(c, s[5])) for s in STEPS] for c in pf.CODES]
    out += ['', 'Таблица 3. 95-й перцентиль времени операции по ступеням, мс', pf.table(head, rows)]
    head = ['Операция'] + [f'{s[0]} %' for s in STEPS]
    rows = [[c] + [pf.num(err500(c, s[4]), 2) for s in STEPS] for c in pf.CODES]
    out += ['', 'Таблица 4. Доля ошибок по операциям, %', pf.table(head, rows)]
    def column(n):
        return [s[n] for s in STEPS]

    # Порядок строк — как в таблицах утилизации остальных протоколов, метрики пула — в конце.
    rows = [
        ['CPU efr-api, среднее по 4 серверам, %', *column(6)],
        ['Память efr-api, среднее по 4 серверам, %', *MEM_APP],
        ['CPU efr-cft-adapter, %', *column(7)],
        ['Память efr-cft-adapter, %', *MEM_ADAPTER],
        ['CPU БД, %', *column(8)],
        ['Память БД, %', *MEM_DB],
        ['Диск БД, утилизация %', *column(9)],
        ['CPU efr-nt-gen01, %', *column(10)],
        ['CPU efr-nt-gen02, %', *column(11)],
        ['Память efr-nt-gen01, %', *MEM_GEN_OS[0]],
        ['Память efr-nt-gen02, %', *MEM_GEN_OS[1]],
        ['Heap JMeter на генераторах, % от 6 ГБ', *MEM_GEN],
        ['HikariCP: активных на экземпляр (из 40)', *column(12)],
        ['HikariCP: ожидающих, всего', *column(13)],
    ]
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
            api = sum(pf.target(c, pct) * REQUESTS[c] for c in pf.CODES if c not in NOT_API) / 3600 * share * ramp
            http503 = max(0.0, charts.noisy(rng, api * e503 / 100, 0.15)) if e503 else 0.0
            http500 = max(0.0, charts.noisy(rng, requests * e500 / 100, 0.6))
            step = STEPS.index(s)
            rows.append([target, delivered, requests - http503 - http500, http503, http500,
                         *np.clip(charts.noisy(rng, [cpu_app, cpu_db, g1, g2], 0.04), 0, 100),
                         min(40.0, charts.noisy(rng, act, 0.04)), max(0.0, charts.noisy(rng, pend, 0.12)) if pend else 0.0,
                         MEM_APP[step] + rng.normal(0, 0.25), MEM_ADAPTER[step] + rng.normal(0, 0.25),
                         MEM_DB[step] + rng.normal(0, 0.12), charts.noisy(rng, disk, 0.06),
                         charts.noisy(rng, cpu_ad, 0.05),
                         MEM_GEN_OS[0][step] + rng.normal(0, 0.3), MEM_GEN_OS[1][step] + rng.normal(0, 0.3),
                         charts.noisy(rng, MEM_GEN[step], 0.04), mult, e503, e500])
        if not rising:
            t.append(start + length)
            rows.append([np.nan] * 22)
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
        charts.panel(img / name, title, t, data, unit, threshold, label, ylim, colors, source, summarize=unit != 'мс')
    rows = len(a)
    charts.panel(img / '11-p95.png', 'Рисунок 5. 95-й перцентиль по окнам', t,
                 {c: charts.noisy(rng, P95[c] * growth(c, a[:, 19]), 0.04, rows) for c in pf.CODES}, 'мс',
                 source='Grafana · JMeter', summarize=False)
    errors = {}
    for c in pf.CODES:
        http503 = 0.0 if c in NOT_API else charts.noisy(rng, a[:, 20], 0.12, rows)
        errors[c] = np.clip(http503 + charts.noisy(rng, a[:, 21] * ERR_WEIGHT[c], 0.35, rows), 0, None)
    charts.panel(img / '11-errors.png', 'Рисунок 6. Доля ошибок по операциям', t, errors, '%',
                 source='Grafana · JMeter')
    columns = {
        'CPU efr-api, среднее по 4 серверам, %': 5, 'CPU БД, %': 6,
        'CPU efr-nt-gen01, %': 7, 'CPU efr-nt-gen02, %': 8,
        'Память efr-api, среднее по 4 серверам, %': 11,
        'Память efr-cft-adapter, %': 12, 'Память БД, %': 13,
        'Диск БД, утилизация %': 14, 'CPU efr-cft-adapter, %': 15,
        'Память efr-nt-gen01, %': 16, 'Память efr-nt-gen02, %': 17,
        'Heap JMeter на генераторах, % от 6 ГБ': 18,
    }
    return [*files, '11-p95.png', '11-errors.png',
            *charts.server_panels(img, 11, t, {name: a[:, col] for name, col in columns.items()}, 7)]
