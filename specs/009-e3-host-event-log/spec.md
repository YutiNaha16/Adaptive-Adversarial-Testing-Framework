# Feature Specification: Host Event Log Signal

**Feature Branch**: `009-e3-host-event-log`
**Created**: 2026-07-06
**Status**: Draft
**Epic**: E3 — Defence Interface & Detectors (F12)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Detect host-side events from the OS log and return a detection result (Priority: P1)

The experiment loop passes an executed action to the host-log adapter and receives back a
DetectionResult describing whether any configured keyword patterns matched new lines in
the host's auth/audit log. This gives the evaluator a host-side signal — e.g. SSH login
attempts recorded by sshd — alongside the network-side Suricata signal from F11.

**Why this priority**: Without a host-side detection channel, the experiment loop is
blind to events that leave no network trace: local privilege escalation, file access
auditing, PAM authentication events. A basic keyword-match against auth.log is the
minimum viable host signal for Phase 1.

**Independent Test**: Write a fixture auth.log file containing a line with a known
keyword ("sshd"); assert the adapter returns `alerted=True` with the matched pattern in
`rule_ids` — no Docker, no running lab required.

**Acceptance Scenarios**:

1. **Given** the host log contains a line matching a configured keyword pattern,
   **When** the adapter is asked to observe an action, **Then** it returns
   `alerted=True`, the matched pattern string in `rule_ids`, `coverage="covered"`,
   `anomaly_score=0.0`.

2. **Given** the host log contains no lines matching any configured pattern, **When**
   the adapter observes an action, **Then** it returns `alerted=False`, `rule_ids=[]`,
   `coverage="uncovered"`, `anomaly_score=0.0`.

3. **Given** the host log is empty (no events written yet), **When** the adapter
   observes an action, **Then** it returns `alerted=False`, `rule_ids=[]`,
   `coverage="uncovered"`, `anomaly_score=0.0`.

---

### User Story 2 — Distinguish coverage states for host-side events (Priority: P2)

The adapter reports three distinct coverage states so the evaluator can separate
genuine detection gaps from unmonitored host paths.

**Why this priority**: Principle VI (Honest Feedback) requires distinguishing "a
keyword rule existed and fired" from "no keyword rule matched" from "the log was
unreadable". Without this distinction the evaluator cannot tell whether a missed
detection is a tuning problem or a coverage gap.

**Independent Test**: Feed fixture log files representing each of the three states
to the adapter; assert the correct `coverage` value in each returned DetectionResult.

**Acceptance Scenarios**:

1. **Given** a pattern match occurred, **When** the adapter returns, **Then**
   `coverage="covered"`.

2. **Given** no pattern matched but the log file is readable, **When** the adapter
   returns, **Then** `coverage="uncovered"`.

3. **Given** the log file path is inaccessible, **When** the adapter attempts to
   observe, **Then** `coverage="unknown"` and `DefenceError` is raised.

---

### User Story 3 — Read only new log lines since the last call (Priority: P3)

On repeated calls within the same experiment run, the adapter reads only lines appended
after the previous call so that events from an earlier episode do not pollute the
current one.

**Why this priority**: Without incremental reading a keyword that fired in episode 1
would appear to have fired in episode 2 — corrupting reward signals. This is an
integrity requirement for the experiment loop, identical in motivation to F11 US3.

**Independent Test**: Simulate two sequential adapter calls against a growing fixture
log; verify the second call returns only patterns matched in lines appended after the
first call.

**Acceptance Scenarios**:

1. **Given** the adapter has already made one call and no new lines were written,
   **When** it makes a second call, **Then** it returns `alerted=False` regardless of
   what the log contained before.

2. **Given** the adapter has already made one call and a new matching line was
   appended, **When** it makes a second call, **Then** only the new match is reported.

3. **Given** the log file shrinks between calls (rotation), **When** the adapter
   detects the cursor is past the new end-of-file, **Then** it resets and re-reads
   from the beginning.

---

### Edge Cases

- What happens when multiple patterns match a single log line? All matched pattern
  strings must appear in `rule_ids`, not just the first.
- What happens when the same pattern matches multiple lines? The pattern string appears
  once in `rule_ids` per matching line (duplicates allowed — the caller can count).
- What happens when the log file contains binary or non-UTF-8 bytes? The adapter must
  decode with error replacement and continue — a single undecodable line must not crash.
- What happens when the configured pattern list is empty? The adapter must return
  `alerted=False`, `coverage="uncovered"` — an empty pattern set cannot match anything.
