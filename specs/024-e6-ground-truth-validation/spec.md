# Feature Specification: Ground-Truth Validation Harness (F22)

**Feature Branch**: `024-e6-ground-truth-validation`  
**Created**: 2026-07-11  
**Status**: Draft  
**Epic**: E6 — Analysis, Explainability & Reporting

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Validate Blind Spots Against Disabled SIDs (Priority: P1)

A security researcher has run an experiment, obtained a list of evaded actions (blind spots) from the explainability engine, and wants to know whether those blind spots correspond to genuinely disabled rules. They call `validate_blind_spots` with the blind-spot list and the set of SIDs they deliberately disabled before the run. They get back a `ValidationResult` telling them how many of the reported blind spots are confirmed by a disabled rule (true positives), how many are not (false positives), and the overall Blind-Spot Precision score. This is the number that feeds the Phase 1 gate criterion.

**Why this priority**: This is the core deliverable of F22. Without it, the system cannot answer RQ2 ("does the report accurately identify real gaps?") and the Phase 1 gate cannot be evaluated.

**Independent Test**: Call `validate_blind_spots` with a hand-crafted list of `ActionExplanation` objects and a known set of disabled SIDs; verify the returned precision and counts match analytic expectations.

**Acceptance Scenarios**:

1. **Given** two blind-spot explanations whose `suricata_category` values map to disabled SIDs, **When** `validate_blind_spots` is called, **Then** `true_positives == 2`, `false_positives == 0`, `blind_spot_precision == 1.0`.
2. **Given** one explanation confirmed by a disabled SID and one not, **When** `validate_blind_spots` is called, **Then** `true_positives == 1`, `false_positives == 1`, `blind_spot_precision == 0.5`.
3. **Given** an empty explanation list, **When** `validate_blind_spots` is called, **Then** no error is raised and `blind_spot_precision == 0.0`, all counts are zero.
4. **Given** explanations but an empty set of disabled SIDs, **When** `validate_blind_spots` is called, **Then** `blind_spot_precision == 0.0` and all counts reflect zero matches.

---

### User Story 2 — SID-to-Category Lookup (Priority: P2)

A developer integrating the validation harness needs to map a raw Suricata SID string to the `suricata_category` label used throughout the system (e.g. `"ET SCAN"`). They look up `SURICATA_SID_CATEGORIES` to translate a SID before calling `validate_blind_spots`, or to annotate a disabled-SID report with human-readable category names.

**Why this priority**: The SID-to-category map is the bridge between Suricata's rule identifiers and the category labels used by the explainability engine. Without it, callers cannot construct the `disabled_sids` argument meaningfully.

**Independent Test**: Import `SURICATA_SID_CATEGORIES` and verify it contains at least one entry per Phase 1 category and that each value is a non-empty string matching a known category label.

**Acceptance Scenarios**:

1. **Given** the `SURICATA_SID_CATEGORIES` constant is imported, **When** each of the 8 Phase 1 categories is checked, **Then** at least one SID key maps to each category value.
2. **Given** a SID present in `SURICATA_SID_CATEGORIES`, **When** it is passed as a disabled SID in `validate_blind_spots`, **Then** any blind spot with the matching `suricata_category` is counted as a true positive.

---

### User Story 3 — Phase 1 Gate Assessment (Priority: P3)

A researcher looks at the `ValidationResult` and wants to know immediately whether the Blind-Spot Precision meets the Phase 1 gate threshold (≥ 0.8). Rather than manually comparing the float, they check a property on the result object that returns a clear pass/fail boolean.

**Why this priority**: This makes the gate criterion machine-readable and directly usable in F26 (Phase 1 gate evaluation) without requiring callers to remember the threshold.

**Independent Test**: Construct `ValidationResult` objects with precision above and below 0.8; verify the gate-pass property returns `True` and `False` respectively.

**Acceptance Scenarios**:

1. **Given** a `ValidationResult` with `blind_spot_precision == 0.85`, **When** the gate property is checked, **Then** it returns `True`.
2. **Given** a `ValidationResult` with `blind_spot_precision == 0.75`, **When** the gate property is checked, **Then** it returns `False`.
3. **Given** a `ValidationResult` with `blind_spot_precision == 0.8` (exactly at threshold), **When** the gate property is checked, **Then** it returns `True`.

