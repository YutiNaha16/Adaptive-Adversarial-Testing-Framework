# Feature Specification: Feedback Collector (F15)

**Feature Branch**: `015-e4-feedback-collector`
**Created**: 2026-07-10
**Status**: Draft
**Epic**: E4 — Feedback Loop & Experiment Engine

## Overview

After each attack action runs inside an episode, the system must record what happened and decide whether the attacker made progress. This component — the feedback collector — is the bridge between "the action ran" and "here is what the reward function needs." It takes the detection outcome, updates the running episode record, and returns a compact result that the reward function can consume directly.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Episode State Recording (Priority: P1)

After an action completes, the episode's running record must be updated with the outcome. The RL loop cannot compute a meaningful reward or context vector without this up-to-date history.

**Why this priority**: Every other component in E4 (context vector, reward, episode loop) depends on EpisodeState being correctly updated. Without reliable mutation, no downstream signal is trustworthy.

**Independent Test**: Construct a fresh episode state, call the feedback collector with known inputs, then inspect each mutated field directly.

**Acceptance Scenarios**:

1. **Given** a fresh episode state with empty histories, **When** the feedback collector is called with action "recon-syn-scan" and alert_fired=True, **Then** alert_history contains [True], detection_history["recon-syn-scan"] contains [True], completed_actions contains "recon-syn-scan", and step equals 1.
2. **Given** an episode state where "recon-syn-scan" was already recorded once, **When** the feedback collector is called again with alert_fired=False, **Then** detection_history["recon-syn-scan"] contains [True, False] and alert_history has grown by 1.
3. **Given** any episode state, **When** the feedback collector is called, **Then** step is incremented by exactly 1 — no more, no less.

---

### User Story 2 — Stage Progress Detection (Priority: P2)

After an action completes, the system must determine whether that action unlocked at least one new attack step that was not reachable before. This boolean is the direct input to the reward function's progress branch.

**Why this priority**: The distinction between "made progress" and "stalled" drives the RL reward signal. Incorrect stage progress detection directly corrupts learning.

**Independent Test**: Use a minimal attack graph (e.g., A → B → C) and verify that completing A reports stage_progress=True (B is newly reachable), while completing a terminal node reports stage_progress=False.

**Acceptance Scenarios**:

1. **Given** an episode where no actions are completed and "recon-syn-scan" is an entry point with successors, **When** the feedback collector records "recon-syn-scan", **Then** stage_progress=True (new actions are now reachable).
2. **Given** an episode where all successors of "lateral-move-smb" are already completed, **When** the feedback collector records "lateral-move-smb", **Then** stage_progress=False (no new actions unlocked).
3. **Given** an action that has no successors in the attack graph, **When** the feedback collector records it, **Then** stage_progress=False.

---

### User Story 3 — Alert Category Tracking (Priority: P3)

When an alert fires and the caller knows which IDS rule category triggered it, the episode state must track that category. This enriches the context vector's rule-category slice (F13) and supports post-episode analysis.

**Why this priority**: Enhances observability of the attacker's detection signature. Optional input (category may be unknown), so it does not block the core feedback path.

**Independent Test**: Call the feedback collector with alert_fired=True and a known category string; verify the category appears in fired_categories. Call with category=None or alert_fired=False; verify fired_categories is not modified.

**Acceptance Scenarios**:

1. **Given** an episode with empty fired_categories, **When** the feedback collector is called with alert_fired=True and category="ET SCAN", **Then** fired_categories contains "ET SCAN".
2. **Given** any episode state, **When** the feedback collector is called with alert_fired=False and category="ET SCAN", **Then** fired_categories is NOT updated (no alert, no category recorded).
3. **Given** any episode state, **When** the feedback collector is called with alert_fired=True and category=None (unknown), **Then** fired_categories is NOT updated.

---

### Edge Cases

