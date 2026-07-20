# Feature Specification: Evaluator & Metrics (F20)

**Feature Branch**: `020-e6-evaluator-metrics`
**Created**: 2026-07-11
**Status**: Draft
**Epic**: E6 — Analysis, Explainability & Reporting

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Episode Record Contract (Priority: P1)

A researcher collects episode data during a run and stores it in a structured record for offline analysis. The `EpisodeRecord` captures everything needed to compute all four Phase 1 metrics: who ran (attacker class, seed), what happened step-by-step (action taken, detected, stage progress, reward), and whether the episode completed.

**Why this priority**: All four metric functions operate over lists of `EpisodeRecord`; without this contract being clear and stable, no downstream metric can be computed or tested. It is the foundation for US2, US3, and US4.

**Independent Test**: Construct `EpisodeRecord` objects by hand with known field values and verify they can be created, inspected, and passed into metric functions without error — without running the lab.

**Acceptance Scenarios**:

1. **Given** a completed episode with 3 steps (2 detected, 1 not), **When** an `EpisodeRecord` is constructed, **Then** it holds `attacker_class`, `seed`, `steps` (list of `StepRecord`), `total_reward`, `completed=True`, and `episode_index` without error.
2. **Given** an incomplete episode that hit the step limit, **When** an `EpisodeRecord` is constructed with `completed=False`, **Then** all fields are accessible and the record is valid.
3. **Given** zero steps (empty episode), **When** an `EpisodeRecord` is constructed, **Then** it is valid with an empty steps list.

---

### User Story 2 — Detection Rate (Priority: P2)

A researcher asks: "How often did the defence detect an attack step across all episodes?" They pass a list of episode records to `detection_rate` and receive a single float between 0.0 and 1.0.

**Why this priority**: Detection rate is the primary signal for evaluating whether a defence is effective and whether an attacker is evading. It is the denominator for Robustness Score and a component of Adaptation Gain.

**Independent Test**: Hand-craft episode records with known detected/undetected ratios and assert the returned value matches the expected fraction to within floating-point tolerance.

**Acceptance Scenarios**:

1. **Given** 10 steps across 2 episodes, all detected, **When** `detection_rate` is called, **Then** it returns `1.0`.
2. **Given** 10 steps across 2 episodes, none detected, **When** `detection_rate` is called, **Then** it returns `0.0`.
3. **Given** 4 steps detected out of 10, **When** `detection_rate` is called, **Then** it returns `0.4`.
4. **Given** an empty list of records, **When** `detection_rate` is called, **Then** it returns `0.0` (no steps → no detections).

---

### User Story 3 — Robustness Score & Adaptation Gain (Priority: P3)

A researcher asks two related questions:
- "Has the defence held up in recent episodes (steady-state)?" → `robustness_score`
- "How much better is the adaptive attacker compared to the baseline?" → `adaptation_gain`

Both answers come from slicing or comparing detection rates over specific subsets of episode records.

**Why this priority**: These two metrics directly answer whether the system achieves its steady-state target (robustness) and the central research question RQ1 (adaptation gain). They depend on US2's `detection_rate` being correct.

**Independent Test**: Craft two sets of episode records — one for a baseline (high detection rate) and one for a learner (lower detection rate over the last N episodes) — and verify both functions return the correct values.

**Acceptance Scenarios**:

1. **Given** 10 episodes total and `window=5`, **When** `robustness_score` is called, **Then** it returns the detection rate computed from only the last 5 episodes.
2. **Given** `window` larger than the number of records, **When** `robustness_score` is called, **Then** it uses all available records (no error, no truncation to zero).
3. **Given** baseline records with `detection_rate=0.8` and learner records with `detection_rate=0.5`, **When** `adaptation_gain` is called, **Then** it returns `30.0` (percentage points).
4. **Given** baseline and learner with equal detection rates, **When** `adaptation_gain` is called, **Then** it returns `0.0`.
5. **Given** a learner with a higher detection rate than baseline (learner is worse), **When** `adaptation_gain` is called, **Then** it returns a negative value.

---

### User Story 4 — Convergence Episodes (Priority: P4)

A researcher asks: "At which episode did the attacker start consistently evading the defence?" They call `convergence_episodes` with a detection-rate threshold and receive either the first episode index where evasion was sustained, or `None` if it never happened.

**Why this priority**: Convergence episodes measures learning speed — a key secondary metric for the Phase 1 gate. It depends on US2 and requires a clear trailing-window definition.

**Independent Test**: Create a sequence of episodes where detection rate is high early and drops below threshold from episode index 7 onward; verify `convergence_episodes` returns 7.

**Acceptance Scenarios**:

1. **Given** detection rate drops below `threshold=0.5` from episode 7 onward, **When** `convergence_episodes` is called, **Then** it returns `7`.
2. **Given** detection rate never drops below threshold, **When** `convergence_episodes` is called, **Then** it returns `None`.
3. **Given** detection rate drops below threshold immediately (episode 0), **When** `convergence_episodes` is called, **Then** it returns `0`.
4. **Given** detection rate briefly dips below threshold then rises back, **When** `convergence_episodes` is called, **Then** it returns the index of the first dip (earliest crossing, not the sustained one).
5. **Given** an empty list of records, **When** `convergence_episodes` is called, **Then** it returns `None`.

---

### Edge Cases

