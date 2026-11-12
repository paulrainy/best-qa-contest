"""Сохраняет каждый принятый ID, включая незавершённость и ошибки наблюдения."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time

try:
    from .analyse import classify
    from .common import api, read_jtl, utf8_output
except ImportError:
    from analyse import classify
    from common import api, read_jtl, utf8_output


def collect(rows, base, output, *, drain_s=120, fetch=None):
    accepted = [r for r in rows if r['label'] == 'POST transfer' and classify(r) == 'accepted']
    ids = [r['transferId'] for r in accepted]
    if len(set(ids)) != len(ids):
        raise ValueError('Повторный принятый transferId в JTL')
    remaining = {r['transferId']: r for r in accepted}
    results = {}
    deadline = time.monotonic() + drain_s
    requests = 0
    started = time.time()

    def one(item):
        transfer_id, original = item
        state = dict(transferId=transfer_id, createdAt=original['createdAt'], completedAt=None, status='UNKNOWN')
        try:
            response = fetch(transfer_id) if fetch else api(base, '/api/v1/transfers/' + transfer_id,
                                                            timeout=max(.01, min(5, deadline - time.monotonic())))
            if response['transferId'] != transfer_id:
                raise ValueError('API вернул чужой transferId')
            state.update(response)
        except (OSError, ValueError, KeyError) as exc:
            state['error'] = str(exc)
        state['observedAtMs'] = int(time.time() * 1000)
        return state

    with ThreadPoolExecutor(max_workers=8) as pool:
        while remaining:
            batch = list(remaining.items())
            for offset in range(0, len(batch), 8):
                if time.monotonic() >= deadline:
                    break
                for state in pool.map(one, batch[offset:offset + 8]):
                    requests += 1
                    transfer_id = state['transferId']
                    results[transfer_id] = state
                    if state['status'] in ('COMPLETED', 'FAILED') and not state.get('error'):
                        remaining.pop(transfer_id)
            left = deadline - time.monotonic()
            if not remaining or left <= 0:
                break
            time.sleep(min(.2, left))
    for transfer_id, original in remaining.items():
        if transfer_id not in results:
            results[transfer_id] = dict(transferId=transfer_id, createdAt=original['createdAt'],
                                       completedAt=None, status='UNKNOWN', observedAtMs=int(time.time() * 1000),
                                       error='Drain deadline: статус не получен')
    with Path(output).open('x', encoding='utf-8') as stream:
        for transfer_id in ids:
            stream.write(json.dumps(results[transfer_id], ensure_ascii=False) + '\n')
    Path(output).with_suffix('.survey.json').write_text(json.dumps(dict(requests=requests,
        startedAtMs=int(started * 1000), finishedAtMs=int(time.time() * 1000), drain_s=drain_s,
        accepted=len(ids), remaining=len(remaining)), indent=2) + '\n')
    return list(results.values())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jtl', type=Path, required=True)
    parser.add_argument('--base-url', default='http://localhost:18400')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    utf8_output()
    print(f'Сохранено {len(collect(read_jtl(args.jtl), args.base_url, args.output))} статусов')
