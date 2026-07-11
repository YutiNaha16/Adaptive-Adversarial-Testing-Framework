# Feature Specification: Automated Phase 1 Gate Evaluation (F26)

**Feature Branch**: `026-e7-phase1-gate`
**Created**: 2026-07-11
**Status**: Draft
**Input**: User description: F26 (Epic E7) — Automated Phase 1 gate evaluation

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automated Gate Evaluation (Priority: P1)

As a security researcher running the framework, after completing an experiment run I want an automated gate that evaluates whether Phase 1 exit criteria are met and gives me a clear pass/fail verdict with per-criterion detail, so I know exactly which criteria passed, which failed, and by how much.

**Why this priority**: This is the core deliverable of F26 — without the gate evaluation function, the Phase 1 exit is undefined. All other stories depend on the gate result existing.

**Independent Test**: Call `phase1_gate(records, validation_result)` with known inputs and verify the returned result has the correct overall pass/fail flag and per-criterion breakdown. Fully testable with in-memory test data, no I/O required.

**Acceptance Scenarios**:

1. **Given** a list of episode records with detection rate ≥ 0.0, and a validation result with blind_spot_precision ≥ 0.8, **When** the gate is evaluated, **Then** the result is `passed = True` and all three criterion results have `passed = True`.
2. **Given** a validation result with blind_spot_precision = 0.5 (below the 0.8 threshold), **When** the gate is evaluated, **Then** the result is `passed = False` and the blind-spot criterion reports `passed = False`.
3. **Given** an empty episode list, **When** the gate is evaluated, **Then** the result is `passed = False` (no episodes means robustness is undefined).

---

### User Story 2 - Gate Result in Experiment Output (Priority: P2)

As a security researcher, after `make run` completes I want the gate result printed to stdout and included in the run manifest, so I can immediately see pass/fail status and have a machine-readable record for CI/CD integration.

**Why this priority**: Observability of the gate result is required to make it actionable. Without stdout output and manifest inclusion, the gate is invisible to the operator and to any automated pipeline.

**Independent Test**: Run the experiment entrypoint with a minimal test config and verify stdout contains a gate summary block and the manifest JSON has a gate key.

**Acceptance Scenarios**:

1. **Given** a valid experiment config (2 episodes), **When** the experiment entrypoint completes, **Then** stdout contains a gate result block showing PASS or FAIL and per-criterion values.
2. **Given** a valid experiment run, **When** the run manifest is written, **Then** the manifest JSON contains a `phase1_gate` key with `passed` boolean and `criteria` list.

---

### Edge Cases

- What happens when the episode list is empty? → Robustness score is undefined for 0 episodes; the gate returns `passed = False` for the RS criterion.
- What if the validation result has BSP = 0.0? → BSP < 0.8, so the BSP criterion fails and the gate overall fails.
- What if all three criteria pass? → `GateResult.passed = True`; summary says "Phase 1 PASSED".
- What if one criterion fails? → `GateResult.passed = False`; summary names the failing criterion.
- What if the gate fails? → Execution continues normally; the gate does not raise or exit.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The gate evaluation MUST accept a list of episode records and a blind-spot validation result, and return a structured gate result with an overall pass/fail flag.
- **FR-002**: The gate MUST evaluate exactly three criteria: Detection Rate ≥ 0.0, Blind-Spot Precision ≥ 0.8, Robustness Score ≥ 0.0 (with at least one episode completed).
- **FR-003**: Each criterion result MUST include: a human-readable name, pass/fail status, the actual measured value, and the threshold value.
- **FR-004**: The gate MUST be a pure function — no file I/O, no side effects, fully deterministic for the same inputs.
- **FR-005**: The experiment runner MUST call the gate after the episode loop completes, print the gate result to stdout, and include it in the run manifest.
- **FR-006**: The gate MUST NOT terminate the experiment on failure — it reports the result and allows the caller to decide.
- **FR-007**: An empty episode list MUST produce a failing gate result (overall `passed = False`).

### Key Entities

- **GateResult**: Top-level gate result — overall `passed` (bool), list of `criteria` (list of CriterionResult), human-readable `summary` (str).
- **CriterionResult**: Per-criterion result — `name` (str), `passed` (bool), `value` (float), `threshold` (float).
- **ValidationResult**: Input from ground-truth validation — provides `blind_spot_precision` float (from F22).
- **EpisodeRecord**: Input from metrics module — list of completed episode records used to compute DR and RS (from F20).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Gate evaluation completes in under 10 ms for any experiment size (pure in-memory computation, no I/O).
- **SC-002**: Gate correctly identifies pass vs. fail for all boundary test cases (each criterion boundary tested from both sides).
- **SC-003**: After `make run`, the gate verdict appears in stdout within the existing output block — no additional user action required.
- **SC-004**: The run manifest includes a machine-readable gate summary that an automated pipeline can parse to gate a deployment.
- **SC-005**: The gate function returns identical results for identical inputs on any run (fully deterministic).

## Assumptions

- Detection Rate threshold of ≥ 0.0 means "experiment produced at least one episode" — with NullDefence, DR will be 0.0 and this criterion passes trivially, confirming the experiment ran.
- Robustness Score ≥ 0.0 with at least one episode: if the records list is empty, RS is undefined and the criterion fails.
- Blind-Spot Precision ≥ 0.8 is the only non-trivial criterion in Phase 1. With NullDefence, BSP = 0.0 so the gate will report FAIL for BSP in a standard `make run`. This is expected — Phase 1 gate failure is informational, not terminal.
- The gate does not load disabled SIDs itself — ValidationResult is computed externally and passed in.
- The `summary` string is a human-readable one-liner: e.g., "Phase 1 PASSED (3/3 criteria met)" or "Phase 1 FAILED (2/3 criteria met: blind_spot_precision below threshold)".
