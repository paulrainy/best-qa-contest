"""Регрессии лишних ошибок протоколов; задуманные дефекты сохраняются."""
import importlib
from pathlib import Path

import numpy as np
import pytest

import build_protocols as bp

SOURCE = Path(__file__).resolve().parents[1] / '1c-load-review/jury/source/protocols'


@pytest.fixture
def data(monkeypatch):
    monkeypatch.syspath_prepend(str(SOURCE))
    return {unit: importlib.import_module(f'data_{unit}') for unit in range(11, 16)}


def table_rows(text, caption):
    lines = text.splitlines()
    start = next(n for n, line in enumerate(lines) if line.startswith(caption))
    rows = []
    for line in lines[start + 3:]:
        if not line.startswith('|'):
            break
        rows.append(bp.cells(line))
    return rows


def number(value):
    return float(value.replace(' ', '').replace(',', '.').replace('−', '-'))


def capture(data, unit, monkeypatch, tmp_path):
    plots = {}

    def record(path, title, when, series, metric_unit, *args, **kwargs):
        plots[path.name] = (title, when, series, metric_unit)

    monkeypatch.setattr(data[unit].charts, 'panel', record)
    data[unit].draw(tmp_path)
    return plots


def test_maximum_operation_intensities_sum_to_total(data):
    tables = data[11].tables()
    steps = table_rows(tables, 'Таблица 1.')
    operations = table_rows(tables, 'Таблица 2.')
    # Профиль и пейсинги из методики, независимо от nt_profile.target().
    threads = [42, 33, 8, 16, 6, 10, 8, 20, 3, 5]
    pacing = [15, 15, 20, 20, 20, 20, 40, None, 10, 10]
    for col, percent in enumerate([50, 100, 125, 150, 175, 200]):
        targets = [7200 * percent / 100 if pace is None else
                   int(base * percent / 100 + 0.5) * 3600 / pace
                   for base, pace in zip(threads, pacing)]
        total = sum(target * number(row[col + 1]) / 100 for target, row in zip(targets, operations))
        assert abs(total - number(steps[col][4])) <= sum(targets) * 0.0005 + 0.5


def test_generator_cpu_cannot_exceed_100_percent(data):
    _, series = data[11].series(np.random.default_rng(1105))
    assert np.nanmax(series[:, 7:9]) <= 100
    assert np.nanmin(series[:, 7:9]) >= 0


def test_stability_total_p95_does_not_aggregate_window_percentiles(data, monkeypatch):
    before = data[12].tables()
    monkeypatch.setattr(data[12], 'p95', lambda code: np.full(1000, 999999.0))
    assert data[12].tables() == before


@pytest.mark.parametrize('unit', range(11, 16))
def test_protocol_contains_business_and_server_graphs(data, unit, monkeypatch, tmp_path):
    plots = capture(data, unit, monkeypatch, tmp_path)
    for kind in ['throughput', 'p95', 'errors', 'server-cpu', 'memory', 'disk']:
        assert any(kind in name for name in plots), (unit, kind)
    cpu = next(value[2] for name, value in plots.items() if 'server-cpu' in name)
    memory = next(value[2] for name, value in plots.items() if 'memory' in name)
    servers = [*(f'efr-nt-app{n:02d}' for n in range(1, 5)), 'efr-nt-int01', 'efr-nt-int02',
               'efr-nt-db01', 'efr-nt-gen01', 'efr-nt-gen02']
    assert set(cpu) == set(servers)
    assert set(memory) == set(servers)
    for values in [*cpu.values(), *memory.values()]:
        assert np.nanmin(values) >= 0 and np.nanmax(values) <= 100
    assert 'Память efr-nt-gen01, %' in data[unit].tables()
    assert 'Память efr-nt-gen02, %' in data[unit].tables()
    codes = {f'ОП-{n:02d}' for n in range(1, 11)} - ({'ОП-09'} if unit == 13 else set())
    errors = next(value[2] for name, value in plots.items() if 'errors' in name)
    assert set(errors) == codes
    p95 = next(value[2] for name, value in plots.items() if 'p95' in name)
    assert set(p95) == codes
    if unit == 14:
        assert all(when[0].hour == 21 and when[-1].hour == 21 for _, when, _, _ in plots.values())


