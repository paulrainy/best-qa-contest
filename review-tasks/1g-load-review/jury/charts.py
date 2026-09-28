"""Графики для отчёта НТ из задания 1г.

Рисует participant/img/*.png по тем же числам, что в таблицах отчёта.
Если меняете цифры в отчёте — поменяйте STEPS здесь и перегенерируйте:

    python3 -m venv venv && ./venv/bin/pip install matplotlib
    ./venv/bin/python charts.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "participant" / "img"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 10,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 110,
})

rng = np.random.default_rng(314)

# Ступени теста поиска максимума. Числа совпадают с таблицей 4 отчёта.
# pct, целевая rps, 200 rps, 503 rps, 500 rps, среднее мс, p95 мс,
# CPU приложения, CPU БД, CPU генератора, Hikari active (на под), Hikari pending (всего)
STEPS = [
    (20, 118, 118.0, 0, 0, 146, 415, 11, 7, 12, 3, 0),
    (40, 236, 236.0, 0, 0, 144, 412, 20, 12, 21, 5, 0),
    (60, 355, 354.0, 0, 0, 144, 414, 29, 16, 30, 8, 0),
    (80, 473, 471.0, 0, 0, 146, 418, 37, 21, 39, 11, 0),
    (100, 591, 589.0, 0, 0, 146, 424, 45, 26, 48, 14, 0),
    (120, 709, 650.0, 0, 0, 246, 790, 49, 29, 55, 20, 12),
    (140, 827, 649.9, 0, 0.1, 454, 1390, 50, 30, 63, 20, 90),
    (160, 946, 647.3, 30, 2.7, 588, 2110, 52, 30, 76, 20, 140),
    (180, 1064, 645.1, 164, 4.9, 492, 2040, 53, 31, 91, 20, 140),
    (200, 1182, 641.5, 299, 8.5, 423, 1960, 54, 31, 97, 20, 140),
]

STEP_MIN = 10       # длительность ступени
PAUSE_MIN = 2       # пауза между ступенями
DT_S = 15           # шаг метрик в Grafana
START_H, START_M = 1, 0  # начало теста 01:00


def noisy(value, rel=0.03, n=1):
    return value * (1 + rng.normal(0, rel, n))


def build_series():
    """Временные ряды по всем ступеням; в паузах метрики отсутствуют (NaN)."""
    t, rows = [], []
    minute = 0.0
    for s in STEPS:
        pct, target, ok, e503, e500, avg, p95, cpu_app, cpu_db, cpu_gen, act, pend = s
        n = STEP_MIN * 60 // DT_S
        for i in range(n):
            # разгон 1 с: в первые 30 с ступени — всплеск задержек и провал интенсивности
            burst = i < 2
            k_lat = 3.2 if burst else 1.0
            k_rps = 0.8 if burst else 1.0
            rows.append((
                minute + i * DT_S / 60,
                target,
                noisy(ok * k_rps, 0.015)[0],
                max(0, noisy(e503, 0.08)[0]) if e503 else 0,
                max(0, noisy(e500, 0.3)[0]) if e500 else 0,
                noisy(avg * k_lat, 0.04)[0],
                noisy(p95 * k_lat, 0.05)[0],
                min(100, noisy(cpu_app * (1.3 if burst else 1), 0.04)[0]),
                min(100, noisy(cpu_db, 0.05)[0]),
                min(100, noisy(cpu_gen * (1.2 if burst else 1), 0.02)[0]),
                min(20, noisy(act, 0.05)[0]) if act < 20 else 20,
                max(0, noisy(pend, 0.1)[0]) if pend else 0,
            ))
        minute += STEP_MIN
        rows.append((minute + 0.01, *[np.nan] * 11))  # разрыв линии на паузе
        minute += PAUSE_MIN
    arr = np.array(rows, dtype=float)
    return arr


def clock_ticks(ax, total_min):
    ticks = np.arange(0, total_min + 1, 12)
    ax.set_xticks(ticks)
    labels = []
    for m in ticks:
        h, mm = divmod(int(START_H * 60 + START_M + m), 60)
        labels.append(f"{h:02d}:{mm:02d}")
    ax.set_xticklabels(labels)
    ax.set_xlim(0, total_min)


def step_labels(ax):
    ymax = ax.get_ylim()[1]
    for idx, s in enumerate(STEPS):
        x0 = idx * (STEP_MIN + PAUSE_MIN)
        ax.axvspan(x0, x0 + STEP_MIN, color="0.5", alpha=0.05, lw=0)
        ax.text(x0 + STEP_MIN / 2, ymax * 0.98, f"{s[0]}%", ha="center", va="top",
                fontsize=8, color="0.35")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name)
    plt.close(fig)


def main():
    a = build_series()
    t = a[:, 0]
    total = len(STEPS) * (STEP_MIN + PAUSE_MIN) - PAUSE_MIN

    # Рисунок 1. Интенсивность
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.step(t, a[:, 1], where="post", color="0.2", ls="--", lw=1.2, label="Целевая интенсивность")
    ax.plot(t, a[:, 2] + a[:, 3] + a[:, 4], color="#1f77b4", lw=1.3, label="Все ответы")
    ax.set_ylabel("запросов в секунду")
    ax.set_ylim(0, 1300)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4, frameon=False)
    ax.set_title("Рисунок 1. Интенсивность запросов (JMeter)", loc="left", fontsize=11)
    clock_ticks(ax, total)
    step_labels(ax)
    save(fig, "fig1-throughput.png")

    # Рисунок 2. Ответы по кодам
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t, a[:, 2], color="#2ca02c", lw=1.3, label="200")
    ax.plot(t, a[:, 3], color="#ff7f0e", lw=1.3, label="503")
    ax.plot(t, a[:, 4], color="#d62728", lw=1.3, label="500")
    ax.set_ylabel("ответов в секунду")
    ax.set_ylim(0, 800)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4, frameon=False, title="Код ответа", title_fontsize=9)
    ax.set_title("Рисунок 2. Ответы по кодам (JMeter)", loc="left", fontsize=11)
    clock_ticks(ax, total)
    step_labels(ax)
    save(fig, "fig2-response-codes.png")

    # Рисунок 3. Время отклика
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t, a[:, 5], color="#1f77b4", lw=1.3, label="Среднее")
    ax.plot(t, a[:, 6], color="#9467bd", lw=1.3, label="95-й перцентиль")
    ax.axhline(500, color="#d62728", ls=":", lw=1, label="500 мс")
    ax.set_ylabel("мс")
    ax.set_ylim(0, 3000)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4, frameon=False)
    ax.set_title("Рисунок 3. Время отклика, все запросы (JMeter)", loc="left", fontsize=11)
    clock_ticks(ax, total)
    step_labels(ax)
    save(fig, "fig3-response-time.png")

    # Рисунок 4. CPU
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t, a[:, 7], color="#1f77b4", lw=1.3, label="cards-api, среднее по подам")
    ax.plot(t, a[:, 8], color="#8c564b", lw=1.3, label="PostgreSQL")
    ax.plot(t, a[:, 9], color="#7f7f7f", lw=1.3, label="Генератор нагрузки (ВМ JMeter)")
    ax.set_ylabel("CPU, %")
    ax.set_ylim(0, 110)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4, frameon=False)
    ax.set_title("Рисунок 4. Загрузка CPU (Prometheus)", loc="left", fontsize=11)
    clock_ticks(ax, total)
    step_labels(ax)
    save(fig, "fig4-cpu.png")

    # Рисунок 5. Пул соединений к БД
    fig, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(t, a[:, 10], color="#1f77b4", lw=1.3, label="Активные соединения, среднее на под")
    ax1.axhline(20, color="#1f77b4", ls=":", lw=1, label="maximumPoolSize = 20")
    ax1.set_ylabel("соединений на под")
    ax1.set_ylim(0, 26)
    ax2 = ax1.twinx()
    ax2.plot(t, a[:, 11], color="#ff7f0e", lw=1.3, label="Ожидают соединения, всего по подам")
    ax2.set_ylabel("потоков в ожидании")
    ax2.set_ylim(0, 200)
    ax2.spines["right"].set_visible(True)
    ax2.grid(False)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False, fontsize=9)
    ax1.set_title("Рисунок 5. Пул соединений к БД, HikariCP (Prometheus)", loc="left", fontsize=11)
    clock_ticks(ax1, total)
    step_labels(ax1)
    save(fig, "fig5-db-pool.png")

    # Рисунок 6. Тест стабильности: heap и время отклика, 60 минут
    dt = 5
    ts = np.arange(0, 60 * 60 + 1, dt) / 60  # минуты
    base = 1.1 + 1.5 * ts / 60                 # занятый heap после сборки, ГБ
    saw = (ts * 60 % 22) / 22 * 0.9            # малые сборки примерно раз в 22 с
    heap = base + saw + rng.normal(0, 0.02, ts.size)
    p95 = 424 * (1 + rng.normal(0, 0.04, ts.size))

    fig, (h_ax, r_ax) = plt.subplots(2, 1, figsize=(10, 5.4), sharex=True)
    h_ax.plot(ts, heap, color="#1f77b4", lw=0.8, label="Занятый heap, среднее по подам")
    h_ax.axhline(4.0, color="#d62728", ls=":", lw=1, label="-Xmx = 4 ГБ")
    h_ax.set_ylim(0, 4.5)
    h_ax.set_ylabel("ГБ")
    h_ax.legend(loc="upper left", frameon=False)
    h_ax.set_title("Рисунок 6. Тест стабильности, 100% профиля: JVM heap (Prometheus)", loc="left",
                   fontsize=11)
    r_ax.plot(ts, p95, color="#9467bd", lw=1, label="95-й перцентиль")
    r_ax.set_ylim(0, 800)
    r_ax.set_ylabel("мс")
    r_ax.legend(loc="upper left", frameon=False)
    r_ax.set_title("Время отклика (JMeter)", loc="left", fontsize=11)
    ticks = np.arange(0, 61, 10)
    r_ax.set_xticks(ticks)
    r_ax.set_xticklabels([f"03:{15 + m:02d}" if 15 + m < 60 else f"04:{15 + m - 60:02d}" for m in ticks])
    r_ax.set_xlim(0, 60)
    save(fig, "fig6-stability.png")


if __name__ == "__main__":
    main()
