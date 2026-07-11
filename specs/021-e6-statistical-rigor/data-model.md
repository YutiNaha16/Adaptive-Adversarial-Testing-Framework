# Data Model: Statistical Rigor Layer (F21)

**Feature**: 021-e6-statistical-rigor  
**Date**: 2026-07-11

## Entities

### 1. MultiSeedResult

**Purpose**: Immutable container for a metric computed across multiple seeds. Passed downstream to `summarise_metric`, report generator (F24), and Phase 1 gate (F26).

```python
@dataclass(frozen=True)
class MultiSeedResult:
    metric_name: str          # Human-readable label (e.g., "detection_rate")
    values: list[float]       # Per-seed raw values, length = len(seeds)
    mean: float               # np.mean(values)
    std: float                # np.std(values, ddof=1) — sample std
    ci_low: float             # Bootstrap lower bound
    ci_high: float            # Bootstrap upper bound
    ci_level: float = 0.95    # Confidence level (default 0.95)
```

**Invariants** (enforced by frozen=True; caller is responsible for correctness):
- `0.0 < ci_level < 1.0`
- `ci_low <= mean <= ci_high`
- `len(values) >= 1`
- `std >= 0.0`

**Serialisation**: `dataclasses.asdict(result)` → JSON-compatible dict (all fields are native Python types). Used by F24 (report generator).

**Relationships**:
- Produced by `summarise_metric()`
- Consumed by F24 `ReportGenerator` and F26 `PhaseGate`

---

### 2. EpisodeRecord (imported from aatf.metrics — F20)

**Not defined here.** Defined in `src/aatf/metrics.py` by F20. Imported as:

```python
from aatf.metrics import EpisodeRecord
```

Relevant fields for `run_multi_seed`:
- `seed: int` — overwritten via `dataclasses.replace(record, seed=seed)` for each call to runner

---

### 3. Runner callable (protocol)

**Not a class — a function signature protocol.**

```python
# Type alias (informational)
Runner = Callable[[int], list[EpisodeRecord]]
```

- Input: `seed: int`
- Output: `list[EpisodeRecord]` — any length (including 0)
- Caller-supplied; not defined by this feature.
- May call `aatf.episode`, `aatf.linucb`, or any other module — this feature treats it as a black box.

---

## Function Signatures

### `run_multi_seed`

```python
def run_multi_seed(
    runner: Callable[[int], list[EpisodeRecord]],
    seeds: list[int],
) -> list[EpisodeRecord]:
```

- Calls `runner(seed)` once per seed in `seeds` (sequential, in order).
- For each returned record `r`: appends `dataclasses.replace(r, seed=seed)` to result list.
- Returns concatenated list (order: seed0 records, then seed1 records, …).
- Empty `seeds` → returns `[]`.

---

### `bootstrap_ci`

```python
def bootstrap_ci(
    values: list[float],
    ci_level: float = 0.95,
    n_resamples: int = 1000,
    *,
    rng_seed: int = 0,
) -> tuple[float, float]:
```

- **Raises `ValueError`** if:
  - `not values` (empty list)
  - `n_resamples <= 0`
  - `not (0.0 < ci_level < 1.0)`
- Algorithm:
  1. `arr = np.array(values, dtype=float)`
  2. `rng = np.random.default_rng(rng_seed)`
  3. `indices = rng.integers(0, len(arr), size=(n_resamples, len(arr)))`
  4. `means = arr[indices].mean(axis=1)`
  5. `lo = (1 - ci_level) / 2 * 100`; `hi = (1 - lo / 100) * 100`
  6. Return `(float(np.percentile(means, lo)), float(np.percentile(means, hi)))`

---

### `significance_test`

```python
def significance_test(
    group_a: list[float],
    group_b: list[float],
) -> tuple[float, bool]:
```

- Calls `scipy.stats.mannwhitneyu(group_a, group_b, alternative="two-sided")`.
- Returns `(float(result.pvalue), bool(result.pvalue < 0.05))`.
- No validation of group lengths — caller responsibility (Mann-Whitney handles singleton groups).

---

### `summarise_metric`

```python
def summarise_metric(
    name: str,
    values: list[float],
    ci_level: float = 0.95,
) -> MultiSeedResult:
```

- **Raises `ValueError`** if `not values` (delegates to `bootstrap_ci`).
- Algorithm:
  1. `ci_low, ci_high = bootstrap_ci(values, ci_level=ci_level)`
  2. Return `MultiSeedResult(metric_name=name, values=values, mean=float(np.mean(values)), std=float(np.std(values, ddof=1)), ci_low=ci_low, ci_high=ci_high, ci_level=ci_level)`

---

## Module Structure

```text
src/aatf/statistics.py
├── MultiSeedResult          @dataclass(frozen=True)
├── run_multi_seed()
├── bootstrap_ci()
├── significance_test()
└── summarise_metric()
```

**All 5 names** importable from a single statement:

```python
from aatf.statistics import (
    MultiSeedResult,
    run_multi_seed,
    bootstrap_ci,
    significance_test,
    summarise_metric,
)
```

## Dependencies

| Dependency | Import | Already in venv? |
|------------|--------|-----------------|
| `numpy` | `import numpy as np` | Yes (pinned in requirements.txt) |
| `scipy` | `from scipy import stats` | **No — must add `scipy>=1.12` to requirements.in** |
| `dataclasses` | `from dataclasses import dataclass, replace` | Yes (stdlib) |
| `typing` | `from __future__ import annotations; from typing import Callable` | Yes (stdlib) |
| `aatf.metrics` | `from aatf.metrics import EpisodeRecord` | Yes (F20, merged to main) |
