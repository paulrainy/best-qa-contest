"""Независимый пересчёт Windows-повтора: без кода analyse.py для чисел, затем сверка с summary и повторным анализом."""
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import sys
from uuid import UUID

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parents[2]
sys.path.insert(0, str(REFERENCE))
from tools.analyse import analyse  # noqa: E402


def jtl(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return [r for r in csv.DictReader(stream) if r['label'] == 'POST transfer']


def ms(value):
    return datetime.fromisoformat(value).timestamp() * 1000


def nearest_rank(values):
    values = sorted(values)
    return values[math.ceil(.95 * len(values)) - 1] if values else None


def accepted(row):
    try:
        UUID(row['transferId'])
        ms(row['createdAt'])
    except ValueError:
        return False
    return row['responseCode'] == '202' and row['success'] == 'true' and row['apiStatus'] == 'PROCESSING'


def recount(run):
    posts = jtl(run / 'samples.jtl')
    states = [json.loads(line) for line in (run / 'transfers.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    by_id = {s['transferId']: s for s in states}
    ok = [r for r in posts if accepted(r)]
    origin = int(posts[0]['originMs'])
    assert len({r['originMs'] for r in posts}) == 1
    assert len({r['idempotencyKey'] for r in posts}) == len(posts), 'повтор ключа'
    assert len({r['transferId'] for r in ok}) == len(ok) == len(by_id) == len(states), 'ID и статусы не совпадают'
    summary = json.loads((run / 'summary.json').read_text(encoding='utf-8'))
    windows = []
    for part in summary['intervals']:
        cohort = [r for r in posts if part['start_s'] <= (int(r['timeStamp']) - origin) / 1000 < part['end_s']]
        good = [r for r in cohort if accepted(r)]
        delays = [ms(by_id[r['transferId']]['completedAt']) - ms(r['createdAt']) for r in good
                  if by_id[r['transferId']]['status'] in ('COMPLETED', 'FAILED')]
        mine = dict(posts=len(cohort), accepted=len(good), p95_ms=nearest_rank(int(r['elapsed']) for r in good),
                    within_2s=sum(d <= 2000 for d in delays), unfinished=len(good) - len(delays))
        theirs = dict(posts=part['posts'], accepted=part['accepted'], p95_ms=part['accepted_post_p95_ms'],
                      within_2s=part['within_2s'], unfinished=part['unfinished'])
        assert mine == theirs, (mine, theirs)
        windows.append(dict(start_s=part['start_s'], end_s=part['end_s'], **mine))
    again = analyse(run / 'samples.jtl', run / 'metrics.csv', run / 'transfers.jsonl', run / 'profile.properties')
    seconds = []
    for begin, end in ((0, 10), (10, 20), (20, 30), (30, 60), (60, 180)):
        part = [r for r in ok if begin <= (int(r['timeStamp']) - origin) / 1000 < end]
        if part:
            delays = [ms(by_id[r['transferId']]['completedAt']) - ms(r['createdAt']) for r in part]
            seconds.append(dict(start_s=begin, end_s=end, posts=len(part), p95_ms=nearest_rank(int(r['elapsed']) for r in part),
                                over_500ms=sum(int(r['elapsed']) > 500 for r in part),
                                finalization_over_2s=sum(d > 2000 for d in delays)))
    return dict(run=run.name, all_posts=len(posts), unique_keys=len(posts), accepted_ids=len(ok),
                statuses=dict(sorted({s['status']: sum(t['status'] == s['status'] for t in states) for s in states}.items())),
                windows=windows, reanalysis_equal=again == summary, verdict=summary['nft_verdict'],
                metrics_complete=summary['metrics']['complete'], segments=seconds)


def main():
    result = dict(runs=[recount(HERE / name) for name in ('smoke', 'confirmation')])
    raw = jtl(HERE / 'raw-cli' / 'samples.jtl')
    result['raw_cli'] = dict(posts=len(raw), unique_keys=len({r['idempotencyKey'] for r in raw}),
                             accepted=sum(accepted(r) for r in raw))
    result['generator_java25_posts'] = len(jtl(HERE / 'generator-java25' / 'samples.jtl'))
    mac = jtl(REFERENCE / 'evidence' / 'main-java17' / 'confirmation' / 'samples.jtl')
    win = jtl(HERE / 'confirmation' / 'samples.jtl')

    def per_second(rows):
        origin = int(rows[0]['originMs'])
        counts = {}
        for r in rows:
            key = int((int(r['timeStamp']) - origin) / 1000)
            counts[key] = counts.get(key, 0) + 1
        return counts

    a, b = per_second(mac), per_second(win)
    result['same_seed_against_mac_confirmation'] = dict(
        mac_posts=len(mac), windows_posts=len(win),
        seconds_with_equal_counts=sum(a.get(s) == b.get(s) for s in set(a) | set(b)), seconds_total=len(set(a) | set(b)))
    (HERE / 'recount.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Пересчёт совпал:', [r['run'] for r in result['runs']], 'raw', result['raw_cli'])


if __name__ == '__main__':
    main()
