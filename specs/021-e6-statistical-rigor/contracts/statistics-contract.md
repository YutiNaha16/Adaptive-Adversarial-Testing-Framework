# Contracts: Statistical Rigor Layer (F21)

**Feature**: 021-e6-statistical-rigor  
**Date**: 2026-07-11  
**Module**: `aatf.statistics`

Contracts are organised by user story. Each contract maps to a pytest test ID. All analytic ground truths were verified by hand in `research.md`.

---

## US1 — MultiSeedResult Container

### C-001: Construction with all fields explicit

**Given** a `MultiSeedResult` is constructed with:
- `metric_name="detection_rate"`, `values=[0.8, 0.7, 0.75]`, `mean=0.75`, `std=0.05`, `ci_low=0.65`, `ci_high=0.85`

**When** all fields are accessed

**Then** each field equals the value provided at construction.

```python
rec = MultiSeedResult(
    metric_name="detection_rate",
    values=[0.8, 0.7, 0.75],
    mean=0.75, std=0.05, ci_low=0.65, ci_high=0.85,
)
assert rec.metric_name == "detection_rate"
assert rec.values == [0.8, 0.7, 0.75]
assert rec.mean == 0.75
assert rec.std == 0.05
assert rec.ci_low == 0.65
assert rec.ci_high == 0.85
```

### C-002: Default ci_level is 0.95

**Given** a `MultiSeedResult` is constructed without specifying `ci_level`

**When** `ci_level` is accessed

**Then** it equals `0.95`.

```python
rec = MultiSeedResult(
    metric_name="x", values=[0.5], mean=0.5, std=0.0, ci_low=0.5, ci_high=0.5,
)
assert rec.ci_level == 0.95
```

### C-003: Frozen — attribute assignment raises FrozenInstanceError

**Given** a `MultiSeedResult` instance

**When** an attempt is made to set `rec.mean = 99.0`

**Then** a `dataclasses.FrozenInstanceError` (or `AttributeError`) is raised.

```python
import pytest
rec = MultiSeedResult(
    metric_name="x", values=[0.5], mean=0.5, std=0.0, ci_low=0.5, ci_high=0.5,
)
with pytest.raises((FrozenInstanceError, AttributeError)):
    rec.mean = 99.0
```

---

## US2 — run_multi_seed

**Helper**:

```python
def _ep(episode_index: int, *, seed: int = 0) -> EpisodeRecord:
    from aatf.episode import StepRecord
    return EpisodeRecord(
        attacker_class="MockAttacker",
        seed=seed,
        steps=[StepRecord(action_id="noop", detected=False, stage_progress=False, reward=0.0)],
        total_reward=0.0,
        completed=True,
        episode_index=episode_index,
    )
```

### C-004: Runner called exactly N times

**Given** `seeds = [10, 20, 30, 40, 50]` and a mock runner that appends the seed to a call list

**When** `run_multi_seed(runner, seeds)` is called

**Then** the call list equals `[10, 20, 30, 40, 50]`.

```python
calls = []
def runner(seed: int) -> list[EpisodeRecord]:
    calls.append(seed)
    return [_ep(0, seed=seed)]

run_multi_seed(runner, [10, 20, 30, 40, 50])
assert calls == [10, 20, 30, 40, 50]
```

### C-005: Total record count = N × per-call count

**Given** a runner that returns exactly 3 records per call, and 5 seeds

**When** `run_multi_seed(runner, seeds)` is called

**Then** the result contains exactly 15 records.

```python
def runner(seed: int) -> list[EpisodeRecord]:
    return [_ep(i, seed=seed) for i in range(3)]

result = run_multi_seed(runner, [0, 1, 2, 3, 4])
assert len(result) == 15
```

### C-006: Each record tagged with its seed

**Given** a runner and seeds `[42, 99]`

**When** `run_multi_seed(runner, [42, 99])` is called and the runner returns 2 records per call

