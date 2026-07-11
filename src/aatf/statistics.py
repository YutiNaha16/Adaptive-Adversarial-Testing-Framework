"""Multi-seed statistical analysis layer."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy import stats

from aatf.metrics import EpisodeRecord


@dataclass(frozen=True)
class MultiSeedResult:
    metric_name: str
    values: list[float]
    mean: float
    std: float
    ci_low: float
    ci_high: float
    ci_level: float = 0.95


def run_multi_seed(
    runner: Callable[[int], list[EpisodeRecord]],
    seeds: list[int],
) -> list[EpisodeRecord]:
    result: list[EpisodeRecord] = []
    for seed in seeds:
        for record in runner(seed):
            result.append(dataclasses.replace(record, seed=seed))
    return result


def bootstrap_ci(
    values: list[float],
    ci_level: float = 0.95,
    n_resamples: int = 1000,
    *,
    rng_seed: int = 0,
) -> tuple[float, float]:
    if not values:
        raise ValueError("values must be non-empty")
    if n_resamples <= 0:
        raise ValueError("n_resamples must be > 0")
    if not (0.0 < ci_level < 1.0):
        raise ValueError("ci_level must be in (0, 1)")
    arr = np.array(values, dtype=float)
    rng = np.random.default_rng(rng_seed)
    indices = rng.integers(0, len(arr), size=(n_resamples, len(arr)))
    means = arr[indices].mean(axis=1)
    lo = (1.0 - ci_level) / 2.0 * 100.0
    hi = (1.0 - lo / 100.0) * 100.0
    return float(np.percentile(means, lo)), float(np.percentile(means, hi))


def significance_test(
    group_a: list[float],
    group_b: list[float],
) -> tuple[float, bool]:
    result = stats.mannwhitneyu(group_a, group_b, alternative="two-sided")
    # nan occurs when all values are tied (no variance in null distribution) → not significant
    p_value = float(np.nan_to_num(result.pvalue, nan=1.0))
    return p_value, bool(p_value < 0.05)


def summarise_metric(
    name: str,
    values: list[float],
    ci_level: float = 0.95,
) -> MultiSeedResult:
    if not values:
        raise ValueError("values must be non-empty")
    ci_low, ci_high = bootstrap_ci(values, ci_level=ci_level)
    return MultiSeedResult(
        metric_name=name,
        values=values,
        mean=float(np.mean(values)),
        std=float(np.std(values, ddof=1)),
        ci_low=ci_low,
        ci_high=ci_high,
        ci_level=ci_level,
    )
