# Feature Specification: Statistical Rigor Layer (F21)

**Feature Branch**: `021-e6-statistical-rigor`
**Created**: 2026-07-11
**Status**: Draft
**Epic**: E6 — Analysis, Explainability & Reporting

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Multi-Seed Result Container (Priority: P1)

A researcher needs a single structured object that holds all repetitions of a metric — one value per seed — together with the computed mean, standard deviation, and confidence interval. They pass this object downstream to the report generator (F24) without needing to carry raw lists around.

**Why this priority**: Every other story in this feature produces or consumes a `MultiSeedResult`. Without the container, nothing else can be composed or tested. It is the foundation.

**Independent Test**: Construct a `MultiSeedResult` by hand with known field values and verify all fields are accessible and correctly stored.

**Acceptance Scenarios**:

1. **Given** a metric name, a list of per-seed values, pre-computed mean/std, and CI bounds, **When** a `MultiSeedResult` is constructed, **Then** all six fields are accessible with the correct values.
2. **Given** `ci_level` is not specified, **When** a `MultiSeedResult` is constructed, **Then** `ci_level` defaults to `0.95`.
3. **Given** a `MultiSeedResult`, **When** it is passed to a function expecting a plain data holder, **Then** all fields are readable without error.

---

### User Story 2 — Multi-Seed Run Orchestration (Priority: P2)

A researcher wants to run the same experiment with five different seeds to eliminate lucky-run bias. They supply a single callable (the experiment runner) and a list of seed integers, and receive back a flat list of episode records with each record tagged by the seed that produced it — ready to pass directly to `detection_rate` or any other metric function from F20.

**Why this priority**: This is the mechanism that makes multi-seed results possible. Without it, the researcher would have to manually call the runner multiple times and concatenate records, risking mistakes in seed propagation.

**Independent Test**: Supply a mock runner that returns a fixed list of episode records; verify that calling `run_multi_seed` with N seeds calls the runner exactly N times and returns all records concatenated in call order, with each record's `seed` field matching the seed passed to the runner.

**Acceptance Scenarios**:

1. **Given** a runner and a list of 5 seeds, **When** `run_multi_seed` is called, **Then** the runner is invoked exactly 5 times, once per seed.
2. **Given** a runner that returns 3 episode records per call and 5 seeds, **When** `run_multi_seed` is called, **Then** the result contains exactly 15 episode records.
3. **Given** a runner called with seed `42`, **When** the returned records are inspected, **Then** each record's `seed` field equals `42`.
4. **Given** an empty seed list, **When** `run_multi_seed` is called, **Then** it returns an empty list with no error.

---

### User Story 3 — Bootstrap Confidence Interval (Priority: P3)

A researcher has a list of per-seed detection rates (one float per seed, e.g. 5–30 values). They want a 95% confidence interval that is non-parametric — valid regardless of the distribution shape — and reproducible: the same values and the same `rng_seed` must always return exactly the same interval bounds.

**Why this priority**: Bootstrap CI is the statistical backbone of the constitution's "dispersion" requirement. Without it, the researcher cannot satisfy the Phase 1 gate's reporting obligations.

**Independent Test**: Call `bootstrap_ci` with a known list of values and a fixed `rng_seed`; verify the returned bounds bracket the sample mean and that identical inputs produce identical outputs on repeated calls.

**Acceptance Scenarios**:

1. **Given** a list of identical values (e.g. `[0.5, 0.5, 0.5]`) and any `rng_seed`, **When** `bootstrap_ci` is called, **Then** both CI bounds equal that value (zero variance → zero interval width).
2. **Given** a diverse list of values and `rng_seed=0`, **When** `bootstrap_ci` is called twice, **Then** both calls return identical `(ci_low, ci_high)`.
3. **Given** a list of values, **When** `bootstrap_ci` is called with `ci_level=0.95`, **Then** `ci_low < mean(values) < ci_high` (interval brackets the mean).
4. **Given** `ci_level=0.90` vs `ci_level=0.99`, **When** `bootstrap_ci` is called on the same values, **Then** the 0.99 interval is wider than or equal to the 0.90 interval.

---

### User Story 4 — Significance Test (Priority: P4)

