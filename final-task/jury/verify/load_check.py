"""Проверка нагрузочных дефектов Н1–Н3 (стенд должен быть запущен, данные будут сброшены).

    python load_check.py [интенсивность, переводов/с] [длительность, с]

По умолчанию 60/с в течение 180 с. Печатает по 15-секундным окнам: принято (202), отклонено «200 REJECTED»,
p95 времени ответа POST, глубину очереди учёта и число строк в transfers.
"""
import json
import re
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import requests

BASE = "http://localhost:18400"


def metric(text, name):
    m = re.search(r"^" + re.escape(name) + r" ([0-9.eE+-]+)$", text, re.M)
    return float(m.group(1)) if m else -1


def main():
    rate = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 180
    requests.post(BASE + "/api/test/reset", timeout=30)
    clients = 2000
    lock = threading.Lock()
    window = {"202": 0, "busy": 0, "other": 0, "lat": []}
    session = requests.Session()

    def one(i):
        src = "40817810" + f"{(i % clients + 1) * 10 + 1:012d}"
        dst = "40817810" + f"{((i + 1) % clients + 1) * 10 + 1:012d}"
        t0 = time.perf_counter()
        r = session.post(BASE + "/api/v1/transfers", data=json.dumps(
            {"fromAccount": src, "toAccount": dst, "amount": 100.00}),
            headers={"Idempotency-Key": str(uuid.uuid4()), "Content-Type": "application/json"}, timeout=60)
        dt = time.perf_counter() - t0
        body = r.json()
        with lock:
            if r.status_code == 202:
                window["202"] += 1
            elif r.status_code == 200 and body.get("status") == "REJECTED":
                window["busy"] += 1
            else:
                window["other"] += 1
            window["lat"].append(dt)

    print(f"{'с':>5} {'202':>6} {'200 REJ':>8} {'прочие':>7} {'p95 POST, мс':>13} {'очередь':>8} {'строк':>7}")
    start = time.time()
    next_report = start + 15
    i = 0
    with ThreadPoolExecutor(64) as pool:
        while time.time() - start < duration:
            target = start + i / rate
            delay = target - time.time()
            if delay > 0:
                time.sleep(delay)
            pool.submit(one, i)
            i += 1
            if time.time() >= next_report:
                next_report += 15
                with lock:
                    lat = sorted(window["lat"])
                    p95 = lat[int(len(lat) * 0.95) - 1] * 1000 if lat else 0
                    snap = dict(window)
                    window.update({"202": 0, "busy": 0, "other": 0, "lat": []})
                m = requests.get(BASE + "/metrics", timeout=10).text
                depth = metric(m, 'stand_queue_messages{queue="accounting.transfer-created"}')
                rows = metric(m, "stand_db_transfers_rows")
                print(f"{int(time.time() - start):>5} {snap['202']:>6} {snap['busy']:>8} {snap['other']:>7} "
                      f"{p95:>13.0f} {depth:>8.0f} {rows:>7.0f}")
    m = requests.get(BASE + "/metrics", timeout=10).text
    buckets = {le: float(v) for le, v in re.findall(r'stand_transfer_completion_seconds_bucket\{le="([^"]+)"\} (\S+)', m)}
    total = buckets.get("+Inf", 0)
    if total:
        print(f"завершено переводов: {total:.0f}; из них не дольше 2 с: {buckets['2.0'] / total:.1%}")


if __name__ == "__main__":
    main()
