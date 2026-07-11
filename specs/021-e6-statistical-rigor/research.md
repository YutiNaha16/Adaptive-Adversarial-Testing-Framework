# Research: Statistical Rigor Layer (F21)

**Date**: 2026-07-11
**Feature**: 021-e6-statistical-rigor

## Decision 1: Bootstrap method — percentile, not BCa

**Decision**: Use the percentile bootstrap: resample with replacement `n_resamples` times, compute the mean of each resample, then return the `(1-ci_level)/2` and `1-(1-ci_level)/2` percentiles of the resulting distribution.

**Rationale**: The percentile method is the simplest correct non-parametric bootstrap. It is well-understood, widely cited, and appropriate for Phase 1 scientific validity. BCa (bias-corrected and accelerated) is more accurate for skewed distributions but adds implementation complexity (jackknife acceleration term) that is out of scope. For 5–30 seeds, the distributions will be roughly symmetric and BCa provides minimal additional accuracy.

**Analytic verification** (ci_level=0.95, n_resamples=1000):
- `values = [0.5, 0.5, 0.5]` → all resamples have mean=0.5 → p2.5=0.5, p97.5=0.5 → (0.5, 0.5) ✓
- `values = [0.0, 1.0]` → resample means are 0.0, 0.5, or 1.0 with prob 0.25/0.5/0.25 → p2.5≈0.0, p97.5≈1.0 (bounds ≈ [0.0, 1.0])

**Alternatives considered**: BCa bootstrap — rejected (complexity); t-distribution CI — rejected (parametric, assumes normality; wrong for small n or skewed metrics).

## Decision 2: Significance test — Mann-Whitney U, two-sided

**Decision**: `scipy.stats.mannwhitneyu(group_a, group_b, alternative="two-sided")`.

**Rationale**: Mann-Whitney U is the standard non-parametric alternative to the two-sample t-test. It makes no distributional assumption (correct for detection rates, which are bounded in [0,1]). Two-sided is the scientifically appropriate choice when the direction of the difference is not assumed in advance. Using scipy avoids re-implementing the exact or approximate U statistic.

**Analytic verification** (n1=n2=5, all A > all B):
- `group_a = [0.9, 0.85, 0.88, 0.92, 0.87]`, `group_b = [0.1, 0.12, 0.09, 0.11, 0.08]`
- U = 5×5 = 25 (max), p = 2/C(10,5) = 2/252 ≈ 0.0079 < 0.05 → is_significant=True ✓
- `group_a = group_b = [0.5]*5` → all ties → p = 1.0 → is_significant=False ✓
- Symmetry: mannwhitneyu(a, b, two-sided).pvalue == mannwhitneyu(b, a, two-sided).pvalue ✓ (property of two-sided test)

**Alternatives considered**: Welch's t-test — rejected (parametric, assumes normal distribution); Wilcoxon signed-rank — rejected (for paired samples, not independent groups); permutation test — correct but much slower and adds implementation complexity.

## Decision 3: RNG for bootstrap — numpy.random.default_rng(rng_seed)

**Decision**: `rng = numpy.random.default_rng(rng_seed)`. Use `rng.integers(0, n, size=(n_resamples, n))` to generate indices, then index into values array.

**Rationale**: `default_rng` is the modern NumPy random API (PCG64 generator); it is seeded independently of global state, so it does not interact with `np.random.seed()` calls elsewhere in the codebase. This is the correct approach per the constitution's seeding principle (II): all randomness isolated from global state.

**Alternatives considered**: `np.random.seed()` + `np.random.choice()` — rejected; mutates global NumPy state. `random.Random(rng_seed).choices()` — rejected; Python stdlib, much slower than NumPy for 1000×N resampling.

## Decision 4: run_multi_seed — sequential, not parallel

**Decision**: Call runner sequentially in a for-loop: `for seed in seeds: results.extend(runner(seed))`. Tag each returned record with `dataclasses.replace(record, seed=seed)`.

**Rationale**: Parallelism is explicitly out of scope (F25). Sequential execution is deterministic, easy to test, and avoids any subprocess/multiprocessing complexity. The runner callable is caller-supplied and may not be thread-safe.