A researcher has two lists of per-seed metric values — one for the baseline attacker and one for the LinUCB attacker. They want to know: is the difference statistically significant? They call `significance_test` and receive a p-value and a boolean flag — no manual test setup, no scipy boilerplate.

**Why this priority**: The constitution mandates that "where a claim of improvement is made (e.g. Adaptation Gain), a significance test" must be included. This function is that test.

**Independent Test**: Supply two groups with clearly different distributions (one all-low, one all-high); verify `is_significant=True`. Supply two identical groups; verify `p_value` is large and `is_significant=False`.

**Acceptance Scenarios**:

1. **Given** `group_a = [0.9, 0.85, 0.88]` and `group_b = [0.1, 0.12, 0.09]` (clearly different), **When** `significance_test` is called, **Then** `is_significant` is `True` and `p_value < 0.05`.
2. **Given** two identical lists, **When** `significance_test` is called, **Then** `is_significant` is `False` and `p_value` is large (≥ 0.05).
3. **Given** any two groups, **When** `significance_test` is called, **Then** the result is a tuple of exactly `(float, bool)`.
4. **Given** `group_a` and `group_b` are swapped, **When** `significance_test` is called, **Then** the p-value is identical (two-sided test is symmetric).

---

### User Story 5 — Metric Summary Wrapper (Priority: P5)

A researcher has a list of per-seed detection rates and wants a single call that computes everything — mean, std, 95% CI — and returns it as a `MultiSeedResult` ready for reporting. They don't want to call `bootstrap_ci`, `np.mean`, and `np.std` separately.

**Why this priority**: This is the ergonomic entry point that ties the whole feature together. Researchers call `summarise_metric` rather than assembling the result manually.

**Independent Test**: Call `summarise_metric` with a known list of values; verify the returned `MultiSeedResult` has the correct `mean`, `std`, CI bounds that bracket the mean, and the supplied metric name.

**Acceptance Scenarios**:

1. **Given** `values = [0.8, 0.7, 0.75]` and `name = "detection_rate"`, **When** `summarise_metric` is called, **Then** the returned `MultiSeedResult.mean` equals `mean([0.8, 0.7, 0.75])` and `MultiSeedResult.metric_name == "detection_rate"`.
2. **Given** identical values, **When** `summarise_metric` is called, **Then** `ci_low == ci_high == mean` (zero variance).
3. **Given** any non-empty list, **When** `summarise_metric` is called, **Then** `ci_low ≤ mean ≤ ci_high`.
4. **Given** the same inputs on two calls, **When** `summarise_metric` is called, **Then** the returned `MultiSeedResult` is identical on both calls (deterministic).

---

### Edge Cases

- What if `seeds` is an empty list in `run_multi_seed`? Return an empty list with no error.
- What if `values` has a single element in `bootstrap_ci`? CI bounds both equal that single value.
- What if `values` is empty in `bootstrap_ci`? Raise a `ValueError` — there is nothing to resample.
- What if `values` is empty in `summarise_metric`? Raise a `ValueError` — cannot compute mean/std/CI of empty input.
- What if `group_a` or `group_b` is a single-element list in `significance_test`? Return the test result as-is; Mann-Whitney handles singleton groups (may return p=1.0 or a defined degenerate result).
- What if `n_resamples=0` in `bootstrap_ci`? Raise a `ValueError`.
- What if `ci_level` is outside (0, 1) in `bootstrap_ci` or `summarise_metric`? Raise a `ValueError`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a `MultiSeedResult` data structure capturing: metric name, per-seed values list, mean, standard deviation, lower CI bound, upper CI bound, and CI confidence level (default 0.95).
- **FR-002**: The system MUST provide a `run_multi_seed` function that accepts a runner callable and a list of seed integers; invokes the runner once per seed passing the seed as its sole argument; and returns all returned episode records concatenated in call order, with each record's `seed` field set to the seed that produced it.
- **FR-003**: The system MUST provide a `bootstrap_ci` function that computes a non-parametric bootstrap confidence interval over a list of float values, with configurable confidence level (default 0.95), number of resamples (default 1000), and a deterministic RNG seed (default 0).
- **FR-004**: The system MUST provide a `significance_test` function that performs a two-sided non-parametric test comparing two groups of float values and returns a tuple of (p-value as float, is_significant as bool), where is_significant is True when p-value < 0.05.
- **FR-005**: The system MUST provide a `summarise_metric` function that accepts a metric name and a list of per-seed float values, computes the mean, standard deviation, and bootstrap CI, and returns a `MultiSeedResult`.
- **FR-006**: All five components (`MultiSeedResult`, `run_multi_seed`, `bootstrap_ci`, `significance_test`, `summarise_metric`) MUST be importable from a single module (`aatf.statistics`).
- **FR-007**: All functions MUST be deterministic: identical inputs and seeds MUST always produce identical outputs.
- **FR-008**: No function MUST perform file I/O, network calls, subprocess execution, or any operation with side effects.
- **FR-009**: `bootstrap_ci` MUST raise a clear error when given an empty values list or zero resamples.
- **FR-010**: `summarise_metric` MUST raise a clear error when given an empty values list.
- **FR-011**: `run_multi_seed` MUST tag each returned episode record with the seed used to produce it (by setting the `seed` field on each `EpisodeRecord`).

