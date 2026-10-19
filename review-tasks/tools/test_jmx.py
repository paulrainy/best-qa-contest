import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import build_jmx
import jmx

HERE = Path(__file__).resolve().parent


def small_plan(keep_alive=True):
    return jmx.test_plan('01 Вход', [
        jmx.thread_group('Thread Group', threads=2, rampup=2, duration=60, children=[
            jmx.transaction('Вход', children=[
                jmx.http_request('POST /auth/login', 'POST', '/api/v1/auth/login', keep_alive=keep_alive,
                                 connect_timeout=5000, response_timeout=30000),
            ]),
        ]),
    ])


def test_render_header_and_hash_trees():
    root = ET.fromstring(jmx.render(small_plan()).encode('utf-8'))
    assert root.tag == 'jmeterTestPlan'
    assert root.get('jmeter') == '5.6.3'

    def walk(tree):
        children = list(tree)
        assert len(children) % 2 == 0
        for element, sub in zip(children[::2], children[1::2]):
            assert element.tag != 'hashTree'
            assert sub.tag == 'hashTree'
            walk(sub)

    walk(root.find('hashTree'))


def test_paths():
    assert set(jmx.paths(small_plan())) == {
        'Test Plan', 'Thread Group', 'Thread Group → Вход', 'Thread Group → Вход → POST /auth/login'}


def test_duplicate_sibling_names_rejected():
    plan = jmx.test_plan('x', [jmx.thread_group('Thread Group', 1, 1, 1, children=[
        jmx.http_request('GET /a', 'GET', '/a'), jmx.http_request('GET /a', 'GET', '/a')])])
    with pytest.raises(ValueError, match='повтор имени «GET /a»'):
        jmx.render(plan)


def test_name_with_arrow_rejected():
    plan = jmx.test_plan('x', [jmx.thread_group('A → B', 1, 1, 1)])
    with pytest.raises(ValueError, match='недопустимый символ в имени «A → B»'):
        jmx.render(plan)


def test_disabled_element():
    plan = jmx.test_plan('x', [jmx.thread_group('Thread Group', 1, 1, 1, children=[
        jmx.view_results_tree('View Results Tree', enabled=False)])])
    root = ET.fromstring(jmx.render(plan).encode('utf-8'))
    collector = root.find('.//ResultCollector')
    assert collector.get('enabled') == 'false'


def test_http_request_props():
    root = ET.fromstring(jmx.render(small_plan(keep_alive=False)).encode('utf-8'))
    sampler = root.find('.//HTTPSamplerProxy')
    props = {p.get('name'): p.text for p in sampler}
    assert props['HTTPSampler.use_keepalive'] == 'false'
    assert props['HTTPSampler.connect_timeout'] == '5000'
    assert props['HTTPSampler.method'] == 'POST'


def test_render_is_deterministic():
    assert jmx.render(small_plan()) == jmx.render(small_plan())


SOURCE = '''
import jmx

FILE = '01-login'


def plan(fixed):
    return jmx.test_plan('01 Вход', [
        jmx.thread_group('Thread Group', threads=2, rampup=2, duration=60, children=[
            jmx.http_request('POST /auth/login', 'POST', '/api/v1/auth/login', keep_alive=fixed),
        ]),
    ])
'''


def make_task(tmp_path):
    scripts = tmp_path / 'jury' / 'source' / 'scripts'
    scripts.mkdir(parents=True)
    (scripts / '01_login.py').write_text(SOURCE, encoding='utf-8')
    return tmp_path


def test_build_writes_both_versions(tmp_path):
    task = make_task(tmp_path)
    build_jmx.build(task)
    broken = (task / 'participant' / 'scripts' / '01-login.jmx').read_text(encoding='utf-8')
    fixed = (task / 'jury' / 'fixed' / 'scripts' / '01-login.jmx').read_text(encoding='utf-8')
    assert 'use_keepalive">false' in broken
    assert 'use_keepalive">true' in fixed


def test_stale_detects_edited_file(tmp_path):
    task = make_task(tmp_path)
    build_jmx.build(task)
    assert build_jmx.stale(task) == []
    path = task / 'participant' / 'scripts' / '01-login.jmx'
    path.write_text(path.read_text(encoding='utf-8') + ' ', encoding='utf-8')
    assert build_jmx.stale(task) == ['01']


def test_tree_lists_paths(tmp_path):
    task = make_task(tmp_path)
    text = build_jmx.tree(task, '01')
    assert 'Thread Group → POST /auth/login  [HTTPSamplerProxy]' in text


