"""Tests for aatf.statistics — F21 statistical rigor layer. Contracts C-001..C-020."""

from __future__ import annotations

import dataclasses

import pytest

from aatf.episode import StepRecord
from aatf.metrics import EpisodeRecord
from aatf.statistics import (
    MultiSeedResult,
    bootstrap_ci,
    run_multi_seed,
    significance_test,
    summarise_metric,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _step(detected: bool = False) -> StepRecord:
    return StepRecord(action_id="noop", detected=detected, stage_progress=False, reward=0.0)


def _ep(episode_index: int, *, seed: int = 0) -> EpisodeRecord:
    return EpisodeRecord(
        attacker_class="MockAttacker",
        seed=seed,
        steps=[_step()],
        total_reward=0.0,
        completed=True,
        episode_index=episode_index,
    )


# ---------------------------------------------------------------------------
# US1 — MultiSeedResult Container
# ---------------------------------------------------------------------------


def test_c001_construction_fields():
    """C-001: All fields accessible after construction."""
    rec = MultiSeedResult(
        metric_name="detection_rate",
        values=[0.8, 0.7, 0.75],
        mean=0.75,
        std=0.05,
        ci_low=0.65,
        ci_high=0.85,
    )
    assert rec.metric_name == "detection_rate"
    assert rec.values == [0.8, 0.7, 0.75]
    assert rec.mean == 0.75
    assert rec.std == 0.05
    assert rec.ci_low == 0.65
    assert rec.ci_high == 0.85


def test_c002_default_ci_level():
    """C-002: ci_level defaults to 0.95 when not specified."""
    rec = MultiSeedResult(metric_name="x", values=[0.5], mean=0.5, std=0.0, ci_low=0.5, ci_high=0.5)
    assert rec.ci_level == 0.95


def test_c003_frozen_raises_on_set():
    """C-003: Frozen dataclass — assignment raises FrozenInstanceError or AttributeError."""
    rec = MultiSeedResult(metric_name="x", values=[0.5], mean=0.5, std=0.0, ci_low=0.5, ci_high=0.5)
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        rec.mean = 99.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# US2 — run_multi_seed
# ---------------------------------------------------------------------------


def test_c004_runner_called_n_times():
    """C-004: Runner invoked exactly once per seed."""
    calls: list[int] = []

    def runner(seed: int) -> list[EpisodeRecord]:
        calls.append(seed)
        return [_ep(0, seed=seed)]

    run_multi_seed(runner, [10, 20, 30, 40, 50])
    assert calls == [10, 20, 30, 40, 50]


def test_c005_total_record_count():
    """C-005: Total records = N seeds × per-call count."""

    def runner(seed: int) -> list[EpisodeRecord]:
        return [_ep(i, seed=seed) for i in range(3)]

    result = run_multi_seed(runner, [0, 1, 2, 3, 4])
    assert len(result) == 15


def test_c006_records_tagged_with_seed():
    """C-006: Each record's seed field equals the seed used for that call."""

    def runner(seed: int) -> list[EpisodeRecord]:
        return [_ep(i, seed=0) for i in range(2)]  # seed=0 placeholder

    result = run_multi_seed(runner, [42, 99])
    assert result[0].seed == 42
    assert result[1].seed == 42
    assert result[2].seed == 99
    assert result[3].seed == 99


def test_c007_empty_seeds_returns_empty_list():
    """C-007: Empty seeds list → empty result, no error."""
    result = run_multi_seed(lambda s: [_ep(0)], [])
    assert result == []


# ---------------------------------------------------------------------------
# US3 — bootstrap_ci
# ---------------------------------------------------------------------------


def test_c008_identical_values_zero_width_ci():
    """C-008: All values identical → ci_low == ci_high == that value."""
    lo, hi = bootstrap_ci([0.5, 0.5, 0.5], rng_seed=0)
    assert lo == 0.5
    assert hi == 0.5


def test_c009_determinism():
    """C-009: Same inputs + rng_seed → identical output on repeated calls."""
    result_a = bootstrap_ci([0.1, 0.5, 0.9], rng_seed=0)
    result_b = bootstrap_ci([0.1, 0.5, 0.9], rng_seed=0)
    assert result_a == result_b


def test_c010_ci_brackets_mean():
    """C-010: For non-trivial values, ci_low < mean < ci_high."""
    values = [0.1, 0.3, 0.5, 0.7, 0.9]
    lo, hi = bootstrap_ci(values, ci_level=0.95, rng_seed=0)
    assert lo < 0.5 < hi


def test_c011_empty_values_raises_value_error():
    """C-011: Empty values list → ValueError."""
    with pytest.raises(ValueError):
        bootstrap_ci([])


def test_c012_n_resamples_zero_raises_value_error():
    """C-012: n_resamples=0 → ValueError."""
    with pytest.raises(ValueError):
        bootstrap_ci([0.5], n_resamples=0)


def test_c013_ci_level_out_of_range_raises_value_error():
    """C-013: ci_level outside (0, 1) exclusive → ValueError."""
    with pytest.raises(ValueError):
        bootstrap_ci([0.5], ci_level=0.0)
    with pytest.raises(ValueError):
        bootstrap_ci([0.5], ci_level=1.0)
    with pytest.raises(ValueError):
        bootstrap_ci([0.5], ci_level=1.5)


# ---------------------------------------------------------------------------
# US4 — significance_test
# ---------------------------------------------------------------------------


def test_c014_clearly_different_groups_significant():
    """C-014: All-high vs all-low (n=5) → is_significant=True, p<0.05."""
    # Analytic: U=25 (max, n1=n2=5), p=2/C(10,5)=2/252≈0.0079
    p, sig = significance_test(
        [0.9, 0.85, 0.88, 0.92, 0.87],
        [0.1, 0.12, 0.09, 0.11, 0.08],
    )
    assert sig is True
    assert p < 0.05


def test_c015_identical_groups_not_significant():
    """C-015: Identical groups → is_significant=False, p≥0.05."""
    p, sig = significance_test([0.5] * 5, [0.5] * 5)
    assert sig is False
    assert p >= 0.05


def test_c016_return_type_float_bool():
    """C-016: Return type is (float, bool)."""
    result = significance_test([0.5, 0.6], [0.4, 0.3])
    assert isinstance(result, tuple) and len(result) == 2
    assert isinstance(result[0], float)
    assert isinstance(result[1], bool)


def test_c017_two_sided_symmetry():
    """C-017: Swapping groups gives identical p-value (two-sided test)."""
    a = [0.9, 0.85, 0.88, 0.92, 0.87]
    b = [0.1, 0.12, 0.09, 0.11, 0.08]
    p_ab, _ = significance_test(a, b)
    p_ba, _ = significance_test(b, a)
    assert abs(p_ab - p_ba) < 1e-12


# ---------------------------------------------------------------------------
# US5 — summarise_metric
# ---------------------------------------------------------------------------


def test_c018_correct_mean_and_std():
    """C-018: mean=0.75, std=0.05 (ddof=1) for values=[0.8, 0.7, 0.75]."""
    result = summarise_metric("dr", [0.8, 0.7, 0.75])
    assert result.metric_name == "dr"
    assert abs(result.mean - 0.75) < 1e-9
    assert abs(result.std - 0.05) < 1e-9


def test_c019_identical_values_zero_width_ci():
    """C-019: Identical values → std=0, ci_low==ci_high==mean."""
    result = summarise_metric("x", [0.5, 0.5, 0.5])
    assert result.std == 0.0
    assert result.ci_low == 0.5
    assert result.ci_high == 0.5
    assert result.mean == 0.5


def test_c020_empty_values_raises_value_error():
    """C-020: Empty values → ValueError."""
    with pytest.raises(ValueError):
        summarise_metric("x", [])