### Key Entities

- **MultiSeedResult**: Structured container for a metric computed across multiple seeds. Fields: `metric_name` (human-readable label), `values` (raw per-seed floats), `mean`, `std`, `ci_low`, `ci_high` (all floats), `ci_level` (float, default 0.95).
- **Runner callable**: A caller-supplied function with signature `(seed: int) -> list[EpisodeRecord]`. Not defined by this feature — this feature only invokes it.
- **Bootstrap sample**: A re-sample of size N drawn with replacement from the original values list, used to estimate the sampling distribution of the mean.
- **Significance test result**: A `(p_value: float, is_significant: bool)` tuple. `is_significant` is True when `p_value < 0.05` (fixed threshold, not configurable at this stage).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `run_multi_seed` called with N seeds invokes the runner exactly N times — verifiable by counting calls with a mock runner.
- **SC-002**: `bootstrap_ci` called twice with identical inputs and `rng_seed=0` returns identical `(ci_low, ci_high)` — verifiable by equality assertion.
- **SC-003**: `bootstrap_ci` with `ci_level=0.99` returns an interval at least as wide as the same call with `ci_level=0.90`, across any non-trivial input list.
- **SC-004**: `significance_test` on two clearly-separated groups (e.g. all-high vs all-low) returns `is_significant=True`; on two identical groups returns `is_significant=False`.
- **SC-005**: `summarise_metric` returns a `MultiSeedResult` where `ci_low ≤ mean ≤ ci_high` for any non-empty input list.
- **SC-006**: All five components are importable from `aatf.statistics` in a single import statement with no error.

## Assumptions

- **A1**: The runner callable passed to `run_multi_seed` is responsible for seeding all internal randomness using the provided integer seed. This feature only passes the seed; it does not enforce determinism inside the runner.
- **A2**: `run_multi_seed` sets the `seed` field on returned `EpisodeRecord` objects. Since `EpisodeRecord` is a frozen dataclass, this means replacing each record with a new `EpisodeRecord` where `seed` is overwritten with the actual seed used. Callers constructing records with `seed=0` (or any placeholder) will have their seed field correctly overwritten.
- **A3**: The significance threshold is fixed at `0.05`. Configurable thresholds are out of scope for this feature.
- **A4**: Bootstrap CI uses the percentile method (not BCa or bias-corrected). The percentile method is standard for this use-case and sufficient for Phase 1.
- **A5**: `scipy` is added to `requirements.in` as `scipy>=1.12` and pinned via pip-tools. The `scipy.stats.mannwhitneyu` function is used for the Mann-Whitney test with `alternative="two-sided"`.
- **A6**: The number of bootstrap resamples defaults to 1000, which is standard for scientific computing at this scale. Callers may override via `n_resamples`.

## Scope Boundaries

**In scope**: `MultiSeedResult` dataclass, `run_multi_seed`, `bootstrap_ci`, `significance_test`, `summarise_metric` — all importable from `aatf.statistics`. Adding `scipy>=1.12` to `requirements.in`.

**Out of scope**: Multi-process or parallel seed execution (F25), report generation (F24), explainability engine (F23), ground-truth validation harness (F22), BCa/bias-corrected bootstrap, configurable significance threshold, plotting or visualisation of distributions.
