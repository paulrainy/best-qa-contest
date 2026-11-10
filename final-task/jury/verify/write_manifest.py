#!/usr/bin/env python3
"""Фиксирует происхождение сборки и полный состав четырёх participant/."""
import argparse
import hashlib
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--java-version', required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[3]
final = root / 'final-task'
inputs = [final / 'jury/build-stand.sh', Path(__file__).resolve()]
inputs += [p for p in (final / 'jury/source').rglob('*') if p.is_file()]
source = final / 'jury/stand-src'
inputs += [source / 'pom.xml', source / 'proguard.pro']
inputs += [p for p in (source / 'src').rglob('*') if p.is_file()]
for direction in ('1a-java', '1b-manual', '1c-load', '1d-python'):
    inputs += [p for p in (final / direction / 'participant').rglob('*') if p.is_file() and not {'test-data', '__pycache__'}.intersection(p.parts) and p.suffix not in ('.log', '.lck')]
lines = ['# Происхождение стенда', '', 'Сборка: `' + args.java_version + '`; compiler release 17; четыре физические копии одной сборки.', '', 'Хеши фиксируют исходники, параметры, инструкции и runtime. После изменений пересобрать стенд; манифест не править вручную.', '', '| SHA-256 | Путь от корня репозитория |', '| --- | --- |']
for p in sorted(set(inputs)):
    lines.append('| ' + hashlib.sha256(p.read_bytes()).hexdigest() + ' | ' + p.relative_to(root).as_posix() + ' |')
(final / 'jury/stand-manifest.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