def test_intended_profile_and_timeout_defects_remain(data):
    assert 'ОП-09' not in data[13].CODES
    assert data[15].FACT_08 == 6400
    counts = importlib.import_module('operation_counts').combine(data[15].operation_counts()['ОП-08'])
    assert counts.other_errors == counts.timeouts == 38
    assert counts.failed / counts.total > 0.01
    assert data[15].TIMEOUTS['ОП-08'] == 38
    assert data[15].THRESHOLD['ОП-08'] == 800
    assert data[12].TOTAL_MIN - data[12].WARMUP_MIN == 240
    assert data[12].LIVE[1] / data[12].LIVE[0] > 1.1


@pytest.mark.parametrize('unit', [13, 15])
def test_comparison_exposes_cpu_and_memory_baselines_for_each_server(data, unit):
    rows = table_rows(data[unit].tables(), 'Таблица 5.' if unit == 13 else 'Таблица 6.')
    servers = {*(f'efr-nt-app{n:02d}' for n in range(1, 5)), 'efr-nt-int01', 'efr-nt-int02',
               'efr-nt-db01', 'efr-nt-gen01', 'efr-nt-gen02'}
    assert {(row[0], row[1]) for row in rows} == {(host, metric) for host in servers for metric in ['CPU', 'Память ОС']}
    for row in rows:
        old, new, change = map(number, row[2:])
        assert abs((new / old - 1) * 100 - change) < 0.1


def test_maximum_operation_shares_differ_and_keep_step_verdict(data):
    """Таблица 2: у операций свой процент поданной интенсивности, но вывод по ступени (3.5) один."""
    rows = table_rows(data[11].tables(), 'Таблица 2.')
    for col, percent in enumerate([50, 100, 125, 150, 175, 200], start=1):
        values = [number(row[col]) for row in rows]
        assert len(set(values)) > 3, percent
        assert max(values) - min(values) <= 1.6, percent
        assert all(value <= 100 for value in values)
        assert all(value >= 95 for value in values) if percent <= 125 else all(value < 95 for value in values)


def test_maximum_503_only_for_operations_served_by_efr_api(data, monkeypatch, tmp_path):
    """ОП-08 идёт в адаптер, ОП-09 — в БД: ответов 503 от efr-api у них быть не может."""
    for percent, operations in data[11].operation_counts().items():
        for code, windows in operations.items():
            total = importlib.import_module('operation_counts').combine(windows)
            if code in ('ОП-08', 'ОП-09'):
                assert total.http503 == 0
            elif percent >= 150:
                assert total.http503 / total.total > 0.01


def test_maximum_step_series_are_not_flat(data):
    _, series = data[11].series(np.random.default_rng(1105))
    step = series[np.isfinite(series[:, 0])][:40]  # прогрев: одна ступень, 10 минут
    for column in [11, 12, 13, 14, 15, 16, 17, 18]:
        assert np.std(step[:, column]) > 0, column


@pytest.mark.parametrize('unit', [12, 13, 15])
def test_error_windows_are_count_weighted(data, unit, monkeypatch, tmp_path):
    plots = capture(data, unit, monkeypatch, tmp_path)
    errors = next(value[2] for name, value in plots.items() if 'errors' in name)
    for code, values in errors.items():
        windows = data[unit].operation_counts()[code]
        total = sum(row.total for row in windows)
        failed = sum(row.other_errors + row.http503 + (row.timeouts if unit != 15 else 0) for row in windows)
        weighted = sum(value * row.total for value, row in zip(values, windows) if row.total) / total
        assert weighted == pytest.approx(100 * failed / total)


@pytest.mark.parametrize('first, second', [(13, 15), (13, 14), (14, 15)])
def test_utilisation_curves_are_not_copied_between_protocols(data, first, second, monkeypatch, tmp_path):
    """Одинаковые кривые в двух протоколах — это «график другого запуска», незаложенный дефект."""
    one = capture(data, first, monkeypatch, tmp_path)
    other = capture(data, second, monkeypatch, tmp_path)
    for kind in ['server-cpu', 'memory', 'disk', 'generator-heap']:
        a, b = one[f'{first}-{kind}.png'][2], other[f'{second}-{kind}.png'][2]
        for host in a:
            assert abs(np.corrcoef(a[host], b[host])[0, 1]) < 0.9, (kind, host)


