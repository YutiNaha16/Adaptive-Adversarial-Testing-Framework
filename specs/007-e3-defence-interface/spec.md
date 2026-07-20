# Feature Specification: Pluggable Defence Interface

**Feature Branch**: `007-e3-defence-interface`
**Created**: 2026-07-06
**Status**: Draft
**Epic**: E3 — Defence Interface & Detectors (F10)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Define and invoke a detection component uniformly (Priority: P1)

A framework developer registers any detection component (rule-based or learned) behind the
single Defence contract, and the experiment loop calls it identically regardless of which
concrete detector is wired in.

**Why this priority**: Every downstream component — feedback collector, evaluator,
explainability engine — depends on receiving a consistent detection result. Without this
contract in place, none of those components can be built safely.

**Independent Test**: Wire a minimal in-memory stub that always returns "not detected" behind
the interface; confirm the loop receives a well-formed detection result and nothing else is
needed.

**Acceptance Scenarios**:

1. **Given** a concrete detector registered as a Defence, **When** the loop passes it an
   executed action, **Then** the detector returns a DetectionResult that is structurally
   identical regardless of which concrete detector produced it.

2. **Given** a Suricata-backed detector and an ML-score-backed detector both implementing the
   interface, **When** each processes the same action, **Then** both return the same shaped
   result — one with alert flag + rule IDs populated, the other with a non-zero anomaly score —
   and the loop cannot tell which is which from the return type alone.

3. **Given** a Defence implementation that encounters an internal error, **When** it is invoked,
   **Then** it raises a well-typed exception rather than returning a malformed result.

---

### User Story 2 — Swap detectors without touching consumers (Priority: P2)

A developer replaces the active detector (e.g., swaps Suricata for a trained ML model) by
changing a single configuration line, with no modifications to the feedback collector,
evaluator, or any other consumer.

**Why this priority**: This is the architectural proof that the interface is truly pluggable —
the criterion from Principle III of the project constitution. Without it, every detector
becomes a one-off integration.

**Independent Test**: Replace a stub detector with a second distinct stub in a test; assert
that consumer code under test receives correct results from both without modification.

**Acceptance Scenarios**:

1. **Given** the experiment loop is wired to Detector A, **When** Detector A is swapped for
   Detector B at configuration time, **Then** no consumer source file requires any change.

2. **Given** two detectors with different internal implementations, **When** both are run
   against the same action sequence in separate test runs, **Then** the episode logs are
   structurally identical — only the detection values differ.

---

### User Story 3 — Stub the detector in unit tests (Priority: P3)

A test author creates a lightweight in-process stub that satisfies the Defence interface,
enabling every component that consumes detection results to be unit-tested without a running
Docker lab.

**Why this priority**: If the only way to test downstream components is to spin up Suricata
containers, the test suite becomes slow, brittle, and environment-dependent. Stubbability is
the practical payoff of the interface.

**Independent Test**: Write a test for the feedback collector using only a stub Defence; no
containers, no I/O — pure in-process assertion.

**Acceptance Scenarios**:

1. **Given** a stub Defence that returns a fixed DetectionResult, **When** the feedback
   collector calls it, **Then** the collector produces the expected reward with no Docker
   dependency.

2. **Given** a stub Defence configured to simulate detection failure (raises an exception),
   **When** a consumer calls it, **Then** the consumer handles the failure path correctly and
   the test does not require any external service.

---

### Edge Cases

- What happens when a Defence implementation returns a DetectionResult with
  `coverage = "unknown"`? Consumers must treat this as a distinct state, not equivalent to
  "uncovered".
- What happens when `rule_ids` is non-empty but `alerted` is `False`? The contract must
  define whether this is a permitted state or a validation error.
- What happens when two Defence implementations are instantiated concurrently in the same
  process (future multi-run scenarios)? The interface must not rely on shared mutable state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose a single abstract Defence contract that any detection
  component implements to participate in the experiment loop.

- **FR-002**: The contract MUST accept one executed action as input and return exactly one
  DetectionResult as output — no other call signatures permitted.

- **FR-003**: The DetectionResult returned MUST simultaneously support two paradigms: a binary
  alert with associated rule identifiers (for rule-based detectors) AND a continuous detection
  confidence score in the range 0–1 (for learned detectors).

- **FR-004**: The contract MUST include a coverage indicator that distinguishes three states:
  the action was covered by at least one rule; it was not covered by any rule; coverage status
  is unknown. This distinction is required for accurate blind-spot classification.

- **FR-005**: The Defence contract MUST NOT import, reference, or depend on any concrete
  detector, network library, or file I/O mechanism. It must be self-contained and
  dependency-free beyond the shared data contracts.

- **FR-006**: Any component that consumes detection results (feedback collector, evaluator,
  explainability engine) MUST depend only on the Defence contract — never on a concrete
  implementation class.

- **FR-007**: The contract MUST be verifiable by a conformance test: any class claiming to
  implement Defence can be validated against the contract without running any external service.

- **FR-008**: Concrete Defence implementations MUST raise a typed, identifiable exception on
  internal failure rather than returning a partial or default result silently.

### Key Entities

- **Defence**: The abstract contract. Represents "any component that, given an action,
  produces a detection result." Carries no mutable state of its own.

- **DetectionResult**: The shared output shape (defined in F03). Carries: alert flag, rule
  identifiers, anomaly score, and coverage indicator.

- **Action**: The shared input shape (defined in F03). Carries: action identity, category,
  parameters, and timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of downstream consumer components reference only the abstract Defence
  contract — zero imports of any concrete detector class anywhere in consumer code.

- **SC-002**: A new concrete detector can be integrated by implementing one class and one
  configuration change — no modifications to any existing consumer file.

- **SC-003**: The full unit test suite (including Defence conformance tests) passes with zero
  external services running — no Docker, no network, no file I/O required.

- **SC-004**: Every branch of the DetectionResult shape (alert-only, score-only, both
  populated, coverage=uncovered, coverage=unknown) is exercised by at least one passing test.

- **SC-005**: `make test` count increases by the number of new interface tests; no previously
  passing test regresses.

## Assumptions

- `DetectionResult` and `Action` from F03 (`src/aatf/contracts.py`) are the canonical data
  shapes; this feature does not modify them.
- `rule_ids` being non-empty while `alerted = False` is treated as a validation error —
  rule IDs are only meaningful when an alert fired.
- Concrete implementations (Suricata adapter F11, host-event adapter F12) are out of scope;
  only the abstract interface and conformance test harness are delivered here.
- No new third-party packages are introduced; the interface relies on the Python standard
  library and Pydantic (already pinned).

## Dependencies

- **F03** (`003-e0-core-contracts`): `Action` and `DetectionResult` contracts — must be on
  `main` before implementation begins. *(Already merged.)*
- **Constitution Principle III** (Pluggable Defence): this feature is the direct
  implementation of that principle.
