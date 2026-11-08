"""Графики протоколов 1c в стиле Grafana и Zabbix.

Запуск из папки tools:
    .venv/bin/python ../1c-load-review/jury/source/protocols/charts.py 11 12   — нарисовать графики протоколов
    .venv/bin/python ../1c-load-review/jury/source/protocols/charts.py --tables 11 — таблицы средних в Markdown
    .venv/bin/python ../1c-load-review/jury/source/protocols/charts.py --check 11 12 — таблицы в NN-*.md совпадают с --tables

Числа каждого протокола задаёт его модуль data_NN.py рядом: константы ступеней или интервалов и функция
series(), которая строит ряды по формулам с шумом и фиксированным seed. Таблицы протокола берутся из --tables,
поэтому числа в тексте и на графиках одни и те же.
"""
import importlib
import sys
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
IMG = HERE / 'img'
COLORS = ['#56A64B', '#E0A400', '#8AB8FF', '#FF780A', '#F2495C', '#5794F2', '#B877D9', '#705DA0', '#37872D',
          '#FADE2A']
GRID, TEXT, FRAME = '#E4E4E4', '#464C54', '#D0D0D0'


def style():
    plt.rcParams.update({
        'font.family': 'Arial', 'font.size': 10, 'axes.facecolor': 'white', 'figure.facecolor': 'white',
        'axes.edgecolor': FRAME, 'axes.labelcolor': TEXT, 'xtick.color': TEXT, 'ytick.color': TEXT,
        'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.8, 'axes.spines.top': False,
        'axes.spines.right': False, 'figure.dpi': 120, 'savefig.dpi': 120,
    })


def minutes(start: str, values) -> list:
    """Минуты от начала → время. start — «ГГГГ-ММ-ДД ЧЧ:ММ» по МСК."""
    base = datetime.strptime(start, '%Y-%m-%d %H:%M')
    return [base + timedelta(minutes=float(m)) for m in values]


def noisy(rng, value, rel=0.03, size=None):
    return np.asarray(value) * (1 + rng.normal(0, rel, size))


# Доля сервера в среднем по группе: серверы нагружены неодинаково. У эталона распределение чуть другое.
SERVER_FACTORS = {'app': [0.97, 0.99, 1.01, 1.03], 'int': [0.98, 1.02]}
BASELINE_FACTORS = {'app': [0.975, 0.985, 1.015, 1.025], 'int': [0.985, 1.015]}


def smooth(values, window):
    """Скользящее среднее: память ОС меняется медленно, а не скачет от окна к окну."""
    return np.convolve(values, np.ones(window) / window, mode='same')


def util_series(rows, size, seed, column=1, maximum_column=None):
    """Процентные ряды с заданным средним из таблицы, без выхода за 0–100 %.

    seed у каждого протокола свой: одинаковые кривые в двух протоколах выглядят как график другого запуска.
    """
    rng = np.random.default_rng(seed)
    result = {}
    for row in rows:
        mean = row[column]
        memory = row[0].startswith('Память')
        noise = rng.normal(size=size)
        if memory:
            noise = smooth(noise, 40)
        noise -= noise.mean()
        if maximum_column is not None:  # максимум задан таблицей протокола
            scale = min((row[maximum_column] - mean) / noise.max(), mean / -noise.min())
        else:  # разброс у каждого ряда свой: одинаковый «максимум = среднее × 1,08» выдаёт генератор
            spread = rng.uniform(0.25, 0.45) if memory else mean * rng.uniform(0.022, 0.034)
            scale = spread / noise.std()
        result[row[0]] = np.clip(mean + noise * scale, 0, 100)
    return result


