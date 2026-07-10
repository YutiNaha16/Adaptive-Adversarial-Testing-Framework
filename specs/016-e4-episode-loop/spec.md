# Feature Specification: Episode Loop (F16)

**Feature Branch**: `016-e4-episode-loop`
**Created**: 2026-07-10
**Status**: Draft
**Epic**: E4 — Feedback Loop & Experiment Engine

## Overview

The episode loop is the central orchestrator of a single attack episode. It drives a repeating step cycle — selecting an action, executing it, measuring whether the defence detected it, updating the running episode record, and computing a reward — until the episode ends. The loop is the component that makes all the E4 pieces move together: action selection, action execution, detection, feedback, and reward all happen inside it. It returns a complete, structured record of everything that happened.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Single Step Execution (Priority: P1)

On each step, the loop must correctly orchestrate the full action → detect → feedback → reward sequence. The step record must capture exactly what happened so it can be used for learning and analysis.

**Why this priority**: A single correct step is the atomic unit of the loop. Every other story depends on steps being executed correctly. This is the MVP — a loop that can run one step correctly is already useful for debugging and integration testing.

**Independent Test**: Construct an episode with one available action, run the loop with stub dependencies returning known values, and inspect the returned step record and final episode state.

**Acceptance Scenarios**:

1. **Given** a fresh episode state with one reachable action, stub executor (no-op), and stub defence returning alert_fired=False, **When** the loop runs one step, **Then** the step record contains the correct action_id, detected=False, stage_progress matches the graph's reachability change, and reward=-0.1 (undetected, no further actions → no progress) or reward=+1.0 (undetected with progress).
2. **Given** a stub defence returning alert_fired=True, **When** the loop runs one step, **Then** the step record contains detected=True and reward=-1.0 (detection penalty).
3. **Given** any episode, **When** a step executes, **Then** the episode state's step counter, alert_history, detection_history, and completed_actions are all updated with values consistent with the action taken.

---

### User Story 2 — Episode Termination: All Actions Exhausted (Priority: P2)

When the attack graph has no more reachable actions (all reachable attack steps completed), the episode must end immediately and return a result flagged as complete.

**Why this priority**: This is the "attacker won" scenario — the attacker completed all available attack stages. Correctly detecting this terminal state is essential for the RL reward signal and for reporting on attacker coverage.

**Independent Test**: Configure a one-action episode where completing that action leaves no successors. Verify the loop terminates after exactly one step with completed=True.

**Acceptance Scenarios**:

1. **Given** a fresh episode with one entry-point action that has no successors, **When** the loop runs, **Then** exactly one step executes, the episode terminates with completed=True.
2. **Given** an episode where episode_state.completed_actions already covers all reachable actions, **When** the loop starts, **Then** zero steps execute and the loop terminates immediately with completed=True.

---

### User Story 3 — Episode Termination: Step Limit Reached (Priority: P3)

When the episode reaches the maximum number of steps without exhausting all actions, the episode must end and return a result flagged as incomplete.

**Why this priority**: The step limit prevents unbounded episodes and keeps experiments time-bounded. Without this safeguard, an episode could loop indefinitely if the attack graph has cycles or the attacker revisits actions.

**Independent Test**: Set max_steps=2 with a graph that has more than 2 reachable actions. Verify the loop terminates after exactly 2 steps with completed=False.

**Acceptance Scenarios**:

1. **Given** a max_steps=3 limit and more than 3 reachable actions, **When** the loop runs, **Then** exactly 3 steps execute and the episode terminates with completed=False.
2. **Given** max_steps=0, **When** the loop starts, **Then** zero steps execute and the episode terminates immediately with completed=False.

---

### User Story 4 — Cumulative Episode Result (Priority: P4)

The returned episode result must accurately summarise the entire episode: every step's record, the total accumulated reward, and the final episode state.

**Why this priority**: The episode result is what the RL policy update and the experiment logger will consume. An inaccurate total_reward or missing step record would corrupt learning and reporting.

**Independent Test**: Run a 3-step episode with known rewards per step (-1.0, +1.0, -0.1) and verify total_reward == -0.1, steps list has 3 entries, and episode_state.step == 3.

**Acceptance Scenarios**:

1. **Given** a 3-step episode with rewards [-1.0, +1.0, -0.1], **When** the loop completes, **Then** total_reward == -0.1 (sum) and len(steps) == 3.
2. **Given** a zero-step episode (immediate termination), **When** the loop returns, **Then** total_reward == 0.0 and steps is an empty list.
3. **Given** any episode, **When** the loop completes, **Then** episode_state.step equals len(steps).

---

### Edge Cases