- What happens when `anomaly_score` is requested? It is always `0.0` — this is a
  binary keyword detector with no continuous score.
- What happens when the log file is truncated between calls? The cursor resets to 0 and
  the new file content is read from the beginning (same semantics as F11).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The adapter MUST implement the Defence interface from F10 — it MUST pass
  `check_defence_contract()` without modification to any consumer.

- **FR-002**: The adapter MUST accept a configurable log file path and a configurable
  list of keyword patterns at construction time; no paths or patterns are hardcoded.

- **FR-003**: The adapter MUST scan each new log line against every configured keyword
  pattern and collect the string of every pattern that matches.

- **FR-004**: The adapter MUST return `alerted=True` and populate `rule_ids` with all
  matched pattern strings when at least one pattern matches a new line.

- **FR-005**: The adapter MUST return `alerted=False` and `rule_ids=[]` when no new
  lines match any pattern, in accordance with the `DetectionResult` invariant from F10.

- **FR-006**: The adapter MUST return `anomaly_score=0.0` on every call — this is a
  binary keyword detector with no continuous score.

- **FR-007**: The adapter MUST set `coverage` to exactly one of three values:
  - `"covered"` — at least one pattern matched a new log line;
  - `"uncovered"` — no pattern matched but the log file was readable;
  - `"unknown"` — the log file was unreadable or inaccessible.

- **FR-008**: The adapter MUST raise `DefenceError` when the log file is unreadable,
  so callers are never silently given an unreliable result.

- **FR-009**: The adapter MUST read only log lines written after its last call
  (tail-read / byte-offset cursor) to prevent stale events contaminating new episodes.

- **FR-010**: The adapter MUST skip lines that cannot be decoded and continue
  processing — a single undecodable line must not block detection.

- **FR-011**: The adapter MUST report every distinct pattern that matched across all
  new lines so `rule_ids` is a complete record of the firing keyword rules.

- **FR-012**: An integration test MUST run against the real lab and verify that a live
  SSH probe against the defender produces a positive DetectionResult from the
  defender's auth log — a stub-only test is insufficient.

### Key Entities

- **HostLogDefence**: Concrete Defence implementation. Reads the host OS log
  incrementally, matches each new line against configured keyword patterns, translates
  matches into DetectionResult. Holds a read-position cursor and a keyword pattern list.

- **DetectionResult**: Shared output shape (F03/F10). Carries: alert flag, rule IDs
  (matched pattern strings), anomaly score (always 0.0), coverage indicator.

- **Action**: Shared input shape (F03). HostLogDefence does not use any Action fields
  directly — it reads all new log lines since the last cursor position.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of unit tests pass without a running lab — fixture-based tests cover
  all three coverage states and all edge cases documented above.

- **SC-002**: The integration test passes against the real lab: a live SSH probe to the
  defender causes a matching line to appear in the defender's auth log and the adapter
  returns `alerted=True` with the expected pattern in `rule_ids`.

- **SC-003**: `check_defence_contract()` (F10 conformance helper) passes when called
  with a `HostLogDefence` instance — zero changes to the helper required.

- **SC-004**: A second adapter call after no new log lines returns `alerted=False` —
  stale event isolation verified by test.

- **SC-005**: `make test` count increases by the number of new unit tests; no
  previously passing test regresses; `make lint` stays clean.

## Assumptions

- The host log is a plain-text file with one event per line; lines are terminated by
  `\n`. The format is not parsed structurally — only substring keyword matching is
  performed (plain string `in` operator, not regex). Regex support is deferred.
- `coverage="uncovered"` is returned when no pattern matches AND the log file is
  readable — this is the correct neutral state.
- The integration test reads the defender container's auth log via `docker exec` and
  auto-skips when the lab is not running (same guard pattern as F11).
- Multiple patterns may match a single line; each distinct matching pattern string
  appears in `rule_ids` once per match (duplicates across lines are allowed).
- The adapter does not filter by the Action's timestamp — it returns all matches since
  the last cursor position, following the same tail-read semantics as F11.
- Empty pattern list → `alerted=False`, `coverage="uncovered"` always.

## Dependencies

- **F10** (`007-e3-defence-interface`): `Defence` ABC, `DefenceError`, `NullDefence`,
  `check_defence_contract()` — merged to main.
- **F03** (`003-e0-core-contracts`): `Action`, `DetectionResult` shapes.
- **F11** (`008-e3-suricata-adapter`): Reference pattern for byte-offset cursor,
  truncation detection, and integration test skip guard.
- **Constitution Principle VI** (Honest Feedback): the three coverage states are a
  direct requirement of this principle.