def _server_metrics(metrics, factors=None, seed=None):
    """Разрез по серверам с сохранением среднего приложений и адаптера.

    Для рядов (seed задан) у каждого сервера свой шум с нулевым средним: среднее сервера остаётся
    равным его доле от среднего по группе, а кривые серверов не повторяют друг друга.
    """
    factors = factors or SERVER_FACTORS
    rng = np.random.default_rng(seed) if seed is not None else None
    cpu, memory = {}, {}

    def server(level, factor, kind):
        if rng is None:
            return level * factor
        level = np.asarray(level, dtype=float)
        seen = np.isfinite(level)
        noise = rng.normal(size=level.size)
        if kind == 'Память':
            noise = smooth(noise, 40) * 4
        noise = np.where(seen, level, 0.0) * noise * (0.004 if kind == 'Память' else 0.025)
        noise[seen] -= noise[seen].mean()
        return np.clip(level * factor + noise, 0, 100)

    for kind, destination in [('CPU', cpu), ('Память', memory)]:
        app = metrics[f'{kind} efr-api, среднее по 4 серверам, %']
        adapter = metrics[f'{kind} efr-cft-adapter, %']
        for n, factor in enumerate(factors['app'], 1):
            destination[f'efr-nt-app{n:02d}'] = server(app, factor, kind)
        for n, factor in enumerate(factors['int'], 1):
            destination[f'efr-nt-int{n:02d}'] = server(adapter, factor, kind)
        destination['efr-nt-db01'] = metrics[f'{kind} БД, %']
        for n in [1, 2]:
            destination[f'efr-nt-gen{n:02d}'] = metrics[f'{kind} efr-nt-gen{n:02d}, %']
    return cpu, memory


def decimal(value, digits=1):
    return f'{value:.{digits}f}'.replace('.', ',').replace('-', '−')


def server_comparison(rows):
    """Средние CPU и памяти каждого сервера для сравнения по п. 4.4. Изменение считается из чисел строки."""
    baseline = _server_metrics({row[0]: row[1] for row in rows}, BASELINE_FACTORS)
    current = _server_metrics({row[0]: row[2] for row in rows})
    result = []
    for metric, old, new in zip(['CPU', 'Память ОС'], baseline, current):
        for host in old:
            before, after = round(old[host], 1), round(new[host], 1)
            result.append([host, metric, decimal(before), decimal(after), decimal((after / before - 1) * 100)])
    return result


def server_panels(img, unit, when, metrics, first):
    """CPU, память ОС, диск БД и heap генераторов; агрегаты совпадают с таблицами."""
    cpu, memory = _server_metrics(metrics, seed=2600 + int(unit))
    plots = [
        ('server-cpu', 'CPU серверов', cpu),
        ('memory', 'Память ОС серверов', memory),
        ('disk', 'Утилизация диска БД', {'efr-nt-db01': metrics['Диск БД, утилизация %']}),
        ('generator-heap', 'Heap JMeter, % от 6 ГБ', {
            'Генераторы': metrics['Heap JMeter на генераторах, % от 6 ГБ']}),
    ]
    files = []
    for offset, (suffix, title, values) in enumerate(plots):
        name = f'{unit}-{suffix}.png'
        threshold = 80 if suffix == 'generator-heap' else None
        panel(img / name, f'Рисунок {first + offset}. {title}', when, values, '%', threshold,
              'порог heap 80 %' if threshold else None, (0, 100), source='Grafana · Zabbix / JVM')
        files.append(name)
    return files


def fmt(value: float, unit: str) -> str:
    if np.isnan(value):
        return '—'
    if unit == 'ГБ':
        return f'{value:.2f} {unit}'.replace('.', ',')
    if unit == '%' and 0 < abs(value) < 1:
        return f'{value:.2f} {unit}'.replace('.', ',')  # доли ошибок: 0,05 %, как в таблицах протокола
    if abs(value) >= 100 or value == 0:
        return f'{value:,.0f} {unit}'.replace(',', ' ').strip()
    return f'{value:.1f} {unit}'.replace('.', ',').strip()  # один формат в легенде: 31,0 % рядом с 39,8 %


