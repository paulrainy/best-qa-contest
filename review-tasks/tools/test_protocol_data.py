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
    return float(value.replace(' ', '').replace(',', '.'))


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
    assert data[15].ERRORS['ОП-08'] == 0.6
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