@pytest.mark.parametrize('unit', range(11, 16))
def test_servers_of_one_group_have_own_curves(data, unit, monkeypatch, tmp_path):
    plots = capture(data, unit, monkeypatch, tmp_path)
    cpu = next(value[2] for name, value in plots.items() if 'server-cpu' in name)
    seen = np.isfinite(cpu['efr-nt-app01'])
    for a, b in [('efr-nt-app01', 'efr-nt-app02'), ('efr-nt-app03', 'efr-nt-app04'), ('efr-nt-int01', 'efr-nt-int02')]:
        ratio = cpu[a][seen] / cpu[b][seen]
        assert np.std(ratio) > 0.005, (a, b)


@pytest.mark.parametrize('unit', [13, 15])
def test_server_means_on_graph_match_comparison_table(data, unit, monkeypatch, tmp_path):
    rows = table_rows(data[unit].tables(), 'Таблица 5.' if unit == 13 else 'Таблица 6.')
    plots = capture(data, unit, monkeypatch, tmp_path)
    for metric, kind in [('CPU', 'server-cpu'), ('Память ОС', 'memory')]:
        series = plots[f'{unit}-{kind}.png'][2]
        for row in rows:
            if row[1] == metric:
                assert float(np.mean(series[row[0]])) == pytest.approx(number(row[3]), abs=0.06), row
    changes = {number(row[4]) for row in rows if row[0].startswith('efr-nt-app') and row[1] == 'CPU'}
    assert len(changes) > 1  # у серверов приложений изменение не одинаковое до сотых


def test_os_memory_changes_slowly(data, monkeypatch, tmp_path):
    for unit in [13, 15]:
        memory = capture(data, unit, monkeypatch, tmp_path)[f'{unit}-memory.png'][2]
        for host, values in memory.items():
            assert np.max(np.abs(np.diff(values))) < 1.0, (unit, host)
            assert np.max(values) - np.min(values) < 4.0, (unit, host)


def test_control_run_error_graph_is_not_clipped_and_total_is_below_table(data, monkeypatch, tmp_path):
    limits = {}

    def record(path, title, when, series, unit, threshold=None, label=None, ylim=None, *args, **kwargs):
        limits[path.name] = (series, ylim)

    monkeypatch.setattr(data[14].charts, 'panel', record)
    data[14].draw(tmp_path)
    series, ylim = limits['14-errors.png']
    assert ylim is None or max(np.max(values) for values in series.values()) <= ylim[1]
    windows = data[14].operation_counts()['ОП-06']
    weighted = sum(value * row.total for value, row in zip(series['ОП-06'], windows)) / sum(row.total for row in windows)
    assert 2.39 < weighted < 2.41
    tables = data[14].tables()
    assert 'Ошибки, всего' not in tables
    assert 'Доля ошибок за прогон, все операции — 0,14 %.' in tables.split('\n\n')
    assert all(len(row) == 5 and row[4] for row in table_rows(tables, 'Таблица 2.'))


def test_small_error_shares_keep_two_decimals_in_legend(data):
    fmt = data[11].charts.fmt
    assert fmt(0.05, '%') == '0,05 %'
    assert fmt(0.6, '%') == '0,60 %'
    assert fmt(1.4, '%') == '1,4 %'
    assert fmt(0.0, '%') == '0 %'
    assert fmt(46.0, '%') == '46,0 %'  # тот же формат, что у соседнего 39,8 %
    assert fmt(10.0, 'оп/с') == '10,0 оп/с'
    assert fmt(5600.0, 'мс') == '5 600 мс'


@pytest.mark.parametrize('unit, caption', [(12, 'Таблица 1.'), (13, 'Таблица 2.'), (14, 'Таблица 2.'),
                                           (15, 'Таблица 3.')])
def test_delivered_intensity_differs_by_operation(data, unit, caption):
    rows = table_rows(data[unit].tables(), caption)
    ratios = [number(row[2]) / number(row[1]) for row in rows if not (unit == 15 and row[0] == 'ОП-08')]
    assert len({round(ratio, 3) for ratio in ratios}) > 3
    assert min(ratios) >= 0.95  # 3.5: нагрузка подана


def test_control_and_hotfix_runs_do_not_share_delivered_numbers(data):
    one = [row[2] for row in table_rows(data[14].tables(), 'Таблица 2.')]
    other = [row[2] for row in table_rows(data[15].tables(), 'Таблица 3.')]
    assert sum(a == b for a, b in zip(one, other)) <= 2


