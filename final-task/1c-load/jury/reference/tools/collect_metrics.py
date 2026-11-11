"""Отдельная временная шкала /metrics и ресурсов генератора, без подстановки нулей."""
import argparse
import csv
import json
import math
from pathlib import Path
import platform
import re
import subprocess
import threading
import time

try:
    from .common import request
except ImportError:
    from common import request

FIELDS = dict(accountingQueue='stand_queue_messages{queue="accounting.transfer-created"}',
              notificationQueue='stand_queue_messages{queue="notifications.transfer-events"}',
              dlqQueue='stand_queue_messages{queue="transfers.dlq"}',
              accountingProcessed='stand_accounting_messages_processed_total',
              finalized='stand_transfer_completion_seconds_count', dbTransfers='stand_db_transfers_rows',
              heapUsed='jvm_memory_heap_used_bytes', heapMax='jvm_memory_heap_max_bytes',
              standCpu='process_cpu_load', standThreads='jvm_threads_live')


def parse_metrics(text):
    raw = {}
    for line in text.splitlines():
        if line and not line.startswith('#'):
            match = re.fullmatch(r'(\S+(?:\{.*\})?)\s+(\S+)', line)
            if match:
                value = float(match.group(2))
                raw[match.group(1)] = value if math.isfinite(value) else None
    values = {field: raw.get(name) for field, name in FIELDS.items()}
    http = [v for k, v in raw.items() if k.startswith('stand_http_requests_total{') and v is not None]
    values['httpRequests'] = sum(http) if http else None
    return values


def generator_stats(parent_pid):
    if not parent_pid:
        return {}
    if platform.system() == 'Windows':
        return dict(generatorError='Windows process collection requires a target pilot')
    try:
        lines = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,comm='], text=True).splitlines()
        children = [line.split(None, 2) for line in lines]
        pid = next((int(p) for p, parent, command in children if int(parent) == parent_pid and command.endswith('/java')), parent_pid)
        result = subprocess.check_output(['ps', '-p', str(pid), '-o', '%cpu=,rss='], text=True, stderr=subprocess.PIPE).split()
        if platform.system() == 'Darwin':
            threads = len(subprocess.check_output(['ps', '-M', '-p', str(pid)], text=True, stderr=subprocess.PIPE).splitlines()) - 1
        else:
            threads = int(subprocess.check_output(['ps', '-p', str(pid), '-o', 'nlwp='], text=True, stderr=subprocess.PIPE))
        return dict(generatorPid=pid, generatorCpuPercent=float(result[0]),
                    generatorRssKiB=int(result[1]), generatorThreads=threads)
    except (OSError, subprocess.SubprocessError, ValueError, IndexError) as exc:
        return dict(generatorError=str(exc))


class MetricsCollector:
    def __init__(self, base, output, *, generator_pid=lambda: None, interval=5):
        self.base, self.output = base, Path(output)
        self.generator_pid, self.interval = generator_pid, interval
        self.stop = threading.Event()
        self.error = None
        self.thread = threading.Thread(target=self._collect, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def close(self):
        self.stop.set()
        self.thread.join(15)
        if self.thread.is_alive():
            raise RuntimeError('Сборщик метрик не завершился')
        if self.error:
            raise RuntimeError('Не удалось сохранить метрики') from self.error

    def _collect(self):
        try:
            fields = ['timestampMs', 'error', *FIELDS, 'httpRequests', 'generatorPid',
                      'generatorCpuPercent', 'generatorRssKiB', 'generatorThreads', 'generatorError']
            with self.output.open('x', newline='', encoding='utf-8') as csv_file, self.output.with_suffix('.jsonl').open('x', encoding='utf-8') as raw_file:
                writer = csv.DictWriter(csv_file, fieldnames=fields)
                writer.writeheader()
                while True:
                    sample = dict(timestampMs=int(time.time() * 1000), error='')
                    text = ''
                    try:
                        text = request(self.base, '/metrics', timeout=5)
                        sample.update(parse_metrics(text))
                        missing = [k for k in FIELDS if sample.get(k) is None]
                        if missing:
                            sample['error'] = 'Отсутствуют метрики: ' + ','.join(missing)
                    except (OSError, ValueError) as exc:
                        sample['error'] = str(exc)
                    sample.update(generator_stats(self.generator_pid()))
                    writer.writerow(sample)
                    csv_file.flush()
                    raw_file.write(json.dumps(dict(**sample, prometheus=text), ensure_ascii=False) + '\n')
                    raw_file.flush()
                    if self.stop.wait(self.interval):
                        break
        except BaseException as exc:
            self.error = exc


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://localhost:18400')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--duration', type=float, default=60)
    args = parser.parse_args()
    collector = MetricsCollector(args.base_url, args.output).start()
    try:
        time.sleep(args.duration)
    finally:
        collector.close()