---

### Edge Cases

- What if `disabled_sids` contains SIDs not in `SURICATA_SID_CATEGORIES`? Unknown SIDs are silently ignored — they cannot match any category, so no blind spot is confirmed by them.
- What if the same `suricata_category` appears in multiple explanations and multiple disabled SIDs map to it? Each explanation is evaluated independently; counts reflect the number of explanations confirmed, not the number of SIDs.
- What if `blind_spot_precision` is exactly 0.0 due to empty inputs vs. zero matches? Both cases return 0.0; the `total_reported` and `disabled_sid_count` fields let callers distinguish the two situations.
- What if `disabled_sids` contains a SID that maps to a category that no explanation has? It does not affect precision — disabled SIDs only contribute to true positives when an explanation's category matches.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a `validate_blind_spots` function accepting a list of blind-spot explanations and a set of disabled Suricata SID strings.
- **FR-002**: `validate_blind_spots` MUST return a result containing: `blind_spot_precision` (float), `true_positives` (int), `false_positives` (int), `total_reported` (int), `disabled_sid_count` (int).
- **FR-003**: `blind_spot_precision` MUST equal `true_positives / total_reported`, returning `0.0` when `total_reported == 0`.
- **FR-004**: A blind-spot explanation is a true positive if and only if its `suricata_category` matches the category of at least one disabled SID in the `SURICATA_SID_CATEGORIES` lookup.
- **FR-005**: `validate_blind_spots` MUST handle an empty explanation list without error, returning all-zero counts and `blind_spot_precision == 0.0`.
- **FR-006**: `validate_blind_spots` MUST handle an empty `disabled_sids` set without error, returning `blind_spot_precision == 0.0`.
- **FR-007**: The system MUST provide a `SURICATA_SID_CATEGORIES` constant mapping SID strings to `suricata_category` labels, covering at least one representative SID per Phase 1 category (8 categories total).
- **FR-008**: The result object MUST expose a property or attribute indicating whether `blind_spot_precision >= 0.8` (the Phase 1 gate threshold).
- **FR-009**: All components (`validate_blind_spots`, `ValidationResult`, `SURICATA_SID_CATEGORIES`) MUST be importable from `aatf.ground_truth`.
- **FR-010**: `validate_blind_spots` MUST be a pure function — no file I/O, no network calls, no access to any running service.

### Key Entities

- **ValidationResult**: Immutable result of a validation call. Fields: `blind_spot_precision` (float, 0.0–1.0), `true_positives` (int ≥ 0), `false_positives` (int ≥ 0), `total_reported` (int ≥ 0), `disabled_sid_count` (int ≥ 0). Invariant: `true_positives + false_positives == total_reported`.
- **SURICATA_SID_CATEGORIES**: Static lookup table mapping SID string → suricata_category string. Covers all 8 Phase 1 categories.
- **ActionExplanation** (from F23): Input data shape. Only `suricata_category` field is consumed by this feature.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `validate_blind_spots` correctly computes `blind_spot_precision` to within floating-point tolerance for any analytic input (100% of unit tests pass).
- **SC-002**: `SURICATA_SID_CATEGORIES` covers all 8 Phase 1 `suricata_category` values — verifiable by asserting each category appears as at least one value in the map.
- **SC-003**: Calling `validate_blind_spots` with empty inputs (either argument) raises no exception in 100% of test cases.
- **SC-004**: The gate-pass property returns the correct boolean for precision values at, above, and below the 0.8 threshold.
- **SC-005**: All three public names importable from `aatf.ground_truth` in a single import statement — verified by automated import test.

---

## Assumptions

- **A1**: The caller (lab operator) is responsible for knowing which SIDs were disabled — this module only classifies whether reported blind spots align with disabled SIDs; it does not read Suricata config files.
- **A2**: The `suricata_category` field on `ActionExplanation` is always one of the 8 known Phase 1 category strings (guaranteed by the REMEDIATION_TABLE in F23).
- **A3**: SIDs outside `SURICATA_SID_CATEGORIES` are silently ignored — they produce no match and no error.
- **A4**: No new pip dependencies are required — stdlib only (`dataclasses`).
- **A5**: `ValidationResult` is immutable (frozen dataclass) for the same reason as `ActionExplanation` — results should not be mutated after computation.
