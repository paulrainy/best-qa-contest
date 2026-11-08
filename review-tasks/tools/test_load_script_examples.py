"""Пример ОП-05 проходит через настоящие извлекатели из собираемого JMX."""
import json
import os
from pathlib import Path
import subprocess

import pytest

import build_jmx
import jmx


TASK = Path(__file__).resolve().parents[1] / '1c-load-review'
RUNNER = '''
import groovy.json.JsonOutput
import org.apache.jmeter.extractor.RegexExtractor
import org.apache.jmeter.extractor.json.jsonpath.JSONPostProcessor
import org.apache.jmeter.samplers.SampleResult
import org.apache.jmeter.save.SaveService
import org.apache.jmeter.threads.JMeterContextService
import org.apache.jmeter.threads.JMeterVariables
import org.apache.jmeter.util.JMeterUtils

def home = System.getenv('JMETER_HOME')
JMeterUtils.setJMeterHome(home)
JMeterUtils.loadJMeterProperties("$home/bin/jmeter.properties")
JMeterUtils.initLocale()
def found = []
def walk
walk = { tree ->
    tree.list().each { element ->
        if (element.name in ['Regex taskId', 'JSON Extractor taskId']) found << element
        walk(tree.getTree(element))
    }
}
walk(SaveService.loadTree(new File(args[0])))
assert found.size() == 1
def extractor = found[0]
def ctx = JMeterContextService.getContext()
ctx.setVariables(new JMeterVariables())
def sample = new SampleResult()
sample.setResponseData(new File(args[1]).getText('UTF-8'), 'UTF-8')
sample.setDataType(SampleResult.TEXT)
sample.setSuccessful(true)
ctx.setPreviousResult(sample)
if (extractor instanceof RegexExtractor) extractor.setProperty('RegexExtractor.match_number', '-1')
else {
    assert extractor instanceof JSONPostProcessor
    extractor.setProperty('JSONPostProcessor.match_numbers', '-1')
}
extractor.process()
int count = (ctx.getVariables().get('taskId_matchNr') ?: '0') as int
def values = (0..<count).collect { ctx.getVariables().get('taskId_' + (it + 1)) }
println('CANDIDATES=' + JsonOutput.toJson(values))
'''


@pytest.mark.skipif(not os.environ.get('JMETER_HOME'), reason='нет JMETER_HOME')
@pytest.mark.parametrize('compact', [False, True])
def test_task_id_extractors_match_example(tmp_path, compact):
    source = build_jmx.load_sources(TASK)['05']
    example = source.EXAMPLE.partition(': ')[2].replace(', …', '')
    payload = json.loads(example)
    if compact:
        example = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    response = tmp_path / 'response.json'
    response.write_text(example, encoding='utf-8')
    runner = tmp_path / 'extract.groovy'
    runner.write_text(RUNNER, encoding='utf-8')
    home = os.environ['JMETER_HOME']
    for fixed, expected in [(False, ['TS-20261104-000187', 'CL4471902300417']),
                            (True, ['TS-20261104-000187'])]:
        plan = tmp_path / f'{fixed}.jmx'
        plan.write_text(jmx.render(source.plan(fixed)), encoding='utf-8')
        result = subprocess.run([build_jmx.JAVA, '-Djava.awt.headless=true', '-cp', f'{home}/lib/*:{home}/lib/ext/*',
                                 'groovy.ui.GroovyMain', str(runner), str(plan), str(response)],
                                cwd=tmp_path, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
        line = next(row for row in result.stdout.splitlines() if row.startswith('CANDIDATES='))
        assert json.loads(line.partition('=')[2]) == expected
