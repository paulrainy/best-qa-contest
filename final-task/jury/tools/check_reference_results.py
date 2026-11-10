#!/usr/bin/env python3
"""Отличает два известных нарушения ТЗ от неполного или сломанного прогона."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def validate_reports(directory, expected, known):
    errors, seen, failed = [], set(), set()
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
            bad = [c for c in case if c.tag in ('failure', 'error', 'skipped')]
            if not bad:
                continue
            if len(bad) != 1 or bad[0].tag != 'failure':
                errors.append(f'{identity}: error/skip или несколько ошибок')
                continue
            failure = bad[0]
            marker = known.get(identity)
            message = failure.get('message', '')
            failure_type = failure.get('type', '')
            pytest_assertion = not failure_type and message.startswith('AssertionError: ')
            if pytest_assertion:
                message = message.removeprefix('AssertionError: ')
            assertion_type = pytest_assertion or failure_type in (
                'java.lang.AssertionError', 'org.opentest4j.AssertionFailedError', 'AssertionError')
            if not marker or not assertion_type or not (message.startswith('[' + marker + ']') or message.startswith(marker + ':') or (message.splitlines() or [''])[0] == marker):
                errors.append(f'{identity}: неизвестная причина падения: {message[:180]}')
            else:
                failed.add(identity)
    for missing in sorted(set(expected) - seen):
        errors.append(f'{missing}: результат отсутствует')
    for extra in sorted(seen - set(expected)):
        errors.append(f'{extra}: незарегистрированный тест')
    for missing in sorted(set(known) - failed):
        errors.append(f'{missing}: известное целевое падение отсутствует')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('direction', choices=('java', 'python'))
    parser.add_argument('report_dir', type=Path)
    args = parser.parse_args()
    catalog = json.loads(Path(__file__).with_name('reference-test-catalog.json').read_text(encoding='utf-8'))[args.direction]
    errors = validate_reports(args.report_dir, catalog['tests'], catalog['known'])
    for error in errors:
        print(error)
    if not errors:
        print(f'{args.direction}: полный состав подтверждён; только F10/F16, без ошибок и skip')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