**Then** the first 2 records have `seed=42` and the next 2 have `seed=99`.

```python
def runner(seed: int) -> list[EpisodeRecord]:
    return [_ep(i, seed=0) for i in range(2)]  # seed=0 placeholder

result = run_multi_seed(runner, [42, 99])
assert result[0].seed == 42
assert result[1].seed == 42
assert result[2].seed == 99
assert result[3].seed == 99
```

### C-007: Empty seeds → empty list

**Given** `seeds = []`

**When** `run_multi_seed(runner, [])` is called

**Then** the result is `[]` with no error.

```python
result = run_multi_seed(lambda s: [_ep(0)], [])
assert result == []
```

---

## US3 — bootstrap_ci

### C-008: Identical values → zero-width CI

**Given** `values = [0.5, 0.5, 0.5]` and any `rng_seed`

**When** `bootstrap_ci(values, rng_seed=0)` is called

**Then** `ci_low == ci_high == 0.5`.

```python
lo, hi = bootstrap_ci([0.5, 0.5, 0.5], rng_seed=0)
assert lo == 0.5
assert hi == 0.5
```

### C-009: Determinism — same inputs same output

**Given** `values = [0.1, 0.5, 0.9]` and `rng_seed=0`

**When** `bootstrap_ci` is called twice with identical arguments

**Then** both calls return identical `(ci_low, ci_high)`.

```python
result_a = bootstrap_ci([0.1, 0.5, 0.9], rng_seed=0)
result_b = bootstrap_ci([0.1, 0.5, 0.9], rng_seed=0)
assert result_a == result_b
```

### C-010: CI brackets the mean for non-trivial values

**Given** `values = [0.1, 0.3, 0.5, 0.7, 0.9]` (mean=0.5)

**When** `bootstrap_ci(values, ci_level=0.95, rng_seed=0)` is called

**Then** `ci_low < 0.5 < ci_high`.

```python
lo, hi = bootstrap_ci([0.1, 0.3, 0.5, 0.7, 0.9], ci_level=0.95, rng_seed=0)
assert lo < 0.5 < hi
```

### C-011: Empty values → ValueError

**Given** `values = []`

**When** `bootstrap_ci([])` is called

**Then** `ValueError` is raised.

```python
with pytest.raises(ValueError):
    bootstrap_ci([])
```

### C-012: n_resamples=0 → ValueError

**Given** `n_resamples=0`

**When** `bootstrap_ci([0.5], n_resamples=0)` is called

**Then** `ValueError` is raised.

```python
with pytest.raises(ValueError):
    bootstrap_ci([0.5], n_resamples=0)
```

### C-013: ci_level outside (0, 1) → ValueError

**Given** `ci_level=1.0` (boundary, invalid)

**When** `bootstrap_ci([0.5], ci_level=1.0)` is called

**Then** `ValueError` is raised.

```python
with pytest.raises(ValueError):
    bootstrap_ci([0.5], ci_level=1.0)
with pytest.raises(ValueError):
    bootstrap_ci([0.5], ci_level=0.0)
```

---

## US4 — significance_test

### C-014: Clearly different groups → is_significant=True

**Given**:
- `group_a = [0.9, 0.85, 0.88, 0.92, 0.87]`
- `group_b = [0.1, 0.12, 0.09, 0.11, 0.08]`

**When** `significance_test(group_a, group_b)` is called

**Then** `p_value < 0.05` and `is_significant == True`.

Analytic ground truth: U=25 (max, n1=n2=5), p=2/C(10,5)≈0.0079 < 0.05 ✓

```python
p, sig = significance_test(
    [0.9, 0.85, 0.88, 0.92, 0.87],
    [0.1, 0.12, 0.09, 0.11, 0.08],
)
assert sig is True
assert p < 0.05
```

### C-015: Identical groups → is_significant=False

**Given** `group_a = group_b = [0.5, 0.5, 0.5, 0.5, 0.5]`

