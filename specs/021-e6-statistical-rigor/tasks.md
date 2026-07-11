# Tasks: Statistical Rigor Layer (F21)

**Feature**: `021-e6-statistical-rigor`
**Input**: Design documents from `/specs/021-e6-statistical-rigor/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/statistics-contract.md ✓

**Approach**: TDD — 20 tests written upfront (red), then implementation drives them green story-by-story.
**Baseline**: 237 passed, 4 skipped, 6 failed | **Target**: ≥257 passed, 4 skipped, 6 failed

---

## Phase 1: Setup

**Purpose**: Install new dependency, create stub module, record baseline.

- [ ] T001 Record baseline test count: `cd src && source ../.venv/bin/activate && pytest ../tests/ -q 2>&1 | tail -3` — expect "237 passed, 4 skipped, 6 failed"
- [ ] T002 Add `scipy>=1.12` to `requirements.in`, recompile with `pip-compile requirements.in -o requirements.txt`, then `pip install -r requirements.txt` in the venv — verify with `python -c "from scipy import stats; print('scipy ok')"`
- [ ] T003 Create stub `src/aatf/statistics.py` with `MultiSeedResult` frozen dataclass + `raise NotImplementedError` stubs for all 4 functions — all 5 names must be importable to prevent ImportError during test collection

Stub content for T003:

```python
"""Multi-seed statistical analysis layer."""
from __future__ import annotations
import dataclasses
from dataclasses import dataclass
from typing import Callable
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

def run_multi_seed(runner, seeds):
    raise NotImplementedError

def bootstrap_ci(values, ci_level=0.95, n_resamples=1000, *, rng_seed=0):
    raise NotImplementedError

def significance_test(group_a, group_b):
    raise NotImplementedError

def summarise_metric(name, values, ci_level=0.95):
    raise NotImplementedError
```

**Checkpoint**: `python -c "from aatf.statistics import MultiSeedResult, run_multi_seed, bootstrap_ci, significance_test, summarise_metric; print('stubs ok')"` exits with code 0.

---

## Phase 2: Foundational — Write All 20 Tests (Red Phase)

**Purpose**: Write the complete test file upfront. All 20 tests must FAIL (or raise NotImplementedError) before any implementation begins.

**⚠️ CRITICAL**: Do NOT implement any logic until this phase is complete and pytest confirms failures.

- [ ] T004 Write test helpers and all 20 contracts in `tests/test_statistics.py` — full file per spec below
- [ ] T005 Run `cd src && pytest ../tests/test_statistics.py -v 2>&1 | tail -30` — confirm exactly 20 failures/errors (NotImplementedError), 0 passes

**Complete test file for T004** (`tests/test_statistics.py`):

```python
"""Tests for aatf.statistics — F21 statistical rigor layer. Contracts C-001..C-020."""
from __future__ import annotations

import dataclasses
import pytest
import numpy as np

from aatf.statistics import (
    MultiSeedResult,
    run_multi_seed,
    bootstrap_ci,
    significance_test,
    summarise_metric,
)
from aatf.metrics import EpisodeRecord
from aatf.episode import StepRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _step(detected: bool = False) -> StepRecord:
    return StepRecord(
        action_id="noop", detected=detected, stage_progress=False, reward=0.0
    )


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
    rec = MultiSeedResult(
        metric_name="x", values=[0.5], mean=0.5, std=0.0, ci_low=0.5, ci_high=0.5
    )
    assert rec.ci_level == 0.95


