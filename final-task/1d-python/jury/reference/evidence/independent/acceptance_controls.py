"""Independent acceptance driver. No stand sources or mutations of the main checkout."""
import configparser
import hashlib
import json
import platform
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
import xml.etree.ElementTree as ET

OUT = Path(__file__).parent
ROOT = Path('/tmp/final-python-independent.73EapA/repo')
REF = ROOT / 'final-task/1d-python/jury/reference'
UV = ['uv', 'run', '--locked', '--python', '3.11']
CHECK = UV + ['python', '../../../jury/tools/check_reference_results.py', 'python']
results = {}


def run(name, command, expected=0):
    started = time.time()
    proc = subprocess.run(command, cwd=REF, text=True, capture_output=True, timeout=60)
    (OUT / (name + '.log')).write_text('$ ' + ' '.join(command) + '\n' + proc.stdout + proc.stderr)
    results[name] = {'command': command, 'exit': proc.returncode, 'seconds': time.time() - started}
    assert proc.returncode == expected, (name, proc.returncode, proc.stdout, proc.stderr)
    return proc


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def state():
    return {name: json.load(urllib.request.urlopen('http://localhost:18400/api/test/' + name, timeout=5))
            for name in ('clock', 'consumers')}


environment = {'date': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'platform': platform.platform(),
               'clone': str(ROOT), 'local_origin': '/Users/paul/Documents/work/best-qa-contest',
               'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'lock_sha256': sha(REF / 'uv.lock'),
               'jar_sha256': sha(ROOT / 'final-task/1d-python/participant/stand/transfer-stand.jar'),
               'python': run('python-version', UV + ['python', '-c', 'import sys,platform;print(sys.version);print(sys.executable);print(platform.platform())']).stdout,
               'uv': run('uv-version', ['uv', '--version']).stdout,
               'java': run('java-version', ['/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home/bin/java', '-version']).stderr}
(OUT / 'environment.json').write_text(json.dumps(environment, indent=2))

original_config_hash = sha(REF / 'config/stand.ini')
bad_config = configparser.ConfigParser()
bad_config.read(REF / 'config/stand.ini')
with socket.socket() as probe:
    probe.bind(('127.0.0.1', 0))
    bad_port = probe.getsockname()[1]
bad_config['database']['port'] = str(bad_port)
with (OUT / 'bad-db.ini').open('w') as output:
    bad_config.write(output)
bad = run('bad-db', UV + ['pytest', 'tests/test_transfers.py::test_readiness_and_read_only_connections',
                         '--stand-config', str(OUT / 'bad-db.ini'), '--junitxml=' + str(OUT / 'bad-db/results.xml')], 1)
assert 'БД недоступна' in bad.stdout and str(bad_port) in bad.stdout
bad_cases = list(ET.parse(OUT / 'bad-db/results.xml').getroot().iter('testcase'))
assert len(bad_cases) == 1 and bad_cases[0].find('error') is not None
assert bad_cases[0].find('failure') is None

full_hash = sha(OUT / 'full/results.xml')
run('stale-xml', UV + ['pytest', 'tests', '--junitxml=' + str(OUT / 'full/results.xml')], 4)
assert sha(OUT / 'full/results.xml') == full_hash
http_hash = sha(OUT / 'full-http.jsonl')
run('stale-http', UV + ['pytest', 'tests', '--http-log', str(OUT / 'full-http.jsonl')], 4)
assert sha(OUT / 'full-http.jsonl') == http_hash

# Intentionally altered copies only; not presented as actual test outcomes.
for variant in ('missing', 'failure', 'error', 'skipped', 'duplicate', 'empty'):
    directory = OUT / 'synthetic-xml-controls' / variant
    directory.mkdir(parents=True)
    root = ET.parse(OUT / 'full/results.xml').getroot()
    suite = root.find('testsuite')
    case = suite.find('testcase')
    if variant == 'missing':
        suite.remove(case)
    elif variant in ('failure', 'error', 'skipped'):
        ET.SubElement(case, variant, {'message': 'independent deliberate control'})
    elif variant == 'duplicate':
        suite.append(case)
    if variant != 'empty':
        ET.ElementTree(root).write(directory / 'synthetic.xml')
    run('checker-' + variant, CHECK + [str(directory)], 1)

assert sha(REF / 'config/stand.ini') == original_config_hash
results['default_config_unchanged'] = original_config_hash
results['before_recovery_state'] = state()
run('recovery', UV + ['pytest', 'tests', '--junitxml=' + str(OUT / 'recovery/results.xml'),
                      '--http-log', str(OUT / 'recovery-http.jsonl'), '--order-seed', '20261111'])
run('recovery-check', CHECK + [str(OUT / 'recovery')])
results['final_state'] = state()
assert results['final_state']['clock']['shifted'] is False
assert results['final_state']['consumers'] == {'accounting': 'RUNNING', 'notifications': 'RUNNING'}
results['stale_xml_unchanged_sha256'] = full_hash
results['stale_http_unchanged_sha256'] = http_hash
(OUT / 'controls.json').write_text(json.dumps(results, indent=2, ensure_ascii=False))
print('Independent controls and randomized full recovery: PASS')
