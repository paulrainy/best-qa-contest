"""Экспорт PNG из сохранённых измерений; никаких оконных средних p95 в итогах."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt

try:
    from .analyse import classify, percentile, timestamp
    from .common import read_jtl, read_jsonl
except ImportError:
    from analyse import classify, percentile, timestamp
    from common import read_jtl, read_jsonl


def plot(summary_path, metrics_path, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    summary = json.loads(Path(summary_path).read_text(encoding='utf-8'))
    directory = Path(summary_path).parent
    rows = [r for r in read_jtl(directory / 'samples.jtl') if r['label'] == 'POST transfer']
    metrics = read_jtl(metrics_path)
    origin = summary['origin_ms']
    x = [(int(r['timestampMs']) - origin) / 1000 for r in metrics]

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(output / name, dpi=150)
        plt.close(fig)

    def series(field):
        return [float(r[field]) if r.get(field) and not r['error'] else float('nan') for r in metrics]

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    post, accepted, errors = Counter(), Counter(), Counter()
    per_second = defaultdict(list)
    for row in rows:
        second = int((int(row['timeStamp']) - origin) / 1000)
        post[second] += 1
        if classify(row) == 'accepted':
            accepted[second] += 1
            per_second[second].append(int(row['elapsed']))
        else:
            errors[second] += 1
    seconds = list(range(max(post, default=0) + 1))
    for values, label in ((post, 'Новые POST'), (accepted, 'Принятые'), (errors, 'Отказы/ошибки')):
        axes[0].plot(seconds, [values[s] for s in seconds], label=label, alpha=.8)
    for interval in summary['intervals']:
        axes[0].hlines(interval['target_rps'], interval['start_s'], interval['end_s'], color='black', linestyle='--')
        axes[0].axvspan(interval['start_s'], interval['end_s'], color='green', alpha=.04)
    axes[0].set_ylabel('POST/с; окна1с')
    axes[0].legend()
    axes[1].plot(sorted(per_second), [percentile(per_second[s]) for s in sorted(per_second)], label='p95 принятого POST в окне1с')
    axes[1].axhline(500, color='red', linestyle='--', label='Порог500мс')
    axes[1].set(xlabel='Секунды от начала JMeter', ylabel='Время HTTP, мс')
    axes[1].legend()
    fig.suptitle(f"{summary['profile']}: полная когорта p95={summary['measured']['accepted_post_p95_ms']}мс; {summary['nft_verdict']}")
    save(fig, 'arrivals.png')

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    for field, label in (('accountingQueue', 'Учёт'), ('notificationQueue', 'Уведомления'), ('dlqQueue', 'DLQ')):
        axes[0].plot(x, series(field), label=label)
    axes[0].set_ylabel('Сообщений в очереди')
    axes[0].legend()
    rates = summary['metrics']['accounting_rates']
    axes[1].plot([(r['end'] * 1000 - origin) / 1000 for r in rates],
                 [r['rate'] if r['rate'] is not None else float('nan') for r in rates], label='Δ обработанных / Δt')
    axes[1].set(xlabel='Секунды от начала JMeter', ylabel='Сообщений/с')
    axes[1].legend()
    save(fig, 'queues.png')

    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    axes[0].plot(x, [v / 1048576 for v in series('heapUsed')], label='Heap стенда')
    axes[0].plot(x, [float(r['generatorRssKiB']) / 1024 if r.get('generatorRssKiB') else float('nan') for r in metrics], label='RSS генератора')
    axes[0].set_ylabel('МиБ')
    axes[0].legend()
    axes[1].plot(x, [v * 100 for v in series('standCpu')], label='CPU стенда')
    axes[1].plot(x, [float(r['generatorCpuPercent']) if r.get('generatorCpuPercent') else float('nan') for r in metrics], label='CPU генератора (ps или WinAPI)')
    axes[1].set_ylabel('% CPU, разные базы')
    axes[1].legend()
    axes[2].plot(x, series('standThreads'), label='Потоки стенда')
    axes[2].plot(x, [float(r['generatorThreads']) if r.get('generatorThreads') else float('nan') for r in metrics], label='Потоки генератора')
    axes[2].set(xlabel='Секунды от начала JMeter', ylabel='Потоков')
    axes[2].legend()
    save(fig, 'resources.png')

    states = read_jsonl(directory / 'transfers.jsonl')
    fig, axis = plt.subplots(figsize=(11, 5))
    for status, color in (('COMPLETED', 'tab:blue'), ('FAILED', 'tab:red')):
        subset = [r for r in states if r['status'] == status and r.get('completedAt')]
        axis.scatter([(timestamp(r['createdAt']) - origin) / 1000 for r in subset],
                     [timestamp(r['completedAt']) - timestamp(r['createdAt']) for r in subset],
                     s=4, alpha=.5, label=status, color=color)
    axis.axhline(2000, color='red', linestyle='--', label='SLO2с')
    axis.set(xlabel='Создание: секунды от начала JMeter', ylabel='completedAt−createdAt, мс',
             title=f"В срок: {summary['measured']['within_2s_percent']}%; незавершённых: {summary['measured']['unfinished']}; неизвестных: {summary['measured']['unknown_status']}")
    axis.legend()
    save(fig, 'finalization.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('summary', 'metrics', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    plot(args.summary, args.metrics, args.output)