def test_maximum_and_baseline_runs_do_not_share_p95(data):
    step = [row[3] for row in table_rows(data[11].tables(), 'Таблица 3.') if row[0] != 'ОП-09']
    baseline = [row[3] for row in table_rows(data[13].tables(), 'Таблица 2.')]
    assert sum(a == b for a, b in zip(step, baseline)) <= 1


def test_maximum_operations_outside_pool_slow_down_less(data):
    rows = {row[0]: [number(value) for value in row[1:]] for row in table_rows(data[11].tables(), 'Таблица 3.')}
    for code, (limit, *steps) in rows.items():
        growth = steps[5] / steps[1]  # 200 % к 100 %
        assert (growth < 1.5) == (code in ('ОП-08', 'ОП-09')), code
        assert all(value <= limit for value in steps[:4]), code  # до 150 % все в порогах
    over = [code for code, (limit, *steps) in rows.items() if steps[4] > limit]
    assert over == ['ОП-02', 'ОП-03', 'ОП-04', 'ОП-05', 'ОП-06', 'ОП-07']  # как в выводе протокола


def test_stability_total_p95_lies_within_window_values(data):
    for code, total in data[12].TOTAL_P95.items():
        windows = data[12].p95(code)[data[12].T >= data[12].WARMUP_MIN]
        assert np.percentile(windows, 50) < total < np.percentile(windows, 99.5), code


def test_stability_load_ramps_after_warmup(data):
    load = data[12].LOAD
    steps = np.diff(load)
    assert steps.max() < 0.2  # не мгновенная ступень 50 → 100 %
    assert load[data[12].T >= data[12].WARMUP_MIN + data[12].RAMP_MIN].min() == 1.0


def test_graph_maximum_is_not_fixed_share_of_mean(data, monkeypatch, tmp_path):
    for unit in [13, 15]:
        cpu = capture(data, unit, monkeypatch, tmp_path)[f'{unit}-server-cpu.png'][2]
        ratios = {round(float(np.max(cpu[host]) / np.mean(cpu[host])), 3)
                  for host in ['efr-nt-db01', 'efr-nt-gen01', 'efr-nt-gen02']}
        assert len(ratios) == 3, unit


def test_control_run_heap_peak_matches_conclusion(data, monkeypatch, tmp_path):
    heap = capture(data, 14, monkeypatch, tmp_path)['14-heap.png'][2]
    assert 4.35 <= np.max(heap['Занято']) < 4.45
    assert np.max(heap['После полной сборки, весь heap']) < 2.2


def test_baseline_graphs_keep_operation_colours(data, monkeypatch, tmp_path):
    palettes = {}

    def record(path, title, when, series, unit, threshold=None, label=None, ylim=None, colors=None, *a, **k):
        palettes[path.name] = colors

    monkeypatch.setattr(data[13].charts, 'panel', record)
    data[13].draw(tmp_path)
    full = data[13].charts.COLORS
    assert palettes['13-p95.png'][-1] == full[9] and palettes['13-errors.png'][-1] == full[9]  # ОП-10


def test_utilisation_table_groups_pool_metrics(data):
    names = [row[0] for row in table_rows(data[11].tables(), 'Таблица 5.')]
    assert names[-3:] == ['Heap JMeter на генераторах, % от 6 ГБ', 'HikariCP: активных на экземпляр (из 40)',
                          'HikariCP: ожидающих, всего']


def test_comparison_tables_use_one_minus_sign(data):
    for unit in [13, 15]:
        rows = table_rows(data[unit].tables(), 'Таблица 5.' if unit == 13 else 'Таблица 6.')
        assert not any(cell.startswith('-') for row in rows for cell in row)


def test_window_p95_legend_has_no_interval_aggregates(data):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    try:
        data[11].charts.legend_table(ax, {'ОП-01': np.array([100.0, 9000.0])}, ['red'], 'мс',
                                     summarize=False)
        labels = [cell.get_text().get_text() for table in ax.tables for cell in table.get_celld().values()]
        assert labels == ['', '— ОП-01']
    finally:
        plt.close(fig)


