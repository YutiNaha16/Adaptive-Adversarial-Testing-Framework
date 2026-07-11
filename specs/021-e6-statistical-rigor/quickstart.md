# Quickstart: Statistical Rigor Layer (F21)

**Feature**: 021-e6-statistical-rigor  
**Module**: `aatf.statistics`

## Overview

`aatf.statistics` provides five components for multi-seed statistical analysis of adversarial testing results. All components are pure in-memory: no I/O, no side effects.

## Scenario 1: Basic multi-seed run and summarise

Run an experiment with 5 seeds, get a detection_rate `MultiSeedResult` with CI:

```python
from aatf.statistics import run_multi_seed, summarise_metric
from aatf.metrics import detection_rate

def my_runner(seed: int):
    """Caller-supplied: seeds internal RNG, runs episodes, returns EpisodeRecords."""
    ...

# Run 5 seeds
all_records = run_multi_seed(my_runner, seeds=[0, 1, 2, 3, 4])

# Split per seed (each group of records came from one seed)
# Or compute metric across all:
dr = detection_rate(all_records)  # Overall detection rate

# For per-seed values:
records_by_seed = {}
for r in all_records:
    records_by_seed.setdefault(r.seed, []).append(r)

per_seed_dr = [detection_rate(recs) for recs in records_by_seed.values()]

# Summarise with bootstrap CI
result = summarise_metric("detection_rate", per_seed_dr)
print(f"DR: {result.mean:.3f} [{result.ci_low:.3f}, {result.ci_high:.3f}] ±{result.std:.3f}")
# → DR: 0.750 [0.623, 0.877] ±0.050
```

## Scenario 2: Bootstrap CI on raw values

Compute a 90% confidence interval on a list of per-seed adaptation gains:

```python
from aatf.statistics import bootstrap_ci

gains = [12.5, 15.2, 11.8, 14.0, 13.3]  # one per seed (%)
lo, hi = bootstrap_ci(gains, ci_level=0.90, n_resamples=2000, rng_seed=42)
print(f"90% CI on adaptation gain: [{lo:.2f}%, {hi:.2f}%]")
```

**Determinism guarantee**: `bootstrap_ci(values, rng_seed=42)` always returns the same tuple for the same inputs.

## Scenario 3: Significance test between two attacker policies

Compare LinUCB vs Random attacker detection rates across seeds:

```python
from aatf.statistics import significance_test

linucb_dr = [0.22, 0.19, 0.25, 0.21, 0.18]   # lower = evades detection better
random_dr = [0.55, 0.52, 0.58, 0.54, 0.56]

p_value, is_significant = significance_test(linucb_dr, random_dr)
print(f"p={p_value:.4f}, significant={is_significant}")
# → p=0.0079, significant=True
```

The test is **two-sided** (null: groups are identical) and **non-parametric** (no normal distribution assumption). Threshold: p < 0.05.

## Scenario 4: Full pipeline — run + summarise + test

```python
from aatf.statistics import run_multi_seed, summarise_metric, significance_test
from aatf.metrics import detection_rate

seeds = [10, 20, 30, 40, 50]

# Run baseline (RandomAttacker)
baseline_records = run_multi_seed(baseline_runner, seeds)
# Run learner (LinUCBAttacker)
learner_records = run_multi_seed(learner_runner, seeds)

# Per-seed detection rates
def per_seed_dr(records):
    by_seed = {}
    for r in records: by_seed.setdefault(r.seed, []).append(r)
    return [detection_rate(v) for v in by_seed.values()]

baseline_dr_per_seed = per_seed_dr(baseline_records)
learner_dr_per_seed = per_seed_dr(learner_records)

# Summarise
baseline_summary = summarise_metric("detection_rate_baseline", baseline_dr_per_seed)
learner_summary = summarise_metric("detection_rate_learner", learner_dr_per_seed)

# Test significance
p, sig = significance_test(baseline_dr_per_seed, learner_dr_per_seed)

print(f"Baseline DR: {baseline_summary.mean:.3f} 95%CI [{baseline_summary.ci_low:.3f}, {baseline_summary.ci_high:.3f}]")
print(f"Learner DR:  {learner_summary.mean:.3f} 95%CI [{learner_summary.ci_low:.3f}, {learner_summary.ci_high:.3f}]")
print(f"Significant difference: {sig} (p={p:.4f})")
```

## Error handling

```python
from aatf.statistics import bootstrap_ci, summarise_metric

# Empty values
try:
    bootstrap_ci([])
except ValueError as e:
    print(e)  # "values must be non-empty"

# Invalid n_resamples
try:
    bootstrap_ci([0.5], n_resamples=0)
except ValueError:
    pass

# Invalid ci_level
try:
    summarise_metric("x", [0.5], ci_level=1.5)
except ValueError:
    pass
```

## Importing

```python
from aatf.statistics import (
    MultiSeedResult,
    run_multi_seed,
    bootstrap_ci,
    significance_test,
    summarise_metric,
)
```
