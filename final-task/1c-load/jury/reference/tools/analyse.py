"""Полный JTL: когорты по началу POST, nearest-rank p95, SLO с незавершёнными."""
import argparse
from collections import Counter
from datetime import datetime
import math
from pathlib import Path
from uuid import UUID

try:
    from .common import properties, read_jtl, read_jsonl, utf8_output, windows, write_json
except ImportError:
    from common import properties, read_jtl, read_jsonl, utf8_output, windows, write_json


def timestamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError('Время должно содержать смещение')
    return parsed.timestamp() * 1000


def classify(row):
    code = row.get('responseCode', '')
    if code == '503':
        return 'overload_503'
    if code == '422':
        return 'application_rejection'
    if 'Timeout' in code or 'timeout' in code:
        return 'timeout'
    if code != '202':
        return 'http_or_transport_error'
    try:
        UUID(row.get('transferId', ''))
        timestamp(row.get('createdAt', ''))
        if row.get('apiStatus') != 'PROCESSING' or row.get('success', '').lower() != 'true':
            return 'invalid_202'
    except (ValueError, TypeError):
        return 'invalid_202'
    return 'accepted'


def percentile(values):
    values = sorted(values)
    return values[math.ceil(.95 * len(values)) - 1] if values else None


def counter_rates(samples):
    result = []
    for (start, before), (end, after) in zip(samples, samples[1:]):
        reset = before is not None and after is not None and after < before
        valid = before is not None and after is not None and end > start and not reset
        result.append(dict(start=start, end=end, rate=(after - before) / (end - start) if valid else None, reset=reset))
    return result


def analyse_rows(rows, transfers, intervals, *, smoke=False):
    issues = []
    posts = [r for r in rows if r['label'] == 'POST transfer']
    origins = {int(r['originMs']) for r in posts}
    if len(origins) != 1:
        raise ValueError(f'Нужна одна точка начала подачи, найдено {len(origins)}')
    origin = origins.pop()
    accepted_all = [r for r in posts if classify(r) == 'accepted']
    ids = [r['transferId'] for r in accepted_all]
    if len(set(ids)) != len(ids):
        issues.append('Повторный принятый transferId в JTL')
    statuses = {}
    for transfer in transfers:
        key = transfer['transferId']
        if key in statuses:
            issues.append(f'Повторный результат статуса {key}')
        statuses[key] = transfer
    missing = set(ids) - statuses.keys()
    extra = statuses.keys() - set(ids)
    if missing or extra:
        issues.append(f'Несовпадение принятых ID и статусов: нет {len(missing)}, лишних {len(extra)}')

    def population(selected, duration, target):
        categories = Counter(classify(r) for r in selected)
        accepted = [r for r in selected if classify(r) == 'accepted']
        elapsed = [int(r['elapsed']) for r in accepted]
        within = unfinished = complete = failed = 0
        unknown = []
        delays = []
        for row in accepted:
            state = statuses.get(row['transferId'])
            if state is None:
                unknown.append(row['transferId'])
                continue
            try:
                created = timestamp(row['createdAt'])
                if timestamp(state['createdAt']) != created:
                    raise ValueError('createdAt API отличается от принятого POST')
                status = state['status']
                if state.get('error'):
                    raise ValueError(state['error'])
                if status in ('COMPLETED', 'FAILED'):
                    delay = timestamp(state['completedAt']) - created
                    if delay < 0 or timestamp(state['completedAt']) > state['observedAtMs'] + 1000:
                        raise ValueError('Некорректное время финализации')
                    delays.append(delay)
                    within += delay <= 2000
                    complete += status == 'COMPLETED'
                    failed += status == 'FAILED'
                elif status == 'PROCESSING':
                    unfinished += 1
                    if state['observedAtMs'] < created + 2000:
                        raise ValueError('Не истёк deadline незавершённого перевода')
                else:
                    raise ValueError(f'Неизвестный статус {status}')
            except (ValueError, KeyError, TypeError) as exc:
                unknown.append(row['transferId'])
                issues.append(f"Статус {row['transferId']}: {exc}")
        actual = len(selected) / duration
        expected = target * duration
        tolerance = max(.05 * expected, 3 * math.sqrt(expected)) if smoke else .05 * expected
        load_valid = abs(len(selected) - expected) <= tolerance
        return dict(posts=len(selected), duration_s=duration, target_rps=target, actual_post_rps=actual,
                    expected_posts=expected, tolerance_posts=tolerance, load_valid=load_valid,
                    accepted=len(accepted), accepted_percent=100 * len(accepted) / len(selected) if selected else None,
                    categories=dict(categories), accepted_post_p95_ms=percentile(elapsed),
                    within_2s_percent=100 * within / len(accepted) if accepted and not unknown else None,
                    within_2s=within, completed=complete, failed=failed, unfinished=unfinished,
                    unknown_status=len(unknown), finalization_p95_ms=percentile(delays))

    per_interval = []
    measured_rows = []
    for begin, end, rate in intervals:
        if not 0 <= begin < end or rate <= 0:
            raise ValueError('Неверный измерительный интервал')
        selected = [r for r in posts if begin <= (int(r['timeStamp']) - origin) / 1000 < end]
        measured_rows.extend(selected)
        per_interval.append(dict(start_s=begin, end_s=end, **population(selected, end - begin, rate)))
    duration = sum(end - begin for begin, end, _ in intervals)
    target = sum((end - begin) * rate for begin, end, rate in intervals) / duration
    measured = population(measured_rows, duration, target)
    all_stats = population(posts, max(end for _, end, _ in intervals), target)
    data_complete = not issues and all_stats['unknown_status'] == 0
    load_valid = all(p['load_valid'] for p in per_interval)
    p95, slo = measured['accepted_post_p95_ms'], measured['within_2s_percent']
    verdict = 'UNPROVEN' if not data_complete or not load_valid or p95 is None or slo is None else (
        'PASS' if p95 <= 500 and slo >= 95 else 'FAIL')
    return dict(origin_ms=origin, data_complete=data_complete, issues=list(dict.fromkeys(issues)),
                load_valid=load_valid, nft_verdict=verdict, measured=measured, intervals=per_interval,
                all_posts=all_stats,
                excluded=dict(service_samples=len(rows) - len(posts), outside_measurement_posts=len(posts) - len(measured_rows)))


