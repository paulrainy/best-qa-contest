#!/usr/bin/env python3
"""Диагностический прогон Н1; сбрасывает данные. Полный нагрузочный эталон создаётся отдельно."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import math
from pathlib import Path
import re
import time
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from stand_client import Client


def summarize(rows):
    accepted = [r for r in rows if r['code'] == 202 and r.get('valid', True)]
    samples = sorted(r['elapsed_ms'] for r in accepted)
    return {
        'sent': len(rows), 'accepted': len(accepted),
        'http_503': sum(r['code'] == 503 for r in rows),
        'other_errors': sum(r['code'] not in (202, 503) or not r.get('valid', True) for r in rows),
        'accepted_post_p95_ms': samples[math.ceil(.95 * len(samples)) - 1] if samples else None,
        'within_2s_percent': 100 * sum(r.get('final_ms') is not None and r['final_ms'] <= 2000 for r in accepted) / len(accepted) if accepted else None,
        'unfinished': sum(r.get('final_ms') is None for r in accepted),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rate', nargs='?', type=float, default=60)
    parser.add_argument('duration', nargs='?', type=float, default=15)
    parser.add_argument('--drain', type=float, default=120)
    parser.add_argument('--output', type=Path, default=Path('build/final-load-check'))
    args = parser.parse_args()
    if args.rate <= 0 or args.duration <= 0 or args.drain <= 0: parser.error('Значения должны быть положительными')
    api = Client(); api.call('POST', '/api/test/reset', {})
    start = time.monotonic()

    def one(i):
        src = '40817810' + f'{(i % 2000 + 1) * 10 + 1:012d}'
        dst = '40817810' + f'{((i + 1) % 2000 + 1) * 10 + 1:012d}'
        request = Request(api.base + '/api/v1/transfers', method='POST', data=json.dumps({'fromAccount': src, 'toAccount': dst, 'amount': 100}).encode(), headers={'Content-Type': 'application/json', 'Idempotency-Key': str(uuid.uuid4())})
        begin = time.monotonic()
        row = {'start_s': begin - start, 'final_ms': None, 'valid': False}
        try:
            try: response = urlopen(request, timeout=30)
            except HTTPError as exc: response = exc
            with response:
                row['code'] = response.status
                body = json.loads(response.read())
                row['transferId'] = body.get('transferId')
                row['valid'] = row['code'] != 202 or bool(row['transferId']) and body.get('status') == 'PROCESSING'
        except Exception as exc:
            row.update(code=0, error=str(exc))
        row['elapsed_ms'] = (time.monotonic() - begin) * 1000
        return row

    futures = []
    with ThreadPoolExecutor(max_workers=64) as pool:
        for i in range(math.ceil(args.rate * args.duration)):
            delay = start + i / args.rate - time.monotonic()
            if delay > 0: time.sleep(delay)
            futures.append(pool.submit(one, i))
        rows = [f.result() for f in futures]
    with urlopen(api.base + '/metrics', timeout=10) as response:
        match = re.search(r'^stand_queue_messages\{queue="accounting.transfer-created"\} (\S+)', response.read().decode(), re.M)
        depth = float(match.group(1)) if match else None
    remaining = [r for r in rows if r['code'] == 202 and r['valid']]
    deadline = time.monotonic() + args.drain
    while remaining and time.monotonic() < deadline:
        next_poll = []
        for row in remaining:
            if time.monotonic() >= deadline:
                next_poll.append(row); continue
            transfer = api.call('GET', '/api/v1/transfers/' + row['transferId'])
            if transfer['status'] in ('COMPLETED', 'FAILED'):
                row['final_status'] = transfer['status']
                row['final_ms'] = (datetime.fromisoformat(transfer['completedAt']) - datetime.fromisoformat(transfer['createdAt'])).total_seconds() * 1000
            else: next_poll.append(row)
        remaining = next_poll
        if remaining: time.sleep(.2)
    summary = summarize(rows)
    summary.update(diagnostic_only=True, target_rps=args.rate, duration_s=args.duration, started_in_interval=sum(r['start_s'] < args.duration for r in rows), queue_after_arrivals=depth)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix('.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    args.output.with_suffix('.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))
    return bool(summary['other_errors'])


if __name__ == '__main__': raise SystemExit(main())