**When** `significance_test(group_a, group_b)` is called

**Then** `is_significant == False` and `p_value >= 0.05`.

```python
p, sig = significance_test([0.5] * 5, [0.5] * 5)
assert sig is False
assert p >= 0.05
```

### C-016: Return type is (float, bool)

**Given** any two valid groups

**When** `significance_test(group_a, group_b)` is called

**Then** the result is a tuple where the first element is `float` and the second is `bool`.

```python
result = significance_test([0.5, 0.6], [0.4, 0.3])
assert isinstance(result, tuple) and len(result) == 2
assert isinstance(result[0], float)
assert isinstance(result[1], bool)
```

### C-017: Two-sided symmetry

**Given** `group_a` and `group_b` are distinct groups

**When** `significance_test(group_a, group_b)` and `significance_test(group_b, group_a)` are called

**Then** both return the same `p_value`.

```python
a = [0.9, 0.85, 0.88, 0.92, 0.87]
b = [0.1, 0.12, 0.09, 0.11, 0.08]
p_ab, _ = significance_test(a, b)
p_ba, _ = significance_test(b, a)
assert abs(p_ab - p_ba) < 1e-12
```

---

## US5 — summarise_metric

### C-018: Correct mean and metric_name

**Given** `name="dr"`, `values=[0.8, 0.7, 0.75]`

**When** `summarise_metric(name, values)` is called

**Then**:
- `result.metric_name == "dr"`
- `abs(result.mean - 0.75) < 1e-9`
- `abs(result.std - 0.05) < 1e-9`

Analytic ground truth: mean=0.75, std(ddof=1)=sqrt(((0.05)²+(0.05)²+0²)/2)=sqrt(0.0025)=0.05 ✓

```python
result = summarise_metric("dr", [0.8, 0.7, 0.75])
assert result.metric_name == "dr"
assert abs(result.mean - 0.75) < 1e-9
assert abs(result.std - 0.05) < 1e-9
```

### C-019: Identical values → std=0, zero-width CI

**Given** `values = [0.5, 0.5, 0.5]`

**When** `summarise_metric("x", values)` is called

**Then** `std=0.0`, `ci_low == ci_high == mean == 0.5`.

```python
result = summarise_metric("x", [0.5, 0.5, 0.5])
assert result.std == 0.0
assert result.ci_low == 0.5
assert result.ci_high == 0.5
assert result.mean == 0.5
```

### C-020: Empty values → ValueError

**Given** `values = []`

**When** `summarise_metric("x", [])` is called

**Then** `ValueError` is raised.

```python
with pytest.raises(ValueError):
    summarise_metric("x", [])
```

---

## Contract Summary Table

| Contract | User Story | Description |
|----------|-----------|-------------|
| C-001 | US1 | MultiSeedResult construction |
| C-002 | US1 | Default ci_level=0.95 |
| C-003 | US1 | Frozen — FrozenInstanceError |
| C-004 | US2 | Runner called N times |
| C-005 | US2 | Total record count = N × per-call |
| C-006 | US2 | Records tagged with correct seed |
| C-007 | US2 | Empty seeds → empty list |
| C-008 | US3 | Identical values → zero-width CI |
| C-009 | US3 | Determinism |
| C-010 | US3 | CI brackets mean |
| C-011 | US3 | Empty values → ValueError |
| C-012 | US3 | n_resamples=0 → ValueError |
| C-013 | US3 | ci_level out of range → ValueError |
| C-014 | US4 | Different groups → significant |
| C-015 | US4 | Identical groups → not significant |
| C-016 | US4 | Return type (float, bool) |
| C-017 | US4 | Two-sided symmetry |
| C-018 | US5 | Correct mean and metric_name |
| C-019 | US5 | Identical values → zero-width CI |
| C-020 | US5 | Empty values → ValueError |

**Total**: 20 contracts across 5 user stories.