- What if action_id is already in completed_actions before the call? Set semantics apply — it is added again (no-op for the set), but detection_history and alert_history still grow by one entry for this execution.
- What if detection_history has no prior entries for action_id? The system initialises a new list for that action and appends the first result.
- What if the episode step counter is already at the maximum? The step is incremented unconditionally; clamping to display range is the context vector's responsibility, not the feedback collector's.
- What if the attack graph has no edges for the given action_id? stage_progress=False — no successors means no new reachability.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept an episode state, an action identifier, a detection flag, and optionally an attack graph and an alert category as inputs.
- **FR-002**: The system MUST append the detection flag to the episode's alert timeline on every call.
- **FR-003**: The system MUST append the detection flag to the per-action detection record for the given action identifier.
- **FR-004**: The system MUST mark the action identifier as completed in the episode state.
- **FR-005**: The system MUST increment the episode step counter by exactly 1 on every call.
- **FR-006**: The system MUST determine whether completing this action unlocked at least one new action that was not reachable before the call, using the attack graph.
- **FR-007**: The system MUST return a result containing the detection flag and the computed stage progress flag.
- **FR-008**: The system MUST add the alert category to the episode's fired-categories set if and only if both the detection flag is True AND a category was provided (not None/absent).
- **FR-009**: The system MUST perform all mutations before computing stage progress (so the newly completed action is included in reachability).
- **FR-010**: The system MUST NOT perform any I/O, network calls, or file system access.
- **FR-011**: The attack graph parameter MUST default to the canonical project attack graph when not supplied by the caller.

### Key Entities

- **EpisodeState**: Mutable running record of a single attack episode. Holds alert timeline, per-action detection history, completed-action set, step counter, start time, and fired IDS categories.
- **FeedbackResult**: Immutable pair of (detected: bool, stage_progress: bool) returned by the feedback collector and consumed by the reward function.
- **AttackGraph**: Directed graph of attack stages. Used to compute which actions become reachable after the current action completes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 5 EpisodeState fields (alert_history, detection_history, completed_actions, step, fired_categories) are updated with correct values on every call — verified by unit test inspection of each field independently.
- **SC-002**: Stage progress is correctly True for ≥1 graph position that has successors, and correctly False for ≥1 terminal or already-completed position — verified by distinct unit tests.
- **SC-003**: Alert category tracking correctly adds to fired_categories for alert_fired=True+category-present, and skips for alert_fired=False or category=None — verified by 3 distinct unit tests (US3 scenarios).
- **SC-004**: The feedback function completes in under 1 millisecond per call with the default attack graph (pure in-memory computation, no I/O).
- **SC-005**: 100% of all state mutation tests pass with no side effects observed on any object other than the episode state passed in.

## Assumptions

- `stage_progress` is computed by comparing `attack_graph.available_actions(completed_before)` vs `attack_graph.available_actions(completed_after)`. The current action is added to `completed_actions` first, then reachability is checked so the graph can resolve the full successor set correctly.
- The caller (episode loop, F16) is responsible for reading `eve.json` and translating Suricata alerts into the `alert_fired` boolean and optional `category` string before calling `collect_feedback`.
- `FeedbackResult` is a plain, immutable value object — no validation, no methods beyond field access.
- Detection history records individual execution results (list of bools per action), not aggregates. Aggregation (e.g., detection rate) is the context vector's job (F13).

## Dependencies

- **F03** (Core Contracts): Action type definitions
- **F09** (Attack Graph): `ATTACK_GRAPH` default + `available_actions()` method for stage progress
- **F13** (Context Vector): Defines `EpisodeState` — F15 mutates it in-place
- **F14** (Reward Function): `FeedbackResult` fields feed directly into `compute_reward(detected, stage_progress)`

## Scope Boundaries

The following are explicitly out of scope for this feature:

- Reading Suricata `eve.json` or any file (F16/F11 responsibility)
- Calling `compute_reward` (F14 responsibility — F15 returns its inputs, not the reward value)
- Computing the context vector (F13 responsibility)
- Managing episode termination or episode loop logic (F16 responsibility)
- RL policy updates (F17+)
