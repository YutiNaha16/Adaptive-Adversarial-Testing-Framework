# Implementation Plan: Statistical Rigor Layer (F21)

**Branch**: `021-e6-statistical-rigor` | **Date**: 2026-07-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/021-e6-statistical-rigor/spec.md`

## Summary

Add `aatf.statistics` module providing `MultiSeedResult` frozen dataclass + 4 pure functions (`run_multi_seed`, `bootstrap_ci`, `significance_test`, `summarise_metric`). All stateless, in-memory. Adds `scipy>=1.12` as the only new dependency (for Mann-Whitney U test). Implements the constitution's "statistical honesty is mandatory" clause: every headline metric must be a multi-seed result with dispersion and significance test.

## Technical Context

**Language/Version**: Python 3.12 (pinned per F01 scaffold)  
**Primary Dependencies**: numpy (already in venv), scipy>=1.12 (NEW — must add to requirements.in), dataclasses + typing (stdlib)  
**Storage**: N/A — pure in-memory; no file I/O  
**Testing**: pytest (from src/: `cd src && pytest ../tests/`)  
**Target Platform**: Linux / CPython 3.12  
**Project Type**: Single Python package  
**Performance Goals**: N/A — 20 tests, all fast (bootstrap with n_resamples=1000 runs in <0.1s)  
**Constraints**: All functions must be deterministic given same inputs; no global state mutation (use `np.random.default_rng(rng_seed)`, not `np.random.seed`)  
**Scale/Scope**: 1 file (~70 LOC), 20 new tests (+20 net), baseline 237 → target ≥257

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I — Safety | PASS | Pure in-memory; no network, no lab environment, no traffic |
| II — Reproducibility | PASS | `rng_seed` parameter; `default_rng` isolates global state |
| III — Pluggable Defence | N/A | Offline analysis layer; no defender coupling |
| IV — Scientific Validity/TDD | PASS | Exactly 20 contracts upfront; bootstrap CI + Mann-Whitney = standard statistical methods |
| V — Explainability | N/A | Feeds F24 report; not built here |
| VI — Observability | PASS | Implements the dispersion + significance-test part of §IV ("statistical honesty is mandatory") |
| VII — Phased Delivery | PASS | E6 feature; Phase 1 gate (F26) cannot complete without this |

**No violations.** Complexity tracking: N/A.

## Project Structure

### Documentation (this feature)

```text
specs/021-e6-statistical-rigor/
├── plan.md              # This file
├── research.md          # Phase 0 — design decisions (bootstrap, Mann-Whitney, scipy, etc.)
├── data-model.md        # Phase 1 — MultiSeedResult + function signatures
├── quickstart.md        # Phase 1 — 4 integration scenarios
├── contracts/
│   └── statistics-contract.md  # 20 contracts C-001..C-020
└── tasks.md             # Phase 2 output (/sp.tasks — NOT created by /sp.plan)
```

### Source Code

```text
src/aatf/
└── statistics.py        # NEW — ~70 LOC

tests/
└── test_statistics.py   # NEW — ~200 LOC, 20 tests

requirements.in          # MODIFY — add scipy>=1.12
requirements.txt         # REGENERATE — pip-compile requirements.in
```

## Implementation Sketch (~70 LOC)

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
    return float(result.pvalue), bool(result.pvalue < 0.05)


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

## Dependency Install Plan

**Before red-phase tests can run**, scipy must be installed:

```bash
# Step 1: add scipy>=1.12 to requirements.in
# Step 2: recompile
cd /home/yuti/Adaptive-Adversarial-Testing-Framework
source .venv/bin/activate
pip-compile requirements.in -o requirements.txt
# Step 3: install
pip install -r requirements.txt
```

Verify: `python -c "from scipy import stats; print(stats.__version__)"` should print without error.

## TDD Plan

**Baseline**: 237 passed, 4 skipped, 6 failed (pre-existing Docker tests)  
**Target**: ≥257 passed, 4 skipped, 6 failed (+20 new tests)

**Red phase**: Write all 20 tests in `tests/test_statistics.py`. Import all 5 names at module level → need stubs in `statistics.py` first to avoid ImportError (same pattern as F20). Stubs: `MultiSeedResult` with `@dataclass(frozen=True)` + `raise NotImplementedError` functions.

**Green phase** (story-by-story):
1. US1: `MultiSeedResult` → C-001, C-002, C-003 green
2. US2: `run_multi_seed` → C-004, C-005, C-006, C-007 green
3. US3: `bootstrap_ci` → C-008, C-009, C-010, C-011, C-012, C-013 green
4. US4: `significance_test` → C-014, C-015, C-016, C-017 green
5. US5: `summarise_metric` → C-018, C-019, C-020 green

**Ruff**: run `ruff check . --fix` and `ruff format .` before final commit.

## Contract-to-Test Mapping

| Contract | User Story | Description |
|----------|-----------|-------------|
| C-001 | US1 | MultiSeedResult construction |
| C-002 | US1 | Default ci_level=0.95 |
| C-003 | US1 | Frozen — FrozenInstanceError |
| C-004 | US2 | Runner called N times |
| C-005 | US2 | Total record count |
| C-006 | US2 | Records tagged with correct seed |
| C-007 | US2 | Empty seeds → empty list |
| C-008 | US3 | Identical values → zero-width CI |
| C-009 | US3 | Determinism |
| C-010 | US3 | CI brackets mean |
| C-011 | US3 | Empty values → ValueError |
| C-012 | US3 | n_resamples=0 → ValueError |
| C-013 | US3 | ci_level out of range → ValueError |
| C-014 | US4 | Different groups → significant (n=5, U=25, p≈0.0079) |
| C-015 | US4 | Identical groups → not significant |
| C-016 | US4 | Return type (float, bool) |
| C-017 | US4 | Two-sided symmetry |
| C-018 | US5 | Correct mean/std (analytic: mean=0.75, std=0.05) |
| C-019 | US5 | Identical values → zero-width CI |
| C-020 | US5 | Empty values → ValueError |

## Complexity Tracking

No constitution violations — complexity tracking not required.
