"""Verify committed author inventories and hashes without repeating their runtime matrix."""
import hashlib
import importlib.util
import json
import subprocess
import sys
import tomllib
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import xml.etree.ElementTree as ET

OUT = Path(__file__).parent
ROOT = Path('/tmp/final-python-independent.73EapA/repo')
REF = ROOT / 'final-task/1d-python/jury/reference'
EVIDENCE = REF / 'evidence'
TOOLS = ROOT / 'final-task/jury/tools'
spec = importlib.util.spec_from_file_location('checker', TOOLS / 'check_reference_results.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
catalog = json.loads((TOOLS / 'reference-test-catalog.json').read_text())
expected = catalog['python']['tests']
assert len(expected) == len(set(expected)) == 63
assert len(catalog['java']['tests']) == 61
old_catalog = json.loads(subprocess.check_output(['git', 'show', '7fbed02c2e2f795a60cc8797f4bc67a2e30e0479:final-task/jury/tools/reference-test-catalog.json'], cwd=ROOT))
assert catalog['java'] == old_catalog['java']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(path):
    root = ET.parse(path).getroot()
    cases = list(root.iter('testcase'))
    return {'cases': len(cases), 'failure': len(list(root.iter('failure'))),
            'error': len(list(root.iter('error'))), 'skipped': len(list(root.iter('skipped'))),
            'sha256': sha(path)}


results = {'author_matrix': [], 'other_full': [], 'independent': [], 'distribution': []}
jar_sha = sha(ROOT / 'final-task/1d-python/participant/stand/transfer-stand.jar')
lock_sha = sha(REF / 'uv.lock')
for java in ('17', '21'):
    summary = json.loads((EVIDENCE / ('java' + java) / 'summary.json').read_text())
    assert summary['stand_sha256'] == jar_sha and summary['lock_sha256'] == lock_sha
    assert len(summary['runs']) == 5
    for run in summary['runs']:
        path = EVIDENCE / ('java' + java) / ('python' + run['python'])
        assert run['pytest_exit'] == run['exact_checker_exit'] == 0
        assert run['full'] == 63 and run['unit'] == 11
        assert not checker.validate_reports(path / 'full', expected)
        full, unit = counts(path / 'full/results.xml'), counts(path / 'unit/results.xml')
        assert full['cases'] == 63 and unit['cases'] == 11
        assert all(full[key] == unit[key] == 0 for key in ('failure', 'error', 'skipped'))
        version = (path / 'version.txt').read_text()
        assert version == run['version']
        sync = (path / 'sync.log').read_text()
        if java == '17':
            expected_packages = 14 if run['python'] in ('311', '312') else 13
            assert 'Creating virtual environment' in sync and f'Installed {expected_packages} packages' in sync
        results['author_matrix'].append({'java': java, 'python': run['python'], 'version': version,
                                         'full': full, 'unit': unit, 'sync_sha256': sha(path / 'sync.log')})
for path in [EVIDENCE / 'repeatability' / name for name in ('first', 'second', 'random')] + [EVIDENCE / 'author-sql/full']:
    assert not checker.validate_reports(path, expected)
    file = next(path.glob('*.xml'))
    results['other_full'].append({'path': str(path.relative_to(REF)), **counts(file)})
for name in ('full', 'recovery'):
    assert not checker.validate_reports(OUT / name, expected)
    results['independent'].append({'path': name, **counts(OUT / name / 'results.xml')})
results['independent_helpers'] = counts(OUT / 'helpers/results.xml')

# Recompute the saved monetary reconciliation using Decimal, not its summary counters.
sql = json.loads((EVIDENCE / 'author-sql/sql.json').read_text(), parse_float=Decimal)
checks = sql['checks']
assert sql['accounts'] == len(checks[0]['params']) == len(checks[0]['rows']) == 125
assert all(row['balance'] == row['posted'] for row in checks[0]['rows'])
grouped = defaultdict(list)
for row in checks[1]['rows']:
    grouped[row['transfer_id']].append(row)
assert len(grouped) == len(checks[1]['params']) == sql['transfers'] == 47
for transfer_id, rows in grouped.items():
    first = rows[0]
    credits = [r for r in rows if r['direction'] == 'CREDIT']
    assert len(credits) == 1
    if first['status'] == 'COMPLETED':
        assert credits[0]['posting_type'] == 'AMOUNT' and credits[0]['posted_amount'] == first['amount']
    else:
        assert first['status'] == 'FAILED'
        assert credits[0]['posting_type'] == 'REFUND' and credits[0]['posted_amount'] == first['amount'] + first['commission']
http = [json.loads(line, parse_float=Decimal) for line in (EVIDENCE / 'author-sql/http.jsonl').read_text().splitlines()]
accounts = {json.loads(r['response'])['accountNumber'] for r in http if r['path'] == '/api/test/accounts' and r['status'] == 201}
transfers = {json.loads(r['response'])['transferId'] for r in http if r['path'] == '/api/v1/transfers' and r['status'] == 202}
assert accounts == set(checks[0]['params']) and transfers == set(checks[1]['params'])
results['author_sql'] = {'accounts': len(accounts), 'transfers': len(transfers), 'decimal_recomputed_violations': 0,
                         'sha256': sha(EVIDENCE / 'author-sql/sql.json')}

# Every tracked participant file has the manifest bytes; no reference/test source is distributed.
files = subprocess.check_output(['git', 'ls-files', 'final-task/1d-python/participant'], cwd=ROOT, text=True).splitlines()
manifest = (ROOT / 'final-task/jury/stand-manifest.md').read_text()
lfs_count = 0
for name in files:
    path = ROOT / name
    digest = sha(path)
    assert f'| {digest} | {name} |' in manifest, name
    assert not ({'jury', 'starters', 'tests', '.venv', '__pycache__'} & set(path.parts))
    git_bytes = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT)
    is_lfs = git_bytes.startswith(b'version https://git-lfs.github.com/spec/v1')
    if is_lfs:
        assert ('oid sha256:' + digest).encode() in git_bytes
        assert not path.read_bytes().startswith(b'version https://git-lfs.github.com/spec/v1')
        lfs_count += 1
    results['distribution'].append({'path': name, 'sha256': digest, 'lfs': is_lfs})
assert len(files) == 53 and lfs_count == 48
project = tomllib.loads((REF / 'pyproject.toml').read_text())
lock = tomllib.loads((REF / 'uv.lock').read_text())
assert project['project']['requires-python'] == lock['requires-python'] == '>=3.11'
assert (REF / '.python-version').read_text().strip() == '3.11'
results['project'] = {'requires_python': lock['requires-python'], 'lock_sha256': lock_sha,
                      'packages': [{'name': p['name'], 'version': p['version']} for p in lock['package']]}
(OUT / 'evidence-audit.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
print('PASS: 10 author matrix full+helper inventories; 4 other full; own 2 full+helpers; SQL125/47; 53 manifest files/48 LFS.')
