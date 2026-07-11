# Feature Specification: Attacker Interface + Baselines (F18)

**Feature Branch**: `018-e5-attacker-baselines`
**Created**: 2026-07-11
**Status**: Draft
**Epic**: E5 — Adaptive Attacker Brain

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Common Attacker Interface (Priority: P1)

A researcher wires up any attacker policy to the episode loop by passing an object that satisfies the `Attacker` contract. They write code once against the interface and can swap in any of the three concrete implementations (random, fixed-script, LinUCB) without changing the episode loop.

**Why this priority**: The interface is the foundation everything else plugs into. Without it, neither the baselines nor LinUCBAttacker are drop-in replacements and the episode loop cannot be parameterised.

**Independent Test**: Instantiate each of the three concrete classes, verify they satisfy the `Attacker` interface, and call `choose_action` + `observe` with dummy inputs.

**Acceptance Scenarios**:

1. **Given** an `Attacker` reference holding any concrete implementation, **When** `choose_action(available, context)` is called, **Then** it returns one of the strings in `available`.
2. **Given** any concrete attacker, **When** `observe(action_id, context, reward)` is called, **Then** it completes without error (stateless attackers treat it as a no-op).
3. **Given** type-checking code that accepts `Attacker`, **When** any of the three concrete classes is passed, **Then** no type error occurs.

---

### User Story 2 — Non-Learning Baselines (Priority: P2)

A researcher runs an experiment using `RandomAttacker` (seed=0) and `FixedScriptAttacker` as comparison anchors to measure how much LinUCB improves over chance and scripted behaviour.

**Why this priority**: Baselines are required for RQ1 ("does the adaptive attacker outperform non-adaptive ones?"). `RandomAttacker` is also used in isolation tests where determinism matters.

**Independent Test**: For `RandomAttacker`: call `choose_action` 100 times with the same seed and verify the sequence is identical on a fresh instance with the same seed. For `FixedScriptAttacker`: verify the cycle repeats after the script is exhausted.

**Acceptance Scenarios**:

1. **Given** `RandomAttacker(seed=42)`, **When** `choose_action(["a","b","c"], context)` is called 10 times, **Then** the output sequence is identical to a second `RandomAttacker(seed=42)` called 10 times.
2. **Given** `FixedScriptAttacker(script=["x","y"])` and `available=["x","y"]`, **When** called 4 times, **Then** the sequence is `["x","y","x","y"]`.
3. **Given** `FixedScriptAttacker` with no explicit script and `available=["c","a","b"]`, **When** first called, **Then** the default script is alphabetical: `["a","b","c"]`.
4. **Given** `RandomAttacker`, **When** `observe` is called, **Then** it completes silently (no state change, no error).

---

### User Story 3 — LinUCB Wrapped Behind Interface (Priority: P3)

A researcher swaps in `LinUCBAttacker` (wrapping a `LinUCBModel`) in place of a baseline attacker and the episode loop continues to work identically — the only behavioural difference is that `LinUCBAttacker` learns over episodes.

**Why this priority**: This is the payoff of the interface — `LinUCBAttacker` is the production attacker for RQ1. It must be a drop-in replacement for the baselines.

**Independent Test**: Construct a `LinUCBAttacker` wrapping a `LinUCBModel(d=1)`. Call `choose_action` and `observe` directly; verify `choose_action` delegates to `LinUCBModel.select_action` and `observe` delegates to `LinUCBModel.update` by checking the model's `_arms` state changes after `observe`.

**Acceptance Scenarios**:

1. **Given** `LinUCBAttacker` wrapping a `LinUCBModel(d=1)`, **When** `observe("scan", ctx, reward=1.0)` is called, **Then** `model._arms["scan"]` exists and its `b` component is non-zero.
2. **Given** `LinUCBAttacker`, **When** `choose_action(available, context)` is called, **Then** the returned `action_id` is the same as calling `model.select_action(available, context)` directly.
3. **Given** a function accepting `Attacker`, **When** `LinUCBAttacker` is passed, **Then** it behaves identically to any other `Attacker` from the caller's perspective.

---

### Edge Cases

