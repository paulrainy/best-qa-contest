import json

import pytest

import load_places as lp


@pytest.mark.parametrize('kind, text, keys', [
    ('jmx', '`Вход → POST /auth/login`, поле «Path»', {'jmx:Вход → POST /auth/login'}),
    ('jmx', '`Test Plan`', {'jmx:Test Plan'}),
    ('json', 'Панель «95-й перцентиль», запрос A', {'панель:95-й перцентиль'}),
    ('json', 'Переменная $host', {'переменная:host'}),
    ('json', 'Дашборд, ссылки', {'дашборд'}),
    ('sql', 'строки 14–16', {'строка:14', 'строка:15', 'строка:16'}),
    ('sql', 'Строка 3', {'строка:3'}),
    ('protocol', 'Раздел 12.2, Таблица 3', {'раздел:12.2', 'таблица:3'}),
    ('protocol', 'Рисунок 2', {'рисунок:2'}),
    ('protocol', 'Шапка', {'шапка'}),
    ('protocol', 'Название', {'название'}),
    ('sql', 'где-то в середине', set()),
])
def test_place_keys(kind, text, keys):
    assert lp.place_keys(kind, text) == keys


def test_targets_sql_skips_blank_lines(tmp_path):
    path = tmp_path / '19-x.sql'
    path.write_text('SELECT 1;\n\nSELECT 2;\n', encoding='utf-8')
    assert lp.targets('sql', path) == {'строка:1', 'строка:3'}


def panel(pid, title, **extra):
    return {'id': pid, 'title': title, 'type': 'timeseries', 'gridPos': {'x': 0, 'y': 0, 'w': 12, 'h': 8},
            'datasource': {'type': 'influxdb', 'uid': 'influxdb-nt'},
            'targets': [{'refId': 'A', 'query': 'SELECT 1'}], **extra}


def dashboard(panels, variables=('host',)):
    return {'title': 'D', 'uid': 'd', 'schemaVersion': 39, 'panels': panels,
            'templating': {'list': [{'name': name, 'type': 'query'} for name in variables]}}


def write(tmp_path, data, raw=None):
    path = tmp_path / '16-x.json'
    path.write_text(raw if raw is not None else json.dumps(data, ensure_ascii=False), encoding='utf-8')
    return path


def test_targets_dashboard(tmp_path):
    row = {'id': 10, 'title': 'Сервер', 'type': 'row', 'gridPos': {'x': 0, 'y': 8, 'w': 24, 'h': 1},
           'panels': [panel(11, 'CPU')]}
    path = write(tmp_path, dashboard([panel(1, 'RPS'), row]))
    assert lp.targets('json', path) == {'дашборд', 'панель:RPS', 'панель:Сервер', 'панель:CPU', 'переменная:host'}


@pytest.mark.parametrize('data, raw, message', [
    (None, '{"title": ', 'не разбирается'),
    (dashboard([panel(2, 'A'), panel(2, 'B')]), None, 'повтор id 2'),
    (dashboard([panel(1, 'RPS', targets=[{'query': 'x'}])]), None, 'панель «RPS»: запрос без refId'),
    (dashboard([{k: v for k, v in panel(1, 'RPS').items() if k != 'datasource'}]), None,
     'панель «RPS»: нет datasource'),
    ({'title': 'D', 'panels': []}, None, 'нет uid'),
])
def test_check_dashboard_errors(tmp_path, data, raw, message):
    errors = lp.check_dashboard(write(tmp_path, data, raw))
    assert any(message in e for e in errors), errors


def test_check_dashboard_accepts_valid(tmp_path):
    assert lp.check_dashboard(write(tmp_path, dashboard([panel(1, 'RPS')]))) == []


def test_describe_panel_shows_query(tmp_path):
    path = write(tmp_path, dashboard([panel(1, 'RPS')]))
    assert 'A: SELECT 1' in lp.describe('json', path, 'панель:RPS')