**seed-field overwrite**: `EpisodeRecord` is `frozen=True`, so mutation is not possible. `dataclasses.replace(record, seed=seed)` creates a new frozen instance with the seed field overwritten. This is the standard Python pattern for "modifying" frozen dataclasses. No copy of steps or other fields — `dataclasses.replace` does a shallow copy of all fields except those specified.

**Alternatives considered**: `multiprocessing.Pool.map` — rejected; out of scope (F25 parallelism). Direct mutation of `record.seed` — rejected; `frozen=True` raises `FrozenInstanceError`.

## Decision 5: std with ddof=1 (sample std)

**Decision**: `np.std(values, ddof=1)` (Bessel-corrected sample standard deviation).

**Rationale**: `values` is a sample of per-seed metric values drawn from an unknown population distribution. The unbiased estimator of population std uses `n-1` in the denominator (ddof=1). This is the statistically correct choice when reporting dispersion of sample data, as required by the constitution's scientific validity clause.

**Edge case**: For `len(values) == 1`, `ddof=1` produces `std=nan` (0/0). This is mathematically correct but should be documented. The `summarise_metric` function should raise `ValueError` for empty input; single-element input yields std=nan which callers should be aware of.

**Alternatives considered**: `np.std(values, ddof=0)` (population std) — rejected; biased for small samples (n=5–30).

## Decision 6: Dependency — scipy>=1.12 added to requirements.in

**Decision**: Add `scipy>=1.12` to `requirements.in`, recompile with `pip-tools` (`pip-compile requirements.in -o requirements.txt`), then `pip install -r requirements.txt` in the venv.

**Rationale**: scipy 1.12+ is the current stable release family with a stable `mannwhitneyu` API. Pinning with `>=1.12` gives a minimum floor; pip-tools will resolve to the latest compatible version and pin it with a hash in requirements.txt.

**Analytic check**: scipy is not currently in the venv. Must be installed before tests can run. Task T002 handles this.

## Decision 7: Module name — aatf.statistics (not aatf.stats)

**Decision**: `src/aatf/statistics.py` — not `stats.py`.

**Rationale**: `stats` shadows Python's `statistics` stdlib module in some import contexts; more importantly, `aatf.stats` could collide with downstream readers expecting `scipy.stats`. The full name `statistics` is unambiguous and matches the spec's `aatf.statistics` requirement.

## Decision 8: Analytic ground truths for all contracts

**C-001** (MultiSeedResult construction): Direct field assignment, all accessible.

**C-002** (default ci_level=0.95): `MultiSeedResult(metric_name="x", values=[0.5], mean=0.5, std=0.0, ci_low=0.5, ci_high=0.5)` → `rec.ci_level == 0.95` ✓

**C-004** (runner call count): Use a counter list `calls=[]`; runner appends seed to calls each invocation; assert `calls == seeds_list`.

**C-005** (total records): runner returns 3 records per call; 5 seeds → 15 total records.

**C-006** (seed tagging): `records[0].seed == seeds[0]`, `records[3].seed == seeds[1]`, etc.

**C-008** (bootstrap identical values): `values=[0.5,0.5,0.5]`, any rng_seed → all resample means = 0.5 → p2.5=p97.5=0.5.

**C-009** (bootstrap determinism): `bootstrap_ci([0.1,0.5,0.9], rng_seed=0)` called twice → identical tuple.

**C-010** (bootstrap brackets mean): `values=[0.1,0.3,0.5,0.7,0.9]`, mean=0.5; assert ci_low < 0.5 < ci_high.

**C-014** (significance clearly different): `group_a=[0.9,0.85,0.88,0.92,0.87]`, `group_b=[0.1,0.12,0.09,0.11,0.08]` → p≈0.0079 < 0.05 → True.

**C-015** (significance identical): `group_a=group_b=[0.5,0.5,0.5,0.5,0.5]` → p=1.0 → False.

**C-017** (symmetry): `significance_test(a, b)[0] == significance_test(b, a)[0]`.

**C-018** (summarise_metric mean): `values=[0.8,0.7,0.75]` → mean=0.75, std=0.05 (ddof=1), metric_name="dr".

**C-019** (summarise identical values): `values=[0.5,0.5,0.5]` → std=0.0, ci_low==ci_high==0.5==mean.
