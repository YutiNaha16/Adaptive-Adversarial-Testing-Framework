# Feature Specification: Reward Function

**Feature Branch**: `014-e4-reward-function`
**Created**: 2026-07-10
**Status**: Draft
**Input**: User description: "F14 — single authoritative reward computation for the RL attacker"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Detection Penalty (Priority: P1)

When an attack action fires an IDS alert (detected=True), the attacker receives a penalty of −1.0, regardless of whether the action made progress through the attack graph.

**Why this priority**: Detection is the worst outcome for the attacker — it is the primary signal that drives evasion learning. Getting this branch right first is essential.

**Independent Test**: Call `compute_reward(detected=True, stage_progress=False)` and `compute_reward(detected=True, stage_progress=True)` — both must return exactly −1.0.

**Acceptance Scenarios**:

1. **Given** an action was executed and detected by the IDS, **When** `compute_reward` is called with `detected=True`, **Then** the return value is exactly −1.0, regardless of the value of `stage_progress`.
2. **Given** an action both triggered an alert AND would have unlocked new attack stages, **When** `compute_reward` is called with `detected=True, stage_progress=True`, **Then** the return value is still −1.0 (detection takes priority).

---

### User Story 2 — Progress Reward (Priority: P2)

When an attack action evades detection AND unlocks at least one new action in the attack graph (stage_progress=True), the attacker receives a reward of +1.0.

**Why this priority**: This is the positive reinforcement signal that drives the attacker to advance through the kill chain while staying undetected — the core learning objective.

**Independent Test**: Call `compute_reward(detected=False, stage_progress=True)` — must return exactly +1.0.

**Acceptance Scenarios**:

1. **Given** an action was executed, evaded detection, and completing it unlocked new follow-on actions, **When** `compute_reward` is called with `detected=False, stage_progress=True`, **Then** the return value is exactly +1.0.

---

### User Story 3 — No-Progress Penalty (Priority: P3)

When an attack action evades detection but does NOT unlock any new actions (stage_progress=False), the attacker receives a small penalty of −0.1 to discourage stalling on already-known safe actions.

**Why this priority**: Without this penalty the attacker could exploit safe but dead-end actions indefinitely; the −0.1 discourages that without overwhelming the +1.0 progress signal.

**Independent Test**: Call `compute_reward(detected=False, stage_progress=False)` — must return exactly −0.1.

**Acceptance Scenarios**:

1. **Given** an action was executed, evaded detection, but did not unlock any new attack stages, **When** `compute_reward` is called with `detected=False, stage_progress=False`, **Then** the return value is exactly −0.1.

---

### Edge Cases

- Both `detected=True` and `stage_progress=True` simultaneously → −1.0 (detection always wins).
- The three branches are mutually exclusive and exhaustive — every valid (detected, stage_progress) pair maps to exactly one reward value.
- The reward values (−1.0, +1.0, −0.1) are fixed constants, not configurable at call time.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a single function `compute_reward(detected: bool, stage_progress: bool) -> float` as the sole location for Phase 1 reward computation.
- **FR-002**: `compute_reward` MUST return exactly −1.0 when `detected` is True, regardless of `stage_progress`.
- **FR-003**: `compute_reward` MUST return exactly +1.0 when `detected` is False and `stage_progress` is True.
- **FR-004**: `compute_reward` MUST return exactly −0.1 when `detected` is False and `stage_progress` is False.
- **FR-005**: The three reward branches MUST be mutually exclusive and exhaustive — every valid input pair produces exactly one output.
- **FR-006**: `compute_reward` MUST be a pure function: no I/O, no randomness, no side effects, no global state mutation.
- **FR-007**: The reward constants (REWARD_DETECTED, REWARD_PROGRESS, REWARD_STALL) MUST be exposed as named module-level constants so callers and logs can reference them by name.
- **FR-008**: The function MUST be unit-tested against worked examples for all three branches.

### Key Entities

- **RewardConstants**: Three named float constants — `REWARD_DETECTED = -1.0`, `REWARD_PROGRESS = +1.0`, `REWARD_STALL = -0.1` — exposed at module level.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `compute_reward(True, False)` and `compute_reward(True, True)` both return exactly −1.0.
- **SC-002**: `compute_reward(False, True)` returns exactly +1.0.
- **SC-003**: `compute_reward(False, False)` returns exactly −0.1.
- **SC-004**: All three branches verified by unit tests; all tests pass.
- **SC-005**: The reward function exists in exactly one file — no duplicate implementations anywhere in the codebase.

## Assumptions

- `stage_progress` is computed by the caller (feedback collector, F15) by comparing `attack_graph.available_actions(completed_before)` vs `attack_graph.available_actions(completed_after)` — the reward function itself receives only the pre-computed bool.
- Reward values are fixed for Phase 1; Phase 2 will extend (not replace) with an anomaly penalty term, but that is out of scope here.
- Return type is `float` (Python native), not numpy scalar — no numpy dependency needed.

## Dependencies

- **F03**: Core contracts (no direct runtime dependency; reward function is stdlib-only).
- **F09**: Attack graph (dependency is indirect — caller uses F09 to compute `stage_progress` before calling this function).