- What if `available` is a single-element list? All three implementations must return that element.
- What if `RandomAttacker` receives an empty `available`? Raise a clear error — the episode loop guarantees non-empty (F16 contract), so this is a programming error.
- What if `FixedScriptAttacker` has no explicit script? Default to alphabetical sort of `available` on the very first call, then hold that order for all subsequent calls.
- What if `LinUCBAttacker.observe` is called with an `action_id` not previously seen by the model? Lazy init in `LinUCBModel` handles it transparently.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an `Attacker` abstract contract with two methods: one for selecting an action from a list of available options given a context signal, and one for receiving the reward outcome of a taken action.
- **FR-002**: The `choose_action` method MUST always return one of the strings from the `available` input list.
- **FR-003**: The `observe` method MUST be callable on any `Attacker` without error, even if the implementation is stateless and ignores the inputs.
- **FR-004**: `RandomAttacker` MUST select actions uniformly at random using a seed injectable at construction (default seed = 0), producing identical sequences for identical seeds.
- **FR-005**: `FixedScriptAttacker` MUST cycle through an ordered list of action ids, repeating from the start when exhausted, ignoring the context signal entirely.
- **FR-006**: `FixedScriptAttacker` MUST default to sorting `available` alphabetically on first call if no explicit script is provided at construction, and hold that order for all future calls.
- **FR-007**: `LinUCBAttacker` MUST delegate `choose_action` to the wrapped `LinUCBModel.select_action` and `observe` to `LinUCBModel.update`.
- **FR-008**: All three concrete classes MUST be importable from a single module and satisfy the `Attacker` abstract contract.
- **FR-009**: No attacker implementation MUST perform file I/O, network calls, or subprocess execution.
- **FR-010**: `RandomAttacker` MUST raise a `ValueError` if `available` is empty.

### Key Entities

- **Attacker**: The abstract policy interface. Accepts a list of candidate action ids and a context signal; returns one action id. Also accepts reward feedback after an action is taken.
- **RandomAttacker**: Stateless baseline (beyond RNG state). Uniform random selection, fully reproducible given a seed.
- **FixedScriptAttacker**: Deterministic round-robin baseline over a fixed ordered script.
- **LinUCBAttacker**: Stateful learning attacker. Thin wrapper binding a `LinUCBModel` instance to the `Attacker` interface.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All three concrete attacker classes pass a common interface compliance test — `choose_action` returns a valid available action and `observe` completes without error — with zero failures across 100 calls per class.
- **SC-002**: `RandomAttacker(seed=N)` produces the same action sequence as a fresh `RandomAttacker(seed=N)` for any seed N across 1,000 calls.
- **SC-003**: `FixedScriptAttacker` with a 3-item script repeats the correct cycle over 9 consecutive calls with zero deviations.
- **SC-004**: `LinUCBAttacker.observe` applied 5 times with reward=1.0 results in the same model state as calling `LinUCBModel.update` 5 times directly.
- **SC-005**: Any code accepting an `Attacker` reference works identically with all three concrete implementations substituted in — no code change required at the call site.

## Assumptions

- **A1**: The episode loop always passes a non-empty `available` list to `choose_action`; empty-list behaviour for `RandomAttacker` is a programming error (`ValueError`), not a runtime edge case.
- **A2**: `FixedScriptAttacker` script and `available` always share at least one element in practice (real REGISTRY ids). Filtering script by available is out of scope.
- **A3**: Context vector dimension is a caller concern — the `Attacker` interface is dimension-agnostic; `LinUCBAttacker` inherits dimension from its wrapped `LinUCBModel`.
- **A4**: `observe` is always called with the same `action_id` that was returned by the preceding `choose_action`; out-of-order calls are the caller's responsibility.

## Scope Boundaries

**In scope**: `Attacker` ABC, `RandomAttacker`, `FixedScriptAttacker`, `LinUCBAttacker`, unit tests for all four.

**Out of scope**: Episode loop wiring (F16/F20+), run-manifest serialisation (F19+), head-to-head evaluation (F20+), Q-learning attacker (F19), Phase 2 DQN.
