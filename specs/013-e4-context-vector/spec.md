# Feature Specification: Context Vector Builder

**Feature Branch**: `013-e4-context-vector`
**Created**: 2026-07-10
**Status**: Draft
**Input**: User description: "F13 — pure deterministic function producing the full RL attacker observation at each episode step"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Entry-Point Observation (Priority: P1)

The experiment loop needs a minimal but valid context vector at the very start of an episode (step 0, no actions completed, no alerts fired yet) so the RL attacker can make its first action choice.

**Why this priority**: Every episode starts here. If this fails, nothing else runs.

**Independent Test**: Call `build_context` with a fresh `EpisodeState` (step=0, no completed actions, no detection history, no fired categories) and verify the returned array has the correct fixed length, correct dtype (float32), and expected zero values for all slots.

**Acceptance Scenarios**:

1. **Given** a fresh EpisodeState with step=0, empty completed set, empty detection history, empty fired categories, **When** `build_context` is called, **Then** it returns a float32 array of length CONTEXT_DIM=50 with all slots 0.0 except timing[0]=0.0 and timing[1]=0.0.
2. **Given** the same fresh EpisodeState called twice, **When** `build_context` is called both times, **Then** both arrays are bitwise identical.

---

### User Story 2 — Attack Progress & Technique History (Priority: P2)

After some actions have been executed, the context vector must accurately reflect which actions are completed and what their per-technique detection rates are, so the RL agent can learn which techniques evade detection.

**Why this priority**: This is the core signal the agent uses to learn evasion.

**Independent Test**: Construct an EpisodeState with 3 completed actions (tcp_port_scan detected twice out of two, ssh_brute_force undetected once, http_dir_scan detected once out of one), call `build_context`, verify attack_progress flags for those 3 are 1.0 and technique_history rates match.

**Acceptance Scenarios**:

1. **Given** an EpisodeState where `tcp_port_scan` was executed 3 times (detected 2, undetected 1), **When** `build_context` is called, **Then** the technique_history slot for tcp_port_scan equals 2/3 ≈ 0.6667 (float32).
2. **Given** an EpisodeState where `ssh_brute_force` is in completed_actions, **When** `build_context` is called, **Then** the attack_progress flag for ssh_brute_force is 1.0 and all 14 other action flags are 0.0.
3. **Given** an EpisodeState where action `dns_exfil` has never been executed, **When** `build_context` is called, **Then** the technique_history slot for dns_exfil is 0.0 (no NaN, no error).

---

### User Story 3 — Alert History & Rule Category Signals (Priority: P3)

The rolling alert window and rule-category flags give the agent short-term memory of recent detection events and knowledge of which IDS rule classes are active.

**Why this priority**: Adds temporal context on top of the stateless progress signals; enriches the observation but is not required for basic learning.

**Independent Test**: Construct an EpisodeState with a specific alert history sequence and two fired categories, call `build_context`, verify the alert_history slots and category flags match.

**Acceptance Scenarios**:

1. **Given** a step-level alert history of [detected, undetected, detected] (3 steps) and window N=10, **When** `build_context` is called, **Then** alert_history slots are [1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] (most-recent-last, zero-padded at front).
2. **Given** EpisodeState with fired_categories={ET SCAN, ET DNS}, **When** `build_context` is called, **Then** exactly the ET SCAN and ET DNS category flags are 1.0 and all other 6 category flags are 0.0.
3. **Given** EpisodeState with an unknown category string in fired_categories, **When** `build_context` is called, **Then** no error is raised and the unknown category is silently ignored.

---

### Edge Cases