- What if `records` is empty for any metric function? Each function must handle this gracefully: `detection_rate([]) → 0.0`, `robustness_score([], window) → 0.0`, `adaptation_gain([], []) → 0.0`, `convergence_episodes([]) → None`.
- What if `window` exceeds the number of episodes in `robustness_score`? Use all available records without raising an error.
- What if `window=0` is passed to `robustness_score`? Treat as 0.0 (no episodes in window → no detections). Do not raise.
- What if an episode has zero steps? Its contribution to detection rate is zero detections added to the count, but the zero denominator is absorbed by the total step count across all records. If all records have zero steps, return 0.0.
- What if `adaptation_gain` receives one or both empty lists? Return 0.0.
- What is the trailing window size for `convergence_episodes`? Fixed at 5 episodes (assumption A3 below). Documented in spec; can be overridden by caller via optional parameter.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an `EpisodeRecord` data structure capturing: attacker class name (string), seed (integer), steps (ordered list of step records), total reward (float), completed (boolean), and episode index (integer).
- **FR-002**: Each step record within an `EpisodeRecord` MUST capture: action identifier (string), whether detection occurred (boolean), whether stage progress occurred (boolean), and the reward value (float). This shape MUST be compatible with the existing `StepRecord` from the episode loop (F16).
- **FR-003**: The system MUST provide a `detection_rate` function that accepts a list of episode records and returns the fraction of steps (across all records) where detection occurred, as a float in [0.0, 1.0].
- **FR-004**: The system MUST provide a `robustness_score` function that accepts a list of episode records and a window size, and returns the detection rate computed over only the last `window` episodes.
- **FR-005**: The system MUST provide an `adaptation_gain` function that accepts two lists of episode records (baseline and learner) and returns the difference in detection rates multiplied by 100, in percentage points. A positive result means the learner evades more than the baseline.
- **FR-006**: The system MUST provide a `convergence_episodes` function that accepts a list of episode records and a detection-rate threshold (default 0.5) and returns the episode index of the first episode where the trailing-window detection rate falls below the threshold, or `None` if it never does.
- **FR-007**: All four metric functions MUST be importable from a single module (`aatf.metrics`).
- **FR-008**: All four metric functions MUST be deterministic: identical inputs MUST always produce identical outputs.
- **FR-009**: No metric function MUST perform file I/O, network calls, subprocess execution, or any operation with side effects.
- **FR-010**: All metric functions MUST handle empty input gracefully without raising exceptions.
- **FR-011**: The `EpisodeRecord` structure MUST be importable from `aatf.metrics` (or re-exported from there) so callers need only one import.

### Key Entities

- **EpisodeRecord**: Represents one complete or partial attack episode. Fields: `attacker_class` (name of attacker policy used), `seed` (RNG seed for reproducibility), `steps` (ordered list of step records), `total_reward` (sum of per-step rewards), `completed` (whether all attack graph actions were exhausted), `episode_index` (position in the run sequence starting from 0).
- **StepRecord** (from F16, re-used): Represents one action taken in an episode. Fields: `action_id` (which attack action was chosen), `detected` (whether the defence raised an alert), `stage_progress` (whether the attack graph advanced), `reward` (computed reward for this step).
- **Metric Result**: A scalar float for `detection_rate`, `robustness_score`, `adaptation_gain`; an `int | None` for `convergence_episodes`. No wrapper type — raw Python scalars.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given a list of 1,000 episode records with a known fraction of detected steps, `detection_rate` returns the correct value to within ±1e-9 floating-point tolerance — verified with hand-crafted test data.
- **SC-002**: `robustness_score` with `window=W` returns the identical value as `detection_rate` applied to only the last `W` episodes — verifiable by constructing disjoint early and late record sets.
- **SC-003**: `adaptation_gain(baseline, learner)` returns a value in percentage points equal to `(detection_rate(baseline) - detection_rate(learner)) × 100` — verifiable with any hand-crafted pair of record lists.
- **SC-004**: `convergence_episodes` returns `None` when detection rate never crosses the threshold and returns the correct integer index when it does — verifiable without running the lab.
- **SC-005**: All four functions return identical results on repeated calls with the same input — verifiable by calling each function twice and asserting equality.
- **SC-006**: All four functions complete on lists of 10,000 episode records (each with up to 20 steps) without error and within a time budget acceptable for offline analysis (no performance target beyond "not slow").

## Assumptions

- **A1**: `StepRecord` from `aatf.episode` (F16) has exactly the fields: `action_id: str`, `detected: bool`, `stage_progress: bool`, `reward: float`. The `EpisodeRecord` in this feature wraps lists of these existing `StepRecord` objects rather than redefining the step shape.
- **A2**: `episode_index` reflects the position in the list passed to the function (0-based), not a globally unique episode ID across different runs. Callers are responsible for assigning consistent indices.
- **A3**: The trailing window size for `convergence_episodes` is fixed at 5 episodes by default. If fewer than 5 episodes have occurred up to the current index, use all available episodes up to that point.
- **A4**: `attacker_class` is the plain class name string (e.g., `"LinUCBAttacker"`), not a fully-qualified module path.
- **A5**: The `seed` field in `EpisodeRecord` is informational only — metric functions do not use it in any computation.

## Scope Boundaries

**In scope**: `EpisodeRecord` dataclass, four metric functions (`detection_rate`, `robustness_score`, `adaptation_gain`, `convergence_episodes`), all importable from `aatf.metrics`, with unit tests using hand-crafted data.

**Out of scope**: Multi-seed orchestration (F21), statistical confidence intervals and significance tests (F21), explainability engine (F23), report generation (F24), disk serialisation of episode logs (separate concern), visualisation, streaming / incremental computation, parallel execution of metric functions.
