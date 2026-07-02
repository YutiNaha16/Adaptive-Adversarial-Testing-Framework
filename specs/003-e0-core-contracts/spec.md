# Feature Specification: Core Data Contracts

**Feature Branch**: `003-e0-core-contracts`
**Created**: 2026-07-02
**Status**: Draft
**Epic**: E0 — Foundation & Reproducibility

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Action and Detection exchange types (Priority: P1)

A developer building the experiment loop needs typed, validated containers for the two
most fundamental events: the action the attacker chooses, and the detection verdict the
defence returns. Both must be defined without any reference to Suricata or to any specific
ML model — they are the language both sides speak.

**Why this priority**: Every downstream component (executor, feedback collector, evaluator,
explainability engine) depends on these two types. Nothing else can be built until they exist
and are testable.

**Independent Test**: `Action` and `DetectionResult` are importable from `aatf.contracts`;
constructing a valid instance of each succeeds; invalid field values raise a validation error;
`DetectionResult` accepts both binary mode (`alerted=True, rule_ids=["SID:2100498"]`) and
continuous mode (`anomaly_score=0.87`) through the same type without error.

**Acceptance Scenarios**:

1. **Given** a valid action payload, **When** `Action` is constructed, **Then** all fields are
   accessible and the object is immutable (assignment raises an error).
2. **Given** `alerted=True` and a list of rule ids, **When** `DetectionResult` is constructed,
   **Then** it represents a binary Suricata-style detection with the correct field values.
3. **Given** `anomaly_score=0.73` and `alerted=False`, **When** `DetectionResult` is
   constructed, **Then** it represents a continuous ML-style detection with the correct score.
4. **Given** a `DetectionResult` with `anomaly_score=1.5`, **When** constructed, **Then** a
   validation error is raised (score must be in [0, 1]).
5. **Given** a missing required field in `Action`, **When** constructed, **Then** a validation
   error names the missing field.

---

### User Story 2 — EpisodeRecord JSONL observability (Priority: P1)

A developer running an experiment needs every step logged as a structured, self-contained
record that can be written to a JSONL file, read back later by the offline analysis pipeline,
and round-trip without any information loss. This is how the offline evaluator and
explainability engine get their input — they must never need to re-run the live lab.

**Why this priority**: Without a lossless, JSONL-serialisable step record, the offline
pipeline (E6) has nothing to operate on. The logging contract is as critical as the live
exchange types.

**Independent Test**: An `EpisodeRecord` can be serialised to a JSON string, written as a
JSONL line, parsed back, and re-constructed with field-for-field equality against the
original; any field type violation at construction time raises a validation error.

**Acceptance Scenarios**:

1. **Given** a fully populated `EpisodeRecord`, **When** serialised to JSON and reconstructed,
   **Then** the result equals the original (lossless round-trip).
2. **Given** a JSONL file with multiple `EpisodeRecord` lines, **When** each line is parsed and
   reconstructed, **Then** all records are valid and equal to their originals.
3. **Given** an `EpisodeRecord` with a reward of any float value, **When** constructed,
   **Then** no error is raised (reward has no hard bound — any finite float is valid).
4. **Given** an `EpisodeRecord` with a non-numeric reward, **When** constructed, **Then** a
   validation error is raised.

---

### User Story 3 — ContextVector and RunManifest supporting types (Priority: P2)

A developer building the attacker brain (F17+) and the episode orchestrator (F16) needs a
typed container for the state the attacker observes each step (the context vector), and the
offline analysis pipeline needs a typed counterpart for the run-manifest produced by F02.
Both are supporting types that complete the full vocabulary of the system.

**Why this priority**: `ContextVector` and `RunManifest` are needed by later features but
are not blocking the live loop's core exchange (US1) or the logging contract (US2). They
complete Epic E0's typed vocabulary.

**Independent Test**: `ContextVector` and `RunManifest` are importable; valid instances
construct without error; invalid field types are rejected; `RunManifest` round-trips through
JSON losslessly.

**Acceptance Scenarios**:

1. **Given** valid numeric signal arrays, **When** `ContextVector` is constructed, **Then**
   all fields are accessible and the object is immutable.
2. **Given** a `ContextVector` with an `attack_progress` value outside [0, 1], **When**
   constructed, **Then** a validation error is raised.
3. **Given** a valid `RunManifest`, **When** serialised and reconstructed, **Then** the
   result equals the original.

---

### Edge Cases

- `DetectionResult` with neither `rule_ids` populated nor `anomaly_score` set — must still
  be valid (represents an undetected action where the defence saw nothing).
- `DetectionResult` with both `rule_ids` populated and `anomaly_score` set simultaneously —
  must be valid (a hybrid detection with both a binary alert and a continuous score).
- `EpisodeRecord` where the nested `detection` has an empty `rule_ids` list — must be valid
  (undetected episode step).
- `Action` with an empty `parameters` dict — must be valid (some actions have no tuneable
  parameters).
- `ContextVector` with `current_stage=4` — must raise a `ValidationError` (only 0–3 are
  valid stages in the 4-stage attack graph).
- JSONL round-trip with `datetime`-typed fields — must serialise to ISO strings and
  reconstruct as equal `datetime` objects.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The contracts module MUST export five types: `Action`, `DetectionResult`,
  `ContextVector`, `EpisodeRecord`, `RunManifest`. All MUST be importable from
  `aatf.contracts`.
- **FR-002**: `Action` MUST carry: a unique identifier (`action_id: str`), a category label
  (`category: str`, e.g. `"scan"`, `"brute"`, `"exfil"`), a parameter dict
  (`parameters: dict[str, Any]`), and a UTC timestamp (`timestamp: datetime`). MUST be frozen.
- **FR-003**: `DetectionResult` MUST represent BOTH binary mode (Suricata: `alerted: bool`,
  `rule_ids: list[str]` — may be empty) AND continuous mode (ML: `anomaly_score: float`
  in [0, 1]) in a **single unified type**. Both fields present simultaneously MUST be valid.
  MUST be frozen.
- **FR-004**: `DetectionResult` MUST carry a `coverage` field typed as
  `Literal["covered", "uncovered", "unknown"]` so the explainability engine can distinguish
  true blind spots from threshold/load failures (constitution Principle VI).
- **FR-005**: `ContextVector` MUST carry the signal families from the proposal (§7.4):
  `alert_history: list[float]` (each element validated in [0.0, 1.0] — 0.0 = no alert,
  1.0 = alert fired; Phase 2 may use intermediate scores without a schema change),
  `attack_progress: float` (validated in [0, 1]),
  `current_stage: int` (validated in [0, 3], maps directly to the 4-stage attack graph:
  0 = recon, 1 = initial access, 2 = lateral movement, 3 = exfiltration — used by the
  attacker brain to determine legal actions at each step),
  `technique_detection_rates: dict[str, float]` (each value schema-validated in [0.0, 1.0]
  via an `Annotated` dict-value type — bad values raise `ValidationError` at construction), and
  `time_since_last_alert: float` (validated ≥ 0). MUST be frozen.
- **FR-006**: `EpisodeRecord` MUST carry: `episode_id: str`, `step: int` (≥ 0),
  `action: Action`, `detection: DetectionResult`, `reward: float`,
  `context_before: ContextVector`, `context_after: ContextVector`, `timestamp: datetime`.
  MUST be frozen.
- **FR-007**: `EpisodeRecord` MUST be JSONL-serialisable: `model_dump(mode="json")` produces
  a JSON-serialisable dict; `EpisodeRecord.model_validate(data)` reconstructs an equal
  instance (lossless round-trip). A test MUST verify this round-trip.
- **FR-008**: `RunManifest` MUST mirror the F02 runtime manifest schema: `seed: int`,
  `python_version: str`, `packages: dict[str, str]`, `suricata_version: str`,
  `ruleset_version: str`, `git_commit: str`, `config_snapshot: dict[str, Any]`,
  `timestamp: str`. MUST be frozen.
- **FR-009**: `src/aatf/contracts.py` MUST have zero imports from any defence, Suricata
  adapter, attacker, or experiment loop module. It is a pure data-shapes module.