def full_plan():
    """План, в котором есть каждая фабрика jmx.py, — для проверки в настоящем JMeter."""
    return jmx.test_plan('99 Все элементы', variables={'pacing': '15000'}, comment='проверка', children=[
        jmx.http_defaults('HTTP Request Defaults', domain='${__P(efr.host)}', port='${__P(efr.port,443)}',
                          protocol='https', connect_timeout=5000, response_timeout=30000, content_encoding='UTF-8'),
        jmx.header_manager('HTTP Header Manager', [('Content-Type', 'application/json'),
                                                    ('X-Request-Id', '${__UUID()}')]),
        jmx.cookie_manager('HTTP Cookie Manager'),
        jmx.auth_manager('HTTP Authorization Manager', 'https://${__P(cft.host)}', 'nt_cft', '${__P(cft.password)}'),
        jmx.user_variables('Переменные', {'amount': '100000'}),
        jmx.backend_listener_influx('Backend Listener', 'http://influxdb-nt:8086/write?db=jmeter', 'efr-test'),
        jmx.view_results_tree('View Results Tree', enabled=False),
        jmx.summary_report('Summary Report', enabled=False),
        jmx.thread_group('Thread Group', '${__P(threads,4)}', '${__P(rampup,4)}', '${__P(duration,3600)}', children=[
            jmx.precise_throughput_timer('Precise Throughput Timer', 7200, duration='${__P(duration,3600)}'),
            jmx.constant_throughput_timer('Constant Throughput Timer', 60.0, enabled=False),
            jmx.once_only('Вход', children=[
                jmx.csv_data_set('users_op01.csv', 'data/users_op01.csv', recycle=False, stop_thread=True),
                jmx.http_request('POST /auth/login', 'POST', '/api/v1/auth/login', body='{"login":"${login}"}',
                                 children=[jmx.json_extractor('JSON Extractor token', 'token', '$.token',
                                                              default='token_NOT_FOUND')]),
            ]),
            jmx.transaction('ОП-01 Поиск клиента', children=[
                jmx.http_request('GET /clients', 'GET', '/api/v1/clients', params=[('passport', '${passport}')],
                                 keep_alive=False, embedded=True, connect_timeout=5000, response_timeout=30000,
                                 children=[
                                     jmx.regex_extractor('Regex clientId', 'clientId', '"id":"(.+?)"',
                                                         default='clientId_NOT_FOUND'),
                                     jmx.response_assertion('Response Assertion', ['"status":"ACTIVE"']),
                                     jmx.response_assertion('Код 200', ['200'], field=jmx.RESPONSE_CODE,
                                                            test_type=jmx.EQUALS),
                                     jmx.json_assertion('JSON Assertion', '$.status', 'ACTIVE'),
                                     jmx.duration_assertion('Duration Assertion', 800),
                                     jmx.jsr223('post', 'JSR223 PostProcessor', 'vars.put("a", "1")'),
                                 ]),
                jmx.uniform_random_timer('Пауза', 3000, 4000.0),
                jmx.constant_timer('Constant Timer', 1000),
            ]),
            jmx.if_controller('Если найден', '${__jexl3("${clientId}" != "clientId_NOT_FOUND")}', children=[
                jmx.loop_controller('Loop Controller', 2, children=[jmx.debug_sampler('Debug Sampler')]),
            ]),
            jmx.jsr223('pre', 'JSR223 PreProcessor', 'vars.put("sig", "x")', cache=False),
            jmx.beanshell_pre('BeanShell PreProcessor', 'vars.put("b", "2");'),
            jmx.jsr223('sampler', 'JSR223 Sampler', 'SampleResult.setIgnore()'),
            jmx.jdbc_config('JDBC Connection Configuration', 'efr', 'jdbc:postgresql://efr-nt-db01:5432/efr',
                            'efr_report', '${__P(db.password)}', 10),
            jmx.jdbc_request('ОП-09 Отчёт', 'efr', 'SELECT 1 WHERE ? = ?', args='${a},${a}', types='INTEGER,INTEGER'),
            jmx.flow_control_action('Пейсинг', children=[
                jmx.jsr223('timer', 'JSR223 Timer', 'return 0'),
            ]),
        ]),
    ])


@pytest.mark.skipif(not os.environ.get('JMETER_HOME'), reason='нет JMETER_HOME — JMeter не скачан')
def test_jmeter_round_trip(tmp_path):
    path = tmp_path / 'all.jmx'
    path.write_text(jmx.render(full_plan()), encoding='utf-8')
    code, output = build_jmx.check([path])
    assert code == 0, output
    assert f'OK {path}' in output


@pytest.mark.skipif(not os.environ.get('JMETER_HOME'), reason='нет JMETER_HOME — JMeter не скачан')
def test_jmeter_flags_misspelled_property(tmp_path):
    sampler = jmx.http_request('GET /a', 'GET', '/a')
    sampler.props.append(jmx.S('HTTPSampler.conect_timeout', '5000'))
    plan = jmx.test_plan('x', [jmx.thread_group('Thread Group', 1, 1, children=[sampler])])
    path = tmp_path / 'bad.jmx'
    path.write_text(jmx.render(plan), encoding='utf-8')
    code, output = build_jmx.check([path])
    assert code == 1
    assert 'Thread Group → GET /a: HTTPSampler.conect_timeout: наше «5000», GUI «»' in output


def test_sources_can_import_helpers(tmp_path):
    task = make_task(tmp_path)
    scripts = task / 'jury' / 'source' / 'scripts'
    (scripts / 'helpers_1g.py').write_text("NAME = 'GET /from-helper'\n", encoding='utf-8')
    (scripts / '02_helper.py').write_text(
        "import jmx\nimport helpers_1g\nFILE = '02-helper'\n\n\ndef plan(fixed):\n"
        "    return jmx.test_plan('x', [jmx.thread_group('Thread Group', 1, 1, children=[\n"
        "        jmx.http_request(helpers_1g.NAME, 'GET', '/h')])])\n", encoding='utf-8')
    assert 'Thread Group → GET /from-helper' in build_jmx.tree(task, '02')


def test_multiline_body_saved_with_crlf_like_gui():
    plan = jmx.test_plan('x', [jmx.thread_group('Thread Group', 1, 1, children=[
        jmx.http_request('POST /a', 'POST', '/a', body='{\n  "a": 1\n}')])])
    text = jmx.render(plan)
    assert '{&#xd;\n  &quot;a&quot;: 1&#xd;\n}' in text or '{&#xd;\n  "a": 1&#xd;\n}' in text
    value = ET.fromstring(text.encode('utf-8')).find('.//elementProp[@elementType="HTTPArgument"]/stringProp[@name="Argument.value"]').text
    assert value == '{\r\n  "a": 1\r\n}'
