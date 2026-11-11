import csv,json,math,pathlib
from datetime import datetime
project=pathlib.Path(__file__).resolve().parents[1]
checks=[]
for path in sorted((project/'evidence').rglob('summary.json')):
    source=path.parent
    summary=json.loads(path.read_text())
    rows=list(csv.DictReader((source/'samples.jtl').open()))
    statuses={r['transferId']:r for r in map(json.loads,(source/'transfers.jsonl').read_text().splitlines())}
    posts=[r for r in rows if r['label']=='POST transfer']
    accepted=[r for r in posts if r['responseCode']=='202' and r['success']=='true' and r['transferId'] and r['createdAt'] and r['apiStatus']=='PROCESSING']
    accepted_ids={r['transferId'] for r in accepted}
    assert len(statuses)==len(accepted)==len(accepted_ids)
    assert len({r['idempotencyKey'] for r in posts})==len(posts)
    origin=int(posts[0]['originMs'])
    intervals=[]
    for part in summary['intervals']:
        selected=[r for r in posts if part['start_s'] <= (int(r['timeStamp'])-origin)/1000 < part['end_s']]
        cohort=[r for r in selected if r['transferId'] in accepted_ids]
        elapsed=sorted(int(r['elapsed']) for r in cohort)
        p95=elapsed[math.ceil(.95*len(elapsed))-1] if elapsed else None
        within=sum(statuses[r['transferId']]['status'] in ('COMPLETED','FAILED') and (datetime.fromisoformat(statuses[r['transferId']]['completedAt'])-datetime.fromisoformat(r['createdAt'])).total_seconds()<=2 for r in cohort)
        assert len(selected)==part['posts'] and len(cohort)==part['accepted'] and p95==part['accepted_post_p95_ms'] and within==part['within_2s']
        intervals.append(dict(start_s=part['start_s'],end_s=part['end_s'],posts=len(selected),accepted=len(cohort),p95_ms=p95,within_2s=within))
    checks.append(dict(run=str(source.relative_to(project/'evidence')),all_posts=len(posts),unique_keys=len(posts),unique_ids=len(accepted),intervals=intervals))
(project/'evidence/independent-recount.json').write_text(json.dumps(checks,indent=2)+'\n')
print('Independent cohort recount:',len(checks),'runs match')