- What if max_steps=0? The loop checks the step limit before running any steps — zero steps execute, completed=False.
- What if the episode_state already has some completed_actions on entry (partial resume)? Available actions are computed from the current state — the loop continues from where it left off.
- What if the action selector raises an exception? The exception propagates up — the loop does not catch it.
- What if the defence system returns category=None? The category is passed through to the feedback collector, which handles None silently (no fired_categories update).
- What if two termination conditions are both true (no actions AND step >= max_steps)? The "no available actions" check takes priority (completed=True).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST check for available attack actions at the start of each step; if none exist, it MUST terminate the episode with completed=True.
- **FR-002**: The system MUST check the step counter against the step limit at the start of each step; if the limit is reached, it MUST terminate with completed=False.
- **FR-003**: The "no available actions" check MUST take priority over the step-limit check.
- **FR-004**: The system MUST invoke the provided action selector with the list of currently available actions and the current episode state to choose the next action.
- **FR-005**: The system MUST invoke the provided action executor with the chosen action identifier to simulate executing the attack.
- **FR-006**: The system MUST obtain a detection result (alert fired flag and optional alert category) from the provided defence system for the action just executed.
- **FR-007**: The system MUST update the episode state in-place using the feedback collector after each step.
- **FR-008**: The system MUST compute a scalar reward for each step using the reward function.
- **FR-009**: The system MUST record every step's action identifier, detection result, stage progress flag, and reward in a step record.
- **FR-010**: The system MUST accumulate the total reward across all steps.
- **FR-011**: The system MUST return a result containing: the final episode state, the list of all step records, the total accumulated reward, and the completion flag.
- **FR-012**: The system MUST NOT perform any file I/O, network access, or database operations.
- **FR-013**: The system MUST NOT introduce any randomness of its own — all non-determinism is the action selector's responsibility.
- **FR-014**: The action selector, action executor, and defence system MUST all be accepted as parameters so they can be replaced with stubs in unit tests.
- **FR-015**: The attack graph and step limit MUST be overridable via optional parameters, defaulting to the canonical project values.

### Key Entities

- **EpisodeResult**: Immutable summary of a completed episode — contains the final episode state, ordered list of step records, cumulative reward, and a boolean indicating whether all available actions were completed.
- **StepRecord**: Immutable record of one step — the action taken, whether it was detected, whether it advanced the attack graph, and the reward received.
- **EpisodeState**: Mutable running record of episode progress (from F13) — mutated in-place by the feedback collector during each step.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A 3-step episode with known stub inputs produces exactly 3 step records with correct action_id, detected, stage_progress, and reward values — verified by unit test with no tolerance.
- **SC-002**: An episode that exhausts all available actions terminates with completed=True and a steps list whose length equals the number of available actions — verified by unit test.
- **SC-003**: An episode that hits max_steps=3 terminates with exactly 3 step records and completed=False — verified by unit test.
- **SC-004**: total_reward in EpisodeResult equals the arithmetic sum of all individual step rewards to floating-point precision — verified by unit test with abs tolerance < 1e-9.
- **SC-005**: A zero-step episode (max_steps=0 or no available actions at start) returns total_reward=0.0 and an empty steps list — verified by 2 distinct unit tests.

## Assumptions

- The Defence interface exposes a `detect(action_id: str) -> tuple[bool, str | None]` method returning `(alert_fired, category)`. Category is None when the alert category cannot be determined.
- The action selector signature is `(available: list[str], episode_state: EpisodeState) -> str`. It is the caller's responsibility to return a valid action_id from the available list.
- The action executor signature is `(action_id: str) -> None`. It is a side-effect-only call — F16 does not use its return value.
- `MAX_STEPS` defaults to the value defined in `context_vector.py` (currently 100).
- EpisodeState is not copied by the loop — the caller passes in a state and receives it back mutated. This allows the caller to inspect the state after episode completion.

## Dependencies

- **F03** (Core Contracts): Defence interface definition
- **F09** (Attack Graph): `ATTACK_GRAPH` default + `available_actions()` for step termination check
- **F13** (Context Vector): `EpisodeState`, `MAX_STEPS`
- **F14** (Reward Function): `compute_reward(detected, stage_progress)` called each step
- **F15** (Feedback Collector): `collect_feedback(episode_state, action_id, alert_fired, ...)` called each step

## Scope Boundaries

The following are explicitly out of scope for this feature:

- RL policy updates — the attacker learning rule (F17+)
- Writing episode logs to disk or any file (F19+)
- Running multiple episodes or an experiment harness (F20+)
- Actual lab traffic generation — the action executor is injected by the caller (F11)
- Context vector construction — available via `build_context` from F13 but not called by the loop itself
