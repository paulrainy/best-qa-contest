"""Целые количества бизнес-операций: общий источник таблиц и графиков."""
from bisect import bisect_right
from dataclasses import dataclass
from itertools import accumulate
import math
import random

import numpy as np


@dataclass(frozen=True)
class Counts:
    total: int
    other_errors: int = 0
    http503: int = 0
    timeouts: int = 0

    def __post_init__(self):
        if any(type(value) is not int or value < 0 for value in
               (self.total, self.other_errors, self.http503, self.timeouts)) or self.failed > self.total:
            raise ValueError('Нужны целые неотрицательные количества, ошибки не больше общего числа')

    @property
    def failed(self):
        return self.other_errors + self.http503 + self.timeouts

    @property
    def successful(self):
        return self.total - self.failed


def combine(windows) -> Counts:
    rows = list(windows)
    return Counts(*(sum(getattr(row, field) for row in rows)
                    for field in ('total', 'other_errors', 'http503', 'timeouts')))


def split_counts(counts: Counts, weights: list[float], seed: int) -> list[Counts]:
    if not len(weights) or any(not math.isfinite(w) or w < 0 for w in weights):
        raise ValueError('Некорректные веса окон')
    if not counts.total:
        return [Counts(0) for _ in weights]
    if sum(weights) <= 0:
        raise ValueError('Положительное количество требует положительных весов')
    rng = random.Random(seed)
    weight_sum = sum(weights)
    exact = [counts.total * w / weight_sum for w in weights]
    totals = [math.floor(value) for value in exact]
    # Метод наибольших остатков, случайный порядок только для равных остатков.
    order = list(range(len(weights)))
    rng.shuffle(order)
    order.sort(key=lambda i: exact[i] - totals[i], reverse=True)
    for i in order[:counts.total - sum(totals)]:
        totals[i] += 1
    boundaries = list(accumulate(totals))
    errors = [[0, 0, 0] for _ in weights]
    positions = iter(rng.sample(range(counts.total), counts.failed))
    for category, number in enumerate((counts.other_errors, counts.http503, counts.timeouts)):
        for _ in range(number):
            errors[bisect_right(boundaries, next(positions))][category] += 1
    return [Counts(total, *error) for total, error in zip(totals, errors)]


def make_counts(rate, minutes, error_percent, seed, weights=None, http503_percent=0, timeouts=0,
                other_errors=None) -> list[Counts]:
    total = math.floor(rate * minutes / 60 + 0.5)
    errors = math.floor(total * error_percent / 100 + 0.5) if other_errors is None else other_errors
    counts = Counts(total, errors, math.floor(total * http503_percent / 100 + 0.5), timeouts)
    if weights is None:
        rng = random.Random(seed)
        weights = [rng.uniform(0.94, 1.06) for _ in range(round(minutes * 4))]
    return split_counts(counts, list(weights), seed)


def error_values(windows, include503=True, include_timeouts=True):
    return np.array([100 * (row.other_errors + row.http503 * include503 + row.timeouts * include_timeouts)
                     / row.total if row.total else np.nan for row in windows])


def error_summary(windows, include503=True, include_timeouts=True):
    total = combine(windows)
    values = error_values(windows, include503, include_timeouts)
    return (100 * (total.other_errors + total.http503 * include503 + total.timeouts * include_timeouts)
            / total.total if total.total else np.nan,
            float(np.nanmax(values)) if total.total else np.nan)


def throughput(operations):
    return np.array([sum(row.total for row in window) / 15 for window in zip(*operations.values())])