def test_c003_frozen_raises_on_set():
    """C-003: Frozen dataclass — assignment raises FrozenInstanceError or AttributeError."""
    rec = MultiSeedResult(
        metric_name="x", values=[0.5], mean=0.5, std=0.0, ci_low=0.5, ci_high=0.5
    )
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
```

**Checkpoint**: `cd src && pytest ../tests/test_statistics.py -v 2>&1 | tail -5` shows 20 FAILED/ERROR, 0 passed.

---

## Phase 3: User Story 1 — MultiSeedResult Container (P1)

**Goal**: `MultiSeedResult` frozen dataclass fully functional; C-001, C-002, C-003 green.

**Independent Test**: `cd src && pytest ../tests/test_statistics.py::test_c001_construction_fields ../tests/test_statistics.py::test_c002_default_ci_level ../tests/test_statistics.py::test_c003_frozen_raises_on_set -v`

- [ ] T006 [US1] Implement `MultiSeedResult` frozen dataclass in `src/aatf/statistics.py` — already present in stub; verify C-001, C-002, C-003 pass (they should pass even from stub since dataclass is already complete)
- [ ] T007 [US1] Run `cd src && pytest ../tests/test_statistics.py::test_c001_construction_fields ../tests/test_statistics.py::test_c002_default_ci_level ../tests/test_statistics.py::test_c003_frozen_raises_on_set -v` — expect 3 PASSED

**Checkpoint**: 3/20 green. Remaining 17 still fail on NotImplementedError.

---

## Phase 4: User Story 2 — run_multi_seed (P2)

**Goal**: `run_multi_seed` sequential orchestration; C-004..C-007 green.

**Independent Test**: `cd src && pytest ../tests/test_statistics.py -k "c004 or c005 or c006 or c007" -v`

- [ ] T008 [US2] Implement `run_multi_seed` in `src/aatf/statistics.py`:
  ```python
  def run_multi_seed(
      runner: Callable[[int], list[EpisodeRecord]],
      seeds: list[int],
  ) -> list[EpisodeRecord]:
      result: list[EpisodeRecord] = []
      for seed in seeds:
          for record in runner(seed):
              result.append(dataclasses.replace(record, seed=seed))
      return result
  ```
  Key: `dataclasses.replace(record, seed=seed)` — NOT `record.seed = seed` (frozen).
- [ ] T009 [US2] Run `cd src && pytest ../tests/test_statistics.py -k "c004 or c005 or c006 or c007" -v` — expect 4 PASSED

**Checkpoint**: 7/20 green.

---

## Phase 5: User Story 3 — bootstrap_ci (P3)

**Goal**: Non-parametric bootstrap confidence interval; C-008..C-013 green.

**Independent Test**: `cd src && pytest ../tests/test_statistics.py -k "c008 or c009 or c010 or c011 or c012 or c013" -v`

- [ ] T010 [US3] Implement `bootstrap_ci` in `src/aatf/statistics.py`:
  ```python
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
  ```
  Key: `np.random.default_rng(rng_seed)` — NOT `np.random.seed()` (isolates global state).
- [ ] T011 [US3] Run `cd src && pytest ../tests/test_statistics.py -k "c008 or c009 or c010 or c011 or c012 or c013" -v` — expect 6 PASSED (note: C-013 tests 3 invalid ci_level values in one test — all 3 must raise)

**Checkpoint**: 13/20 green.

---

## Phase 6: User Story 4 — significance_test (P4)

**Goal**: Two-sided Mann-Whitney U significance test; C-014..C-017 green.

**Independent Test**: `cd src && pytest ../tests/test_statistics.py -k "c014 or c015 or c016 or c017" -v`

- [ ] T012 [US4] Implement `significance_test` in `src/aatf/statistics.py`:
  ```python
  def significance_test(
      group_a: list[float],
      group_b: list[float],
  ) -> tuple[float, bool]:
      result = stats.mannwhitneyu(group_a, group_b, alternative="two-sided")
      return float(result.pvalue), bool(result.pvalue < 0.05)
  ```
  Key: `alternative="two-sided"` is required — not "greater" or "less".
- [ ] T013 [US4] Run `cd src && pytest ../tests/test_statistics.py -k "c014 or c015 or c016 or c017" -v` — expect 4 PASSED (analytic: p_ab≈0.0079 for C-014, p=1.0 for C-015)

**Checkpoint**: 17/20 green.

---

## Phase 7: User Story 5 — summarise_metric (P5)

**Goal**: Ergonomic wrapper; C-018..C-020 green; full suite at ≥257.

**Independent Test**: `cd src && pytest ../tests/test_statistics.py -k "c018 or c019 or c020" -v`

- [ ] T014 [US5] Implement `summarise_metric` in `src/aatf/statistics.py`:
  ```python
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
  ```
  Key: `ddof=1` for Bessel-corrected sample std (not population std).
- [ ] T015 [US5] Run `cd src && pytest ../tests/test_statistics.py -k "c018 or c019 or c020" -v` — expect 3 PASSED

**Checkpoint**: 20/20 green on test_statistics.py.

---

## Phase 8: Polish & Validation

**Purpose**: Code quality, full-suite verification, commit, merge.

- [ ] T016 Run `ruff check src/aatf/statistics.py tests/test_statistics.py --fix` — fix any lint issues (unused imports, line-too-long)
- [ ] T017 Run `ruff format src/aatf/statistics.py tests/test_statistics.py` — auto-format
- [ ] T018 Run full suite `cd src && pytest ../tests/ -q 2>&1 | tail -5` — confirm ≥257 passed, 4 skipped, 6 failed (pre-existing Docker tests only)
- [ ] T019 Commit all changes: `src/aatf/statistics.py`, `tests/test_statistics.py`, `requirements.in`, `requirements.txt` with message "feat(statistics): add F21 statistical rigor layer — MultiSeedResult + bootstrap_ci + significance_test"
- [ ] T020 Merge branch `021-e6-statistical-rigor` to `main` (fast-forward)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No prior dependencies — T001 → T002 → T003 sequential (T002 must complete before venv has scipy; T003 needs scipy import in stub)
- **Phase 2 (Red phase)**: Depends on Phase 1 — T004 then T005 sequential
- **Phases 3–7 (US1–US5)**: Depend on Phase 2 completion (all tests written); implement in P1→P5 order
- **Phase 8 (Polish)**: Depends on all 20 tests green

### User Story Dependencies

- **US1 (P1)**: Trivially satisfies the stub — just verify 3 tests pass
- **US2 (P2)**: No dependency on US1; only needs stub + EpisodeRecord from F20
- **US3 (P3)**: No dependency on US1/US2; pure numpy
- **US4 (P4)**: No dependency on US1/US2/US3; pure scipy
- **US5 (P5)**: Depends on US3 (`bootstrap_ci` must be implemented); cannot be green until T010 done

### Within Each User Story

- Write tests first (Phase 2) → verify red → implement → verify green
- Never skip the red-phase verification

### Parallel Opportunities

- T016 (ruff check) and T018 (full suite) cannot run in parallel — ruff changes files, full suite must see clean state
- T006 and T008 could theoretically run in parallel (different functions), but keeping sequential is safer for tracking

---

## Parallel Example: US3 bootstrap_ci

```bash
# Single function, sequential:
Task T010: "Implement bootstrap_ci in src/aatf/statistics.py"
Task T011: "Run pytest C-008..C-013 — expect 6 PASSED"
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 (Setup + scipy install)
2. Complete Phase 2 (all 20 tests written + red confirmed)
3. Complete Phase 3 (US1 — MultiSeedResult 3 tests green)
4. Validate independently

### Incremental Delivery

1. Phase 1 → scipy available
2. Phase 2 → all 20 red
3. Phase 3 → 3 green (US1)
4. Phase 4 → 7 green (US1+US2)
5. Phase 5 → 13 green (US1+US2+US3)
6. Phase 6 → 17 green (US1+US2+US3+US4)
7. Phase 7 → 20 green (all)
8. Phase 8 → clean + commit + merge

---

## Notes

- `[P]` marks tasks operating on different files with no dependencies — can run in parallel
- `[USn]` maps to the user story in spec.md
- **Architecture invariants** (do not deviate):
  - `dataclasses.replace(record, seed=seed)` — never `record.seed = seed`
  - `np.random.default_rng(rng_seed)` — never `np.random.seed()`
  - `np.std(values, ddof=1)` — never `ddof=0`
  - `alternative="two-sided"` in mannwhitneyu — always
- Total tasks: 20 (T001–T020)
- Tests per story: US1=3, US2=4, US3=6, US4=4, US5=3 → 20 total
