# Feature Specification: Attacker Update Rule — LinUCB (F17)

**Feature Branch**: `017-e4-attacker-update`
**Created**: 2026-07-10
**Status**: Draft
**Epic**: E4 — Feedback Loop & Experiment Engine

## Overview

The attacker update rule is the learning engine that makes the attacker adaptive. After each episode step the attacker observes whether it was detected and whether it made progress, then updates its internal model so it can make better choices in future episodes. The model maintains a separate belief for each attack action — how rewarding that action tends to be given the current situation — and balances exploiting known-good actions with exploring unfamiliar ones. Over many episodes it converges on the attack sequence that best evades the defence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Parameter Update After a Step (Priority: P1)

After each episode step the attacker receives a reward signal and must update its internal belief about the action it just took, given the situation it observed. The updated belief must be mathematically exact — there must be no accumulated error from repeated updates.

**Why this priority**: Correctness of the update is the foundation of the entire learning system. If the belief update is wrong, the attacker's preferences drift away from reality over time, making every downstream signal and metric untrustworthy.

**Independent Test**: Construct a model with known initial beliefs, call `update()` with a known context observation and reward, and verify the resulting beliefs match hand-computed expected values to floating-point precision.

**Acceptance Scenarios**:

1. **Given** a freshly initialised model with one known action, a known context observation, and a known reward, **When** `update()` is called once, **Then** the internal belief matrices for that action match the analytically computed expected values to within floating-point machine epsilon.
2. **Given** a model that has been updated repeatedly with the same context and the same positive reward, **When** `select_action()` is called with that action available, **Then** the model consistently selects that action over an untrained alternative — confirming that repeated positive observations strengthen the preference.
3. **Given** a model updated with positive reward on action A and negative reward on action B, **When** `select_action()` is called with both available, **Then** action A is preferred — demonstrating that the model has correctly learned which action is more rewarding.

---

### User Story 2 — Action Selection Under Uncertainty (Priority: P2)

When the attacker must choose the next action, it selects the one with the highest score — balancing the expected reward with a confidence bonus that favours actions whose beliefs are still uncertain. A tunable coefficient controls how much the attacker explores unfamiliar actions versus exploiting known-good ones.

**Why this priority**: The selection rule is what the episode loop calls every step. Getting it correct is a prerequisite for the attacker learning anything useful. The exploration-exploitation balance directly determines how quickly the attacker finds evasive attack paths.

**Independent Test**: Construct a model with known belief parameters for two actions; manually compute the expected scores; verify `select_action()` returns the action with the higher score. Also verify that when scores are equal, the alphabetically first action is always returned.

**Acceptance Scenarios**:

1. **Given** a model with known parameters for two available actions and a known context, **When** `select_action()` is called, **Then** the returned action_id matches the one whose score is analytically highest.
2. **Given** a model where two actions produce identical scores for a given context, **When** `select_action()` is called, **Then** the alphabetically first action_id is always returned — the tie-break is deterministic and independent of parameter order.
3. **Given** an exploration coefficient of zero, **When** `select_action()` is called, **Then** the result is identical to pure greedy selection (only expected reward matters; the uncertainty bonus contributes nothing).

---

### User Story 3 — State Export and Restore (Priority: P3)

The model's learned parameters must be exportable as plain data so they can be saved to a run manifest, inspected, and restored. A restored model must produce identical scores to the original.

**Why this priority**: Run manifests are required for reproducibility (Constitution Principle II). Without serialisable state, a learned model cannot be checkpointed or replicated across runs.

**Independent Test**: Train a model for several steps, export its state, reconstruct from the export, and verify the reconstructed model produces identical `select_action()` outputs for the same context.

**Acceptance Scenarios**:

1. **Given** a trained model with non-trivial beliefs, **When** the state is exported, **Then** the export contains only standard, human-readable data — verifiable by passing it through a JSON serialiser without error.
2. **Given** an exported state, **When** the model is reconstructed from it, **Then** the reconstructed model produces the same scores for every available action as the original, for any context input.
3. **Given** a freshly initialised model (no updates), **When** a round-trip export + reconstruct is performed, **Then** the reconstructed model behaves identically to a newly created model with the same settings.

---

### Edge Cases