- **FR-010**: A static-analysis test MUST verify FR-009 by grepping `contracts.py` for
  forbidden module references (mirrors the FR-012 pattern established in F02).

### Key Entities

- **Action**: One step the attacker takes — category + parameters + identity + time.
- **DetectionResult**: The defence's verdict on one action — unified binary/continuous shape
  plus coverage classification. The architectural key to Principle III (pluggable defence).
- **ContextVector**: The observable state the attacker sees before choosing each action —
  four numeric signal families from the proposal.
- **EpisodeRecord**: One complete logged step — bundles Action, DetectionResult, reward,
  before/after context, and timestamp into a self-contained JSONL record for offline replay.
- **RunManifest**: The typed read-side validation schema for the F02 provenance JSON —
  ensures the analysis pipeline can safely parse and validate a stored manifest.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All five contract types are importable from `aatf.contracts` and construct
  without error given valid inputs — verified by automated tests.
- **SC-002**: `DetectionResult` accepts binary mode, continuous mode, and both modes
  simultaneously — three distinct valid constructions, zero validation errors.
- **SC-003**: `EpisodeRecord` round-trips through JSONL (serialise → write line → read line
  → parse → reconstruct) with field-for-field equality — verified by automated test.
- **SC-004**: Invalid field types and out-of-range floats (e.g. `anomaly_score=1.5`,
  `attack_progress=-0.1`, `alert_history=[0.0, 1.5]`) are rejected at construction time
  with a validation error naming the offending field.
- **SC-005**: `contracts.py` has zero imports from defence, attacker, or loop modules —
  verified by static-analysis test.

---

## Assumptions

- Pydantic V2 is already installed (F02). No new dependencies required for this feature.
- `datetime` fields are stored as timezone-aware UTC throughout (consistent with F02 manifest).
- `parameters: dict[str, Any]` on `Action` is intentionally permissive — specific action
  types (F07) will add their own parameter validation; the contract only enforces the dict
  shape.
- `alert_history` list length on `ContextVector` is not validated at the schema level — it
  varies by rolling window size, which is a config concern, not a contract concern.
- `RunManifest` is the read-side typed validator; `aatf.manifest.write_manifest()` (F02)
  remains the write-side. Field names are identical so round-trip interop is guaranteed.
- All five types are implemented in a single flat module `src/aatf/contracts.py` (not a
  sub-package) — sufficient at this scale.

---

## Clarifications

### Session 2026-07-02

- Q: Should `DetectionResult.coverage` be a Python `Enum` or a `Literal` string type? →
  A: `Literal["covered", "uncovered", "unknown"]` — three stable values; Pydantic V2
  validates `Literal` directly without a separate Enum class.
- Q: Should contracts live in a flat `contracts.py` or a `contracts/` sub-package? →
  A: Flat `src/aatf/contracts.py` — all five types fit in one file; a sub-package adds
  indirection with no benefit until the types grow significantly in a later feature.
- Q: Should `ContextVector` carry an explicit `current_stage: int` field or infer stage
  from `attack_progress`? → A: Add `current_stage: int` validated in [0, 3] — explicit
  integer maps directly to the 4-stage attack graph and is unambiguous for the attacker
  brain's legal action selection; `attack_progress` stays for the reward signal.
- Q: Should `technique_detection_rates` dict values be schema-validated in [0.0, 1.0] or
  left to the caller? → A: Schema-validated via Pydantic `Annotated` dict-value type —
  `dict[str, Annotated[float, Field(ge=0.0, le=1.0)]]`; out-of-range values raise
  `ValidationError` at construction, consistent with all other bounded fields.
- Q: Should `alert_history` elements be `list[int]` (binary 0/1), `list[float]` validated
  in [0.0, 1.0], or `list[float]` unconstrained? → A: `list[float]` validated in [0.0, 1.0]
  — binary flags (0.0/1.0) in Phase 1; Phase 2 can use intermediate anomaly scores without
  any schema change. Pydantic validates each element; out-of-range values raise a
  `ValidationError`.
