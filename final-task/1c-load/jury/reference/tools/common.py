import csv
import json
import os
from pathlib import Path
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def utf8_output():
    """Windows-каналы (Git Bash, перенаправление) иначе получают cp1252 и падают на кириллице."""
    if os.name == 'nt':
        for stream in (sys.stdout, sys.stderr):
            stream.reconfigure(encoding='utf-8')


def properties(path):
    result = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            result[key.strip()] = value.strip()
    return result


def windows(profile):
    return [tuple(map(float, item.split(':'))) for item in profile['measurement.windows'].split(';')]


def request(base, path, method='GET', timeout=10):
    req = Request(base.rstrip('/') + path, method=method,
                  data=b'{}' if method == 'POST' else None,
                  headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode('utf-8')


def api(base, path, method='GET', timeout=10):
    return json.loads(request(base, path, method, timeout))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def read_jtl(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
