#!/usr/bin/env python3
"""Принимает только полный успешный прогон эталона без исключений для дефектов."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

REJECTED_TAGS = ('failure', 'error', 'skipped', 'flakyFailure', 'flakyError', 'rerunFailure', 'rerunError')


def validate_reports(directory, expected):
    errors, seen = [], set()
    files = sorted(Path(directory).glob('*.xml'))
    if not expected:
        return ['Каталог тестов ещё не утверждён для этого направления']
    if not files:
        return [f'{directory}: XML-отчётов нет']
    for file in files:
        try:
            root = ET.parse(file).getroot()
        except (OSError, ET.ParseError) as exc:
            errors.append(f'{file}: {exc}')
            continue
        if root.tag not in ('testsuite', 'testsuites'):
            errors.append(f'{file}: неизвестный корневой элемент {root.tag}')
        for case in root.iter('testcase'):
            identity = case.get('classname', '') + '#' + case.get('name', '')
            if identity in seen:
                errors.append(f'{identity}: повторный результат')
            seen.add(identity)
            # Surefire с rerunFailingTestsCount пишет flaky*/rerun*: падение, прошедшее при повторе, тоже отказ.
            bad = [c for c in case if c.tag in REJECTED_TAGS]
            if not bad:
                continue
            for failure in bad:
                message = failure.get('message', '')
                errors.append(f'{identity}: {failure.tag}: {message[:180]}')
    for missing in sorted(set(expected) - seen):
        errors.append(f'{missing}: результат отсутствует')
    for extra in sorted(seen - set(expected)):
        errors.append(f'{extra}: незарегистрированный тест')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('direction', choices=('java', 'python'))
    parser.add_argument('report_dir', type=Path)
    args = parser.parse_args()
    catalog = json.loads(Path(__file__).with_name('reference-test-catalog.json').read_text(encoding='utf-8'))[args.direction]
    errors = validate_reports(args.report_dir, catalog['tests'])
    for error in errors:
        print(error)
    if not errors:
        print(f'{args.direction}: полный состав подтверждён; все проверки успешны, без ошибок и skip')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
