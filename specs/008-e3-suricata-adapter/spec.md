# Feature Specification: Suricata Defence Adapter

**Feature Branch**: `008-e3-suricata-adapter`
**Created**: 2026-07-06
**Status**: Draft
**Epic**: E3 — Defence Interface & Detectors (F11)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Read alert events from Suricata and return a detection result (Priority: P1)

The experiment loop passes an executed action to the Suricata adapter and receives back a
DetectionResult describing whether Suricata fired any rules — including which specific rule
identifiers matched. This replaces manual eve.json inspection with a single, structured call.

**Why this priority**: Without this translation layer, no downstream component (feedback
collector, evaluator, explainability engine) can learn anything from Suricata's output. It is
the minimum viable piece of the detection pipeline.

**Independent Test**: Feed a fixture eve.json file containing a known alert line to the
adapter; verify it returns `alerted=True` with the correct SID in `rule_ids` — no Docker,
no running lab required.

**Acceptance Scenarios**:

1. **Given** a Suricata alert for an SSH scan exists in the event log, **When** the adapter
   is asked to observe an action taken after that alert was written, **Then** it returns
   `alerted=True`, `rule_ids=["2001219"]`, `coverage="covered"`, `anomaly_score=0.0`.

2. **Given** the event log contains no alerts matching the action's time window, **When** the
   adapter observes the action, **Then** it returns `alerted=False`, `rule_ids=[]`,
   `coverage="uncovered"`, `anomaly_score=0.0`.

3. **Given** the event log is empty (Suricata just started, no traffic yet), **When** the
   adapter observes an action, **Then** it returns `alerted=False`, `rule_ids=[]`,
   `coverage="uncovered"`, `anomaly_score=0.0`.

---

### User Story 2 — Distinguish blind spots from unmonitored actions (Priority: P2)

The adapter reports three distinct coverage states so the evaluator can later separate true
detection gaps ("rule exists but threshold not reached") from genuinely unmonitored technique
categories ("no ET Open rule covers this behaviour at all").

**Why this priority**: Principle VI (Honest Feedback) requires this distinction. Without it,
the explainability engine cannot tell whether an evaded action is a tuning problem (threshold
too high) or a coverage gap (no rule exists). Both look like `alerted=False` but require
different remediation.

**Independent Test**: Feed fixture eve.json files representing each coverage state; assert
the correct `coverage` value in each DetectionResult.

**Acceptance Scenarios**:

1. **Given** an alert fired for the action's time window, **When** the adapter observes it,
   **Then** `coverage="covered"` is returned.

2. **Given** no alert fired but the event log is readable and Suricata is running, **When**
   the adapter observes an action in a category known to have ET Open rules, **Then**
   `coverage="uncovered"` is returned.

3. **Given** the event log path is inaccessible or Suricata is not running, **When** the
   adapter attempts to observe an action, **Then** `coverage="unknown"` is returned and
   `DefenceError` is raised so the caller knows the result is unreliable.

---

### User Story 3 — Read only new events since the last call (Priority: P3)

On repeated calls within the same experiment run, the adapter reads only lines written to
eve.json after the previous call, so old alerts from an earlier episode do not incorrectly
contaminate the current one.

**Why this priority**: Without incremental reading, a rule that fired in episode 1 would
appear to have fired in episode 2 as well — corrupting reward signals and metrics. This
is an integrity requirement for the experiment loop.

**Independent Test**: Simulate two sequential adapter calls against a growing fixture
eve.json; verify the second call returns only alerts from lines appended after the first call.

**Acceptance Scenarios**:

1. **Given** an alert was written before the adapter was initialised, **When** the adapter
   makes its first call, **Then** the pre-existing alert is not reported.

2. **Given** the adapter has already made one call and new alerts were written to the log
   afterwards, **When** the adapter makes a second call, **Then** only the new alerts are
   included in the DetectionResult.

3. **Given** no new lines were written since the last call, **When** the adapter makes
   another call, **Then** it returns `alerted=False` regardless of what the log contained
   previously.

---

### Edge Cases

- What happens when eve.json contains malformed JSON on one line? The adapter must skip the
  malformed line and continue, not crash — a single bad line must not block detection.
- What happens when the event log is truncated or rotated between calls? The adapter must
  detect that the file is shorter than the saved read position and reset to the beginning.
- What happens when multiple alerts for different SIDs fire in the same time window? All
  matching SIDs must appear in `rule_ids`, not just the first.