def timeseries(ax, t, series: dict, unit: str, threshold=None, threshold_label=None, ylim=None, colors=None):
    """Линии рядов и линия порога. Возвращает цвета рядов для легенды."""
    used = []
    for n, (name, values) in enumerate(series.items()):
        color = (colors or COLORS)[n % len(colors or COLORS)]
        ax.plot(t, values, color=color, lw=1.2)
        used.append(color)
    if threshold is not None:
        ax.axhline(threshold, color='#F2495C', ls='--', lw=1)
        if threshold_label:
            ax.text(t[0], threshold, f' {threshold_label}', color='#F2495C', va='bottom', fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.set_xlim(t[0], t[-1])
    if ylim:
        ax.set_ylim(*ylim)
    else:
        ax.set_ylim(bottom=0)
    ax.set_ylabel(unit)
    ax.margins(x=0)
    return used


def legend_table(ax, series: dict, colors, unit: str, summarize=True, summary_values=None):
    """Для оконных перцентилей — только имена рядов, без агрегирования за интервал."""
    ax.axis('off')
    rows = [['', 'За интервал' if summary_values is not None else 'Сред.', 'Макс.']] if summarize else [['']]
    for name, values in series.items():
        row = [f'— {name}']
        if summarize:
            values = np.asarray(values, dtype=float)
            mean, maximum = summary_values[name] if summary_values is not None else (np.nanmean(values), np.nanmax(values))
            row += [fmt(mean, unit), fmt(maximum, unit)]
        rows.append(row)
    widths = [0.66, 0.17, 0.17] if summarize else [1.0]
    table = ax.table(cellText=rows, bbox=[0, 0, 1, 1], cellLoc='left', colWidths=widths, edges='open')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for (r, c), cell in table.get_celld().items():
        cell.PAD = 0.01
        if r == 0:
            cell.get_text().set_color(TEXT)
            cell.get_text().set_weight('bold')
        elif c == 0:
            cell.get_text().set_color(colors[r - 1])
        else:
            cell.get_text().set_color(TEXT)


def panel(path: Path, title: str, t, series: dict, unit: str, threshold=None, threshold_label=None, ylim=None,
          colors=None, source='Grafana', summarize=True, summary_values=None):
    """Один график-панель с заголовком, линиями и легендой-таблицей. Сохраняет PNG."""
    style()
    legend_rows = len(series) + 1
    fig = plt.figure(figsize=(10, 3.4 + 0.24 * legend_rows))
    grid = fig.add_gridspec(2, 1, height_ratios=[3.4, 0.24 * legend_rows + 0.1], hspace=0.25)
    ax = fig.add_subplot(grid[0])
    used = timeseries(ax, t, series, unit, threshold, threshold_label, ylim, colors)
    fig.text(0.01, 0.985, title, ha='left', va='top', fontsize=11, weight='bold', color=TEXT)
    fig.text(0.99, 0.985, source, ha='right', va='top', fontsize=9, color='#8E8E8E')
    legend_table(fig.add_subplot(grid[1]), series, used, unit, summarize=summarize, summary_values=summary_values)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.04)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def load(unit: str):
    sys.path.insert(0, str(HERE))
    return importlib.import_module(f'data_{unit}')


def check(unit: str) -> list:
    """Таблицы из data_NN.tables(), которых нет в исходнике протокола слово в слово."""
    source = next(HERE.glob(f'{unit}-*.md')).read_text(encoding='utf-8')
    return [chunk.splitlines()[0] for chunk in load(unit).tables().split('\n\n') if chunk not in source]


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or '--help' in args:
        sys.exit(__doc__)
    if args[0] == '--check':
        problems = {unit: check(unit) for unit in args[1:]}
        for unit, missing in problems.items():
            print(f'{unit}: ' + ('таблицы совпадают' if not missing else 'не совпадают: ' + '; '.join(missing)))
        sys.exit(1 if any(problems.values()) else 0)
    if args[0] == '--tables':
        for unit in args[1:]:
            print(load(unit).tables())
    else:
        for unit in args:
            for name in load(unit).draw(IMG):
                print(name)
