"""Графики протоколов 1г в стиле Grafana и Zabbix.

Запуск из папки tools:
    .venv/bin/python ../1g-load-review/jury/source/protocols/charts.py 11 12   — нарисовать графики протоколов
    .venv/bin/python ../1g-load-review/jury/source/protocols/charts.py --tables 11 — таблицы средних в Markdown

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
        'font.family': 'Arial', 'font.size': 9, 'axes.facecolor': 'white', 'figure.facecolor': 'white',
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


def fmt(value: float, unit: str) -> str:
    if np.isnan(value):
        return '—'
    if unit == 'ГБ':
        return f'{value:.2f} {unit}'.replace('.', ',')
    if abs(value) >= 100 or float(value).is_integer():
        return f'{value:,.0f} {unit}'.replace(',', ' ').strip()
    return f'{value:.1f} {unit}'.replace('.', ',').strip()


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
            ax.text(t[0], threshold, f' {threshold_label}', color='#F2495C', va='bottom', fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.set_xlim(t[0], t[-1])
    if ylim:
        ax.set_ylim(*ylim)
    else:
        ax.set_ylim(bottom=0)
    ax.set_ylabel(unit)
    ax.margins(x=0)
    return used


def legend_table(ax, series: dict, colors, unit: str):
    """Легенда как в Grafana: имя ряда, среднее и максимум."""
    ax.axis('off')
    rows = [['', 'Сред.', 'Макс.']]
    for name, values in series.items():
        values = np.asarray(values, dtype=float)
        rows.append([f'— {name}', fmt(np.nanmean(values), unit), fmt(np.nanmax(values), unit)])
    table = ax.table(cellText=rows, bbox=[0, 0, 1, 1], cellLoc='left', colWidths=[0.66, 0.17, 0.17], edges='open')
    table.auto_set_font_size(False)
    table.set_fontsize(8)
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
          colors=None, source='Grafana'):
    """Один график-панель с заголовком, линиями и легендой-таблицей. Сохраняет PNG."""
    style()
    legend_rows = len(series) + 1
    fig = plt.figure(figsize=(10, 3.4 + 0.2 * legend_rows))
    grid = fig.add_gridspec(2, 1, height_ratios=[3.4, 0.2 * legend_rows + 0.1], hspace=0.25)
    ax = fig.add_subplot(grid[0])
    used = timeseries(ax, t, series, unit, threshold, threshold_label, ylim, colors)
    fig.text(0.01, 0.985, title, ha='left', va='top', fontsize=10, weight='bold', color=TEXT)
    fig.text(0.99, 0.985, source, ha='right', va='top', fontsize=8, color='#8E8E8E')
    legend_table(fig.add_subplot(grid[1]), series, used, unit)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.04)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def load(unit: str):
    sys.path.insert(0, str(HERE))
    return importlib.import_module(f'data_{unit}')


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or '--help' in args:
        sys.exit(__doc__)
    if args[0] == '--tables':
        for unit in args[1:]:
            print(load(unit).tables())
    else:
        for unit in args:
            for name in load(unit).draw(IMG):
                print(name)