- What happens when `anomaly_score` is requested? It is always `0.0` — Suricata is binary.
- What happens when the adapter is called with an action whose timestamp is in the past?
  The time-window matching must use the action timestamp, not wall clock, for determinism.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The adapter MUST implement the Defence interface from F10 — it MUST pass
  `check_defence_contract()` without modification to any consumer.

- **FR-002**: The adapter MUST parse alert events from the Suricata event log and extract
  the rule identifier (SID) from each alert matching the relevant time window.

- **FR-003**: The adapter MUST return `alerted=True` and populate `rule_ids` with all
  matching SIDs when one or more alerts fire within the action's time window.

- **FR-004**: The adapter MUST return `alerted=False` and `rule_ids=[]` when no alerts
  fire, in accordance with the `DetectionResult` invariant from F10.

- **FR-005**: The adapter MUST return `anomaly_score=0.0` on every call — Suricata is a
  binary rule-based detector with no continuous score.

- **FR-006**: The adapter MUST set `coverage` to exactly one of three values:
  - `"covered"` — an alert fired (a rule exists and matched);
  - `"uncovered"` — no alert fired but the event log was readable;
  - `"unknown"` — the event log was unreadable or the detection service was unavailable.

- **FR-007**: The adapter MUST raise `DefenceError` when the event log is unreadable or
  inaccessible, so callers are never silently given an unreliable `"unknown"` result.

- **FR-008**: The adapter MUST read only event log lines written after its last call (tail
  read / seek position tracking) to prevent stale alerts from contaminating new episodes.

- **FR-009**: The adapter MUST skip malformed event log lines and continue processing
  rather than raising an exception for a single bad line.

- **FR-010**: The adapter MUST collect all matching SIDs from a multi-alert time window,
  not just the first one.

- **FR-011**: An integration test MUST run against the real Suricata service (lab running
  via `make lab-up`) and verify that a live probe produces a positive DetectionResult with
  the expected SID — a stub-only test is insufficient for this requirement.

### Key Entities

- **SuricataDefence**: Concrete Defence implementation. Reads the Suricata event log
  incrementally, translates alert lines into DetectionResult. Holds a read-position cursor.

- **EveAlert**: A single parsed alert line from the event log. Carries: timestamp, SID,
  alert message, source and destination addresses. Internal to the adapter.

- **DetectionResult**: Shared output shape (F03/F10). Carries: alert flag, rule IDs,
  anomaly score (always 0.0), coverage indicator.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of unit tests pass without a running lab — fixture-based tests cover all
  three coverage states and all edge cases documented above.

- **SC-002**: The integration test passes against the real lab: a live nmap SSH probe
  produces `alerted=True`, `rule_ids=["2001219"]`, `coverage="covered"` within the
  60-second poll window from the existing smoke test.

- **SC-003**: `check_defence_contract()` (F10 conformance helper) passes when called with
  a `SuricataDefence` instance — zero changes to the helper required.

- **SC-004**: A second adapter call after no new events returns `alerted=False` — stale
  alert isolation verified by test.

- **SC-005**: `make test` count increases by the number of new unit tests; no previously
  passing test regresses; `make lint` stays clean.

## Assumptions

- The Suricata event log is a JSONL file (one JSON object per line) at a configurable path;
  the default path matches the F05 volume mount (`/srv/eve/eve.json` inside the attacker
  container, or the host-side volume path for direct access).
- Alert lines in the event log contain a `event_type="alert"` field and an
  `alert.signature_id` integer field holding the SID.
- `coverage="uncovered"` is returned when no alert fires AND the event log is readable —
  this is the correct neutral state for a readable-but-silent Suricata.
- The time window for matching alerts is defined as: any alert written to the log after the
  adapter's last read position (tail-read semantics), not filtered by the action's timestamp
  field. Timestamp filtering is deferred to F15 (feedback collector) which has fuller context.
- The integration test is skipped automatically when the lab is not running (same pattern
  as the existing isolation test in `tests/test_isolation.py`).

## Dependencies

- **F10** (`007-e3-defence-interface`): `Defence` ABC, `DefenceError`, `NullDefence`,
  `check_defence_contract()` — must be merged to the working branch before implementation.
- **F03** (`003-e0-core-contracts`): `Action`, `DetectionResult` shapes.
- **F05** (`006-e1-suricata-etopen`): Suricata 7.0.5 + ET Open lab — required for the
  integration test only; unit tests run without it.
- **Constitution Principle VI** (Honest Feedback): the three coverage states are a direct
  requirement of this principle.
