# Research: Evaluator & Metrics (F20)

**Date**: 2026-07-11
**Feature**: 020-e6-evaluator-metrics

## Decision 1: EpisodeRecord as a frozen dataclass

**Decision**: Use `@dataclass(frozen=True)` with `steps: list[StepRecord]` (not a tuple).

**Rationale**: Matches the existing pattern in `aatf/episode.py` (`EpisodeResult` is also `frozen=True` with `steps: list[StepRecord]`). Frozen prevents field reassignment, which is sufficient immutability for the metrics use-case. Consumers should not mutate the steps list; no defensive copy is needed at construction time.

**Alternatives considered**: `@dataclass(frozen=True)` with `steps: tuple[StepRecord, ...]` — would give full deep immutability and allow hashing, but the spec says "list of StepRecord" and forcing tuple would break callers who construct records from episode loop output (which yields a list). Pydantic V2 `BaseModel` — available in the venv but adds overhead; the goal is a lightweight data-holder, not a validated model.

## Decision 2: StepRecord import — re-use from aatf.episode, do not redefine

**Decision**: `from aatf.episode import StepRecord`; no copy or re-export.

**Rationale**: `StepRecord` is already defined and tested as part of F16. Redefining it here would create two incompatible types with identical fields; callers would have to cast. Re-exporting from `aatf.metrics` would add public surface without value. The dependency is safe: `aatf.episode` has no transitive dependency on `aatf.metrics`, so there is no circular import.

**Alternatives considered**: Redefine `StepRecord` in `aatf.metrics` — rejected (type mismatch, code duplication). Define an independent `Step` named tuple — rejected (breaks duck-typing with existing episode loop output).

## Decision 3: detection_rate denominator — total steps, not total episodes

**Decision**: `detection_rate = sum(detected steps across all episodes) / sum(all steps across all episodes)`.

**Rationale**: A metric computed per-episode then averaged would be distorted by episodes of different lengths (a 1-step episode and a 20-step episode would be weighted equally). The step-weighted mean reflects the true fraction of steps that triggered detection, which is the scientifically correct quantity for measuring defence coverage.

**Alternatives considered**: `mean(episode-level detection rate)` — rejected; distorted by unequal episode lengths.

## Decision 4: robustness_score window semantics — last-N by list position

**Decision**: `records[-window:]` selects the last `window` episodes by their position in the input list. If `window > len(records)`, Python slice `records[-window:]` naturally returns all records (no IndexError). If `window <= 0`, return `0.0` (no episodes in window).

**Rationale**: The input list is assumed to be ordered by episode occurrence (callers are responsible). Slicing from the tail is O(1) in Python (list slice creates a view reference). Special-casing `window > len` is not needed — Python handles it correctly.

**Analytic verification**: `records = [ep0, ep1, ep2, ep3, ep4]` (5 records). `window=20` → `records[-20:]` = all 5 records. ✓

## Decision 5: adaptation_gain sign convention — positive = learner evades more

**Decision**: `adaptation_gain = (detection_rate(baseline) - detection_rate(learner)) × 100`. Positive value means the learner has a lower detection rate (evades more). Negative value means the learner performs worse than baseline.

**Rationale**: Matches the constitution §VI ("Adaptation Gain") definition and RQ1 direction: we want to show LinUCB achieves *lower* detection rate than baselines. A positive gain = improvement. This is consistent with the Phase 1 gate criterion ("Adaptation Gain ≥ 15 percentage points").

**Analytic ground truths**:
- `dr(baseline)=0.80`, `dr(learner)=0.50` → gain = 30.0 pp ✓
- `dr(baseline)=0.50`, `dr(learner)=0.50` → gain = 0.0 pp ✓
- `dr(baseline)=0.30`, `dr(learner)=0.60` → gain = -30.0 pp (learner worse) ✓

## Decision 6: convergence_episodes algorithm — sliding trailing window

**Decision**: Scan records by list position `i` (0-based). At position `i`, compute `detection_rate(records[max(0, i-window+1) : i+1])`. If the result is strictly less than `threshold`, return `records[i].episode_index`. If no such position exists, return `None`.

**Rationale**: "Convergence" means the attacker has *sustained* evasion for at least `window` consecutive episodes — not just a lucky single episode. A trailing sliding window captures this. We return the *first* episode index where the trailing window drops below threshold (earliest convergence).

**Edge-case verification**:
- `window=5`, episodes 0–9, each 1 step. Episodes 0,1 detected=True; episodes 2–9 detected=False.
  - `i=0`: `records[0:1]` = [True], dr=1.0 ≥ 0.5
  - `i=1`: `records[0:2]` = [T,T], dr=1.0 ≥ 0.5
  - `i=2`: `records[0:3]` = [T,T,F], dr=2/3 ≈ 0.67 ≥ 0.5
  - `i=3`: `records[0:4]` = [T,T,F,F], dr=2/4 = 0.5 — NOT strictly < 0.5
  - `i=4`: `records[0:5]` = [T,T,F,F,F], dr=2/5 = 0.4 < 0.5 → return `records[4].episode_index = 4`
- Immediate (i=0): first step not detected, threshold=0.5 → dr=0.0 < 0.5 → return `records[0].episode_index = 0`
- Never: all detected → dr always = 1.0, never < 0.5 → return None
- Empty: no iterations → return None immediately

**Alternatives considered**: "first episode where single-episode dr < threshold" (no trailing window) — rejected; would trigger on any lucky single undetected step, not genuine sustained convergence. Window of N most-recent episodes (step-weighted) — chosen approach.

## Decision 7: window=3 for convergence contracts (not 5)

**Decision**: Use `window=3` in convergence_episodes test contracts to keep test fixtures small (3–5 episodes each).

**Rationale**: The default `window=5` is correct for production use, but contracts need analytic ground truths. Using `window=3` allows 5-episode fixtures with tractable hand-verification. The parameter is explicitly injectable so any window is testable.

**Analytic ground truth for C-012** (`window=3`, episodes 0–4, 1 step each, ep0/ep1 detected=True, ep2–4 detected=False, threshold=0.5):
- i=0: records[0:1], dr=1.0 ≥ 0.5
- i=1: records[0:2], dr=1.0 ≥ 0.5
- i=2: records[0:3] = [T,T,F], dr=2/3 ≈ 0.67 ≥ 0.5
- i=3: records[1:4] = [T,F,F], dr=1/3 ≈ 0.33 < 0.5 → return `records[3].episode_index = 3`

## Decision 8: module layout — single file src/aatf/metrics.py

**Decision**: All entities and functions in one file: `src/aatf/metrics.py`. `EpisodeRecord` importable from `aatf.metrics`; re-export `StepRecord` from `aatf.episode` is NOT done (callers who need both import from both modules).

**Rationale**: Four pure functions + one dataclass. Total estimated LOC ≈ 45 lines. A single file is readable and avoids unnecessary module fragmentation. `StepRecord` is owned by `aatf.episode`; re-exporting would obscure its origin.

**Alternatives considered**: Separate `aatf/episode_record.py` for the dataclass — over-engineered for this size. `aatf/evaluator.py` — naming inconsistency with the spec (spec says `aatf.metrics`).
