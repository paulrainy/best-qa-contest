"""Контрольные выборки: фильтрация операций и точные итоговые метрики."""
import csv
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


OP = 'ОП-01 Поиск клиента по паспорту'
OP2 = 'ОП-02 Просмотр карточки клиента'


def jtl(tmp_path, rows, name='results.jtl'):
    path = tmp_path / name
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['timeStamp', 'elapsed', 'label', 'success'])
        writer.writerows(rows)
    return path


def calculate(paths, start=0, end=10000):
    return importlib.import_module('calculate_jtl_metrics').calculate(paths, start, end)


def test_p95_excludes_failures(tmp_path):
    path = jtl(tmp_path, [(0, 10, OP, 'true')] * 90 + [(0, 1000, OP, 'false')] * 10)
    assert calculate([path])[OP] == {
        'total': 100, 'failed': 10, 'p95_ms': 10, 'error_percent': 10.0, 'throughput_per_hour': 36000.0,
    }


def test_p95_uses_more_than_20000_samples(tmp_path):
    path = jtl(tmp_path, [(0, 1000, OP, 'true')] * 20000 + [(0, 10, OP, 'true')] * 20000)
    assert calculate([path])[OP]['p95_ms'] == 1000


def test_only_complete_parent_operations_in_interval(tmp_path):
    path = jtl(tmp_path, [
        (0, 50, OP, 'true'), (90, 20, OP, 'false'),  # прогрев и пересечение начала
        (100, 10, OP, 'true'), (180, 20, OP, 'false'),  # обе границы включены
        (195, 10, OP, 'true'), (201, 1, OP, 'true'),
        (110, 5, 'POST /api/v1/clients/search', 'false'),
        (110, 5, 'POST /api/v1/auth/login', 'false'),
    ])
    result = calculate([path], 100, 200)[OP]
    assert result['total'] == 2
    assert result['failed'] == 1
    assert result['p95_ms'] == 10
    assert result['error_percent'] == 50
    assert result['throughput_per_hour'] == 72000


def test_combines_generators_without_combining_operations(tmp_path):
    first = jtl(tmp_path, [(0, 10, OP, 'true'), (0, 500, OP2, 'false')], 'gen01.jtl')
    second = jtl(tmp_path, [(0, 30, OP, 'true'), (0, 50, OP2, 'true')], 'gen02.jtl')
    result = calculate([first, second])
    assert result[OP]['p95_ms'] == 30
    assert result[OP2]['p95_ms'] == 50
    assert result[OP2]['error_percent'] == 50


def test_no_operations_in_interval_is_not_success(tmp_path):
    path = jtl(tmp_path, [(0, 10, OP, 'true')])
    assert calculate([path], 100, 200)[OP] == {
        'total': 0, 'failed': 0, 'p95_ms': None, 'error_percent': None, 'throughput_per_hour': 0,
    }


def test_all_failures_have_no_p95(tmp_path):
    path = jtl(tmp_path, [(0, 10, OP, 'false')])
    result = calculate([path])[OP]
    assert result['p95_ms'] is None
    assert result['error_percent'] == 100


def test_nearest_rank_and_single_sample(tmp_path):
    path = jtl(tmp_path, [(0, value, OP, 'true') for value in range(1, 21)] + [(0, 77, OP2, 'true')])
    result = calculate([path])
    assert result[OP]['p95_ms'] == 19
    assert result[OP2]['p95_ms'] == 77


@pytest.mark.parametrize('row', [
    ('bad', 10, OP, 'true'), (0, -1, OP, 'true'), (0, '1.5', OP, 'true'),
    (0, 10, OP, 'unknown'), (0, 10, OP, ''), (-1, 10, OP, 'true'),
])
def test_rejects_malformed_sample(tmp_path, row):
    with pytest.raises(ValueError, match='results.jtl:2'):
        calculate([jtl(tmp_path, [row])])


def test_rejects_missing_column(tmp_path):
    path = tmp_path / 'bad.jtl'
    path.write_text('timeStamp,elapsed,label\n0,10,test\n')
    with pytest.raises(ValueError, match='success'):
        calculate([path])


def test_rejects_duplicate_path(tmp_path):
    path = jtl(tmp_path, [])
    with pytest.raises(ValueError, match='повтор'):
        calculate([path, path.parent / '.' / path.name])


@pytest.mark.parametrize('start,end', [(100, 100), (200, 100), (-1, 100)])
def test_rejects_invalid_interval(tmp_path, start, end):
    with pytest.raises(ValueError, match='интервал'):
        calculate([jtl(tmp_path, [])], start, end)


def test_cli_outputs_json(tmp_path):
    path = jtl(tmp_path, [(0, 123, OP, 'true')])
    script = Path(__file__).with_name('calculate_jtl_metrics.py')
    result = subprocess.run([sys.executable, str(script), str(path), '--start-ms', '0', '--end-ms', '1000'],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)[OP]['p95_ms'] == 123
