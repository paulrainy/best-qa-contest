"""Точные метрики родительских операций по полным CSV JTL, методика 1c, п. 8.3.

python calculate_jtl_metrics.py gen01.jtl gen02.jtl --start-ms 0 --end-ms 3600000
Границы — Unix epoch в миллисекундах; sampleresult.timestamp.start=true.
Входные файлы — непересекающиеся результаты генераторов, без повторов samples.
"""
import argparse
import csv
import json
import re
from pathlib import Path


OPERATION = re.compile(r'^ОП-(?:0[1-9]|10)(?:\s|$)')
FIELDS = {'timeStamp', 'elapsed', 'label', 'success', 'IdleTime'}


def calculate(paths: list[Path], start_ms: int, end_ms: int) -> dict[str, dict]:
    if not 0 <= start_ms < end_ms:
        raise ValueError('Некорректный измерительный интервал')
    resolved = [Path(path).resolve() for path in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError('Входные пути повторяются')
    if not resolved:
        raise ValueError('Не заданы файлы результатов')
    samples = {}
    for path in resolved:
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            missing = FIELDS - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f'{path}: нет полей {", ".join(sorted(missing))}')
            for row in reader:
                try:
                    stamp, elapsed, idle = int(row['timeStamp']), int(row['elapsed']), int(row['IdleTime'])
                    success = row['success'].lower()
                    if stamp < 0 or elapsed < 0 or idle < 0 or success not in ('true', 'false') or None in row:
                        raise ValueError('некорректное значение')
                    label = row['label']
                    if label is None:
                        raise ValueError('нет label')
                except (ValueError, TypeError, AttributeError) as error:
                    raise ValueError(f'{path}:{reader.line_num}: некорректный sample') from error
                if not OPERATION.match(label):
                    continue
                state = samples.setdefault(label, {'total': 0, 'failed': 0, 'elapsed': []})
                if stamp < start_ms or stamp + elapsed + idle > end_ms:
                    continue
                state['total'] += 1
                if success == 'true':
                    state['elapsed'].append(elapsed)
                else:
                    state['failed'] += 1
    result = {}
    for label, state in sorted(samples.items()):
        values = sorted(state['elapsed'])
        total, failed = state['total'], state['failed']
        result[label] = {
            'total': total,
            'failed': failed,
            'p95_ms': values[(95 * len(values) + 99) // 100 - 1] if values else None,
            'error_percent': 100 * failed / total if total else None,
            'throughput_per_hour': total * 3600000 / (end_ms - start_ms),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+', type=Path)
    parser.add_argument('--start-ms', required=True, type=int)
    parser.add_argument('--end-ms', required=True, type=int)
    args = parser.parse_args()
    try:
        result = calculate(args.paths, args.start_ms, args.end_ms)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