@pytest.mark.parametrize('unit', range(11, 16))
def test_window_p95_panels_disable_aggregate_legend(data, unit, monkeypatch, tmp_path):
    options = []

    def record(path, *args, **kwargs):
        if 'p95' in path.name:
            options.append(kwargs.get('summarize', True))

    monkeypatch.setattr(data[unit].charts, 'panel', record)
    data[unit].draw(tmp_path)
    assert options == [False]


def test_window_counts_sum_to_interval(data):
    counts = importlib.import_module('operation_counts')
    windows = counts.split_counts(counts.Counts(714, 1, 2, 3), [1, 0, 2, 3], seed=7)
    assert [sum(getattr(row, field) for row in windows) for field in
            ('total', 'other_errors', 'http503', 'timeouts')] == [714, 1, 2, 3]
    assert windows[1].total == 0
    assert all(row.failed <= row.total for row in windows)
    assert windows == counts.split_counts(counts.Counts(714, 1, 2, 3), [1, 0, 2, 3], seed=7)


@pytest.mark.parametrize('args', [(-1,), (1, 2), (1, 0, 1, 1), (1.5,), (True,)])
def test_error_categories_do_not_overlap(data, args):
    with pytest.raises(ValueError):
        importlib.import_module('operation_counts').Counts(*args)


def test_aggregate_error_share_is_count_weighted(data):
    counts = importlib.import_module('operation_counts')
    windows = [counts.Counts(1, 1), counts.Counts(99)]
    assert counts.error_values(windows).tolist() == [100.0, 0.0]
    assert counts.error_summary(windows) == (1.0, 100.0)


def test_empty_window_is_not_zero_percent(data):
    counts = importlib.import_module('operation_counts')
    assert np.isnan(counts.error_values([counts.Counts(0)])[0])


@pytest.mark.parametrize('unit,caption', [(12, 'Таблица 1.'), (13, 'Таблица 2.'), (15, 'Таблица 3.')])
def test_error_percentages_are_realizable(data, unit, caption):
    counts = importlib.import_module('operation_counts')
    operations = data[unit].operation_counts()
    for row in table_rows(data[unit].tables(), caption):
        total = counts.combine(operations[row[0]])
        shown_errors = total.other_errors  # 13 скрывает 503, 15 скрывает таймауты
        assert number(row[5]) == round(shown_errors / total.total * 100, 2)
        minutes = 250 if unit == 12 else 60
        assert abs(number(row[2]) - total.total * 60 / minutes) <= 0.5
    if unit == 13:
        assert counts.combine(operations['ОП-07']).total == 714
        assert table_rows(data[unit].tables(), caption)[6][5] == '0,00'


@pytest.mark.parametrize('unit', [12, 13, 14, 15])
def test_throughput_counts_match_tables_and_graph(data, unit, monkeypatch, tmp_path):
    operations = data[unit].operation_counts()
    plots = capture(data, unit, monkeypatch, tmp_path)
    actual = plots[f'{unit}-throughput.png'][2]['Фактическая']
    assert sum(actual) * 15 == pytest.approx(sum(row.total for rows in operations.values() for row in rows))


def test_response_codes_partition_request_count(data):
    from datetime import datetime, timedelta

    when, values = data[11].series(np.random.default_rng(1105))
    for pct, clock, *_ in data[11].STEPS:
        start = datetime.fromisoformat(f'{data[11].DAY} {clock}')
        mask = np.array([start <= time < start + timedelta(minutes=10) for time in when])
        rows = values[mask]
        expected = sum(data[11].REQUESTS[code] * sample.total
                       for code, windows in data[11].operation_counts()[pct].items() for sample in windows)
        assert np.nansum(rows[:, 2:5]) * 15 == pytest.approx(expected)
        assert np.allclose(rows[np.isfinite(rows[:, 2]), 2:5] * 15,
                           np.round(rows[np.isfinite(rows[:, 2]), 2:5] * 15))


@pytest.mark.parametrize('unit', range(11, 16))
def test_window_p95_exists_only_with_successful_operations(data, unit, monkeypatch, tmp_path):
    plots = capture(data, unit, monkeypatch, tmp_path)
    values = plots[f'{unit}-p95.png'][2]
    counts = (data[11].series(np.random.default_rng(1105), with_counts=True)[2] if unit == 11
              else data[unit].operation_counts())
    for code, series in values.items():
        assert np.array_equal(np.isfinite(series), [row.successful > 0 for row in counts[code]]), code