- Zero-execution action → technique_history rate is 0.0, no division error.
- Alert history longer than N → only the last N entries are used.
- step=0 and start_time equals call time → elapsed normalised to 0.0.
- step > MAX_STEPS → timing[0] clips to 1.0, no overflow.
- Unknown action_id in completed_actions → EpisodeState validation raises ValueError before build_context is called.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a `build_context(episode_state: EpisodeState) -> ContextVector` function that is pure and deterministic.
- **FR-002**: `EpisodeState` MUST hold: `completed_actions: set[str]`, `detection_history: dict[str, list[bool]]` (per action_id; True=detected), `alert_history: list[bool]` (step-level), `step: int`, `start_time: float`, `fired_categories: set[str]`.
- **FR-003**: `ContextVector` MUST be a flat float32 numpy array of fixed length `CONTEXT_DIM`.
- **FR-004**: The vector MUST concatenate five feature families in order: alert_history (N=10 slots), attack_progress (15 slots), technique_history (15 slots), timing (2 slots), rule_category_fired (C=8 slots).
- **FR-005**: `CONTEXT_DIM` MUST equal 10 + 15 + 15 + 2 + 8 = 50 and be exposed as a module-level integer constant.
- **FR-006**: `alert_history` slots MUST be the last N step-level detection results (1.0=detected, 0.0=undetected), zero-padded at the front when fewer than N steps have occurred, most-recent entry in slot N-1.
- **FR-007**: `attack_progress` MUST be 15 binary float32 flags (1.0 if action_id in completed_actions, else 0.0), ordered by `sorted(REGISTRY action_ids)`.
- **FR-008**: `technique_history` MUST be 15 float32 values (fraction of detected executions over all executions per action), same ordering as attack_progress; 0.0 when execution count is zero.
- **FR-009**: `timing` MUST be 2 values: `step / MAX_STEPS` clipped to [0.0, 1.0] and `(current_time - start_time) / MAX_EPISODE_SECONDS` clipped to [0.0, 1.0], where MAX_STEPS=100 and MAX_EPISODE_SECONDS=3600.
- **FR-010**: `rule_category_fired` MUST be C=8 binary float32 flags for the canonical ET Open categories in this order: ET SCAN, ET EXPLOIT, ET BRUTE_FORCE, ET WEB_SPECIFIC_APPS, ET DNS, ET POLICY, ET TROJAN, ET INFO; 1.0 if present in fired_categories.
- **FR-011**: The function MUST NOT perform any I/O, network calls, file reads, or random operations.
- **FR-012**: The function MUST raise `ValueError` if `EpisodeState.step` is negative.

### Key Entities

- **EpisodeState**: Snapshot of all observable episode data at one step — completed actions, per-action detection history, rolling alert window, step counter, episode start time, fired rule categories.
- **ContextVector**: A fixed-length (dim=50) float32 numpy array encoding EpisodeState as the RL attacker's observation.
- **CONTEXT_DIM**: Module-level integer constant = 50; the authoritative vector length used by downstream RL policy code.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `build_context` returns an array of exactly 50 elements with dtype float32 for every valid EpisodeState.
- **SC-002**: Two calls with identical EpisodeState inputs return bitwise-identical arrays.
- **SC-003**: All five feature families verified by unit tests against hand-computed worked examples; all tests pass.
- **SC-004**: No NaN or infinity values appear in the output for any valid EpisodeState.
- **SC-005**: `build_context` completes in under 1 ms on a standard development machine (pure in-memory, no I/O).

## Assumptions

- Alert history window N=10, MAX_STEPS=100, MAX_EPISODE_SECONDS=3600 are fixed module-level constants (not configurable per call).
- detection_history tracks lifetime executions per action (not windowed); technique_history is a lifetime detection rate.
- The 8 ET Open rule categories listed are fixed for Phase 1.
- Action ordering for progress/technique slots is `sorted(REGISTRY action_ids)` — consistent with F09.
- numpy is already in requirements from earlier epics.

## Dependencies

- **F03**: Core contracts (Pydantic) for EpisodeState validation.
- **F09**: `REGISTRY` from `aatf.action_library` for the 15 canonical action_ids and sorted ordering.