def metric_summary(metrics, origin, end_s):
    valid = [r for r in metrics if not r['error']]
    times = [int(r['timestampMs']) for r in metrics]
    max_gap = max((b - a for a, b in zip(times, times[1:])), default=None)
    coverage = len(times) >= 2 and times[0] <= origin and times[-1] >= origin + end_s * 1000
    resources = [r for r in metrics if all(r.get(k) for k in ('generatorRssKiB', 'generatorThreads', 'generatorCpuPercent'))]
    return dict(samples=len(metrics), errors=len(metrics) - len(valid),
                             complete=coverage and max_gap <= 12500 and len(valid) == len(metrics) and bool(resources),
                             coverage=coverage, max_gap_ms=max_gap, generator_resource_samples=len(resources),
                             accounting_rates=counter_rates([(int(r['timestampMs']) / 1000,
                                                             float(r['accountingProcessed']) if r['accountingProcessed'] else None)
                                                            for r in metrics]),
                             max_accounting_queue=max((float(r['accountingQueue']) for r in valid if r['accountingQueue']), default=None))


def analyse(jtl, metrics_path, transfers, profile):
    config = properties(profile)
    result = analyse_rows(read_jtl(jtl), read_jsonl(transfers), windows(config), smoke=config['profile.name'] == 'smoke')
    result['metrics'] = metric_summary(read_jtl(metrics_path), result['origin_ms'], max(end for _, end, _ in windows(config)))
    result['nft_confirmation_profile'] = config['profile.name'] == 'confirmation'
    result['profile'] = config['profile.name']
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('jtl', 'metrics', 'transfers', 'profile', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    utf8_output()
    summary = analyse(args.jtl, args.metrics, args.transfers, args.profile)
    write_json(args.output, summary)
    print(summary['nft_verdict'], summary['measured'])