- What if `update()` is called for an action that has not been seen before? The model initialises beliefs for that action on-the-fly before updating — no explicit pre-registration needed.
- What if `select_action()` encounters an action whose beliefs have not been initialised? It treats the action with neutral initial beliefs (unlearned), giving it a high uncertainty bonus that encourages early exploration.
- What if `select_action()` is called with a list containing a single action? That action is always returned regardless of its score.
- What if `select_action()` is called with an empty list? This is a caller error — the episode loop is responsible for ensuring the list is non-empty before calling.
- What if the exploration coefficient is zero? Selection reduces to pure greedy; the uncertainty bonus contributes zero.
- What if `update()` is called multiple times with zero reward? The belief converges toward zero reward for that action, and the model naturally shifts attention to other actions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST maintain a separate belief record for each action it has encountered, created on first reference.
- **FR-002**: Each belief record MUST consist of two components: a square matrix capturing accumulated observations and a vector capturing accumulated reward signal, both with dimension equal to the context vector.
- **FR-003**: Both components MUST be initialised to neutral starting values (identity matrix and zero vector) when a new action is first referenced.
- **FR-004**: The system MUST provide an `update(action_id, context, reward)` operation that revises the belief record for the given action using the provided context observation and reward.
- **FR-005**: The belief update MUST be mathematically exact — repeated updates with known inputs must match analytically computed results to floating-point precision, with no accumulated rounding drift beyond machine epsilon.
- **FR-006**: The system MUST provide a `select_action(available, context)` operation that scores every action in the available list and returns the identifier of the highest-scoring one.
- **FR-007**: The score for each action MUST combine the expected reward (derived from accumulated beliefs) with an uncertainty bonus scaled by the exploration coefficient.
- **FR-008**: When two or more actions produce equal scores, the system MUST return the alphabetically first identifier — the tie-break MUST be deterministic.
- **FR-009**: The exploration coefficient MUST be a configurable parameter with a default value of 1.0, injectable at construction time.
- **FR-010**: The system MUST allow initial belief values to be overridden at construction time, so tests can control starting conditions precisely.
- **FR-011**: The system MUST provide a `to_dict()` method that exports the complete model state as a dictionary containing only standard Python types (no framework-specific objects).
- **FR-012**: The system MUST provide a `from_dict(d)` class-level factory that reconstructs a model producing scores identical to those of the model that generated `d`.
- **FR-013**: The system MUST NOT perform any file I/O, network access, or database operations.
- **FR-014**: The system MUST NOT introduce any randomness — scores are deterministic functions of the beliefs and the context.

### Key Entities

- **LinUCBModel**: The learned belief model. Holds a belief record per encountered action and an exploration coefficient. Exposes `update()`, `select_action()`, `to_dict()`, and `from_dict()`.
- **Belief Record**: Per-action learned state — an accumulated-observation matrix and an accumulated-reward vector. Created with neutral initial values on first reference to a new action identifier.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After one `update()` call with a known context and reward, both belief components match hand-computed expected values with absolute error < 1 × 10⁻⁹ — verified by unit test against analytic ground truth.
- **SC-002**: `select_action()` returns the correct action in a two-action scenario with known belief parameters and known context — verified by unit test comparing against a manually computed score.
- **SC-003**: Alphabetical tie-breaking holds — a unit test where two actions produce identical scores must always return the alphabetically first one.
- **SC-004**: `to_dict()` output passes a standard JSON serialiser without error — zero tolerance: any non-serialisable object is a failure.
- **SC-005**: A round-trip export + reconstruct produces `select_action()` outputs identical to the original for all available actions and any test context — verified by unit test with exact equality.
- **SC-006**: After at least 5 updates strongly favouring one action (high positive reward) and zero updates on a second action, `select_action()` consistently returns the trained action — verified by unit test with known parameters.

## Assumptions

- The context vector dimension `d` is fixed at model construction and equals the output length of `build_context()` from F13. The caller is responsible for consistency; the model does not auto-detect or validate `d`.
- Belief records are initialised lazily (on first reference to a new action_id), not eagerly at construction — the full action list need not be known at construction time.
- The `from_dict()` factory is a class-level method — it does not require an existing model instance.
- `select_action()` with an empty list is a contract violation by the caller; behaviour is undefined and no guarantee is made.

## Dependencies

- **F13** (Context Vector): defines `build_context()` — the output dimension `d` is the model's context dimension
- **numpy**: matrix and vector operations (already in project requirements)

## Scope Boundaries

The following are explicitly out of scope for this feature:

- Wiring the model into the episode loop (that integration is F20+)
- Serialising the model to disk or reading it from a file (F19+)
- Q-learning comparison attacker (F21+)
- Phase 2 DQN attacker (Phase 2)
- Hyperparameter search or automatic tuning of the exploration coefficient
