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
