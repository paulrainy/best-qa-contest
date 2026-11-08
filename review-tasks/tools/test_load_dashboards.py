"""Смысл конфигурации дашбордов: лишние ошибки и задуманные пять дефектов."""
import importlib.util
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[1] / '1c-load-review/jury/source/monitoring/dashboards.py'
spec = importlib.util.spec_from_file_location('load_dashboards', SOURCE)
boards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boards)


@pytest.mark.parametrize('fixed', [False, True])
@pytest.mark.parametrize('make', [boards.jmeter, boards.app])
def test_window_p95_has_no_interval_legend_calculations(make, fixed):
    panels = [panel for panel in make(fixed)['panels'] if panel['type'] == 'timeseries' and
              any('pct95.0' in target.get('query', '') or 'histogram_quantile' in target.get('expr', '')
                  for target in panel['targets'])]
    assert panels
    assert all(panel['options']['legend']['calcs'] == [] for panel in panels)


@pytest.mark.parametrize('fixed', [False, True])
def test_intended_stat_percentile_defect_remains_only_for_participant(fixed):
    panels = [panel for panel in boards.jmeter(fixed)['panels'] if panel['type'] == 'stat']
    assert len(panels) == (0 if fixed else 1)
    if not fixed:
        assert 'mean("pct95.0")' in panels[0]['targets'][0]['query']


@pytest.mark.parametrize('fixed', [False, True])
def test_live_data_indicator_is_kept_with_context(fixed):
    panels = [p for p in boards.app(fixed)['panels'] if
              any('jvm_gc_live_data_size_bytes' in t['expr'] for t in p['targets'])]
    assert len(panels) == 1
    assert panels[0]['fieldConfig']['defaults']['unit'] == 'bytes'
    assert panels[0].get('description')


@pytest.mark.parametrize('fixed', [False, True])
def test_api_dashboard_keeps_exactly_its_five_seeded_differences(fixed):
    panels = {p['title']: p for p in boards.app(fixed)['panels']}
    requests = panels['Запросов за интервал']['targets'][0]['expr']
    assert ('increase(' in requests) == fixed
    assert ('rate(' in requests) != fixed
    p95 = panels['p95 по API, все экземпляры']['targets'][0]['expr']
    assert ('sum by (le, uri)' in p95) == fixed
    heap = panels['Heap по экземплярам']['fieldConfig']['defaults']['custom']['stacking']['mode']
    assert heap == ('none' if fixed else 'normal')
    wait = panels['Ожидание соединения HikariCP']['fieldConfig']['defaults']['unit']
    assert wait == ('s' if fixed else 'ms')
    assert ('HikariCP: ожидающие соединения' in panels) == fixed
