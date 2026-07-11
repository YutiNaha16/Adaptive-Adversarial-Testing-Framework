# Feature Specification: Explainability Engine (F23)

**Feature Branch**: `022-e6-explainability-engine`
**Created**: 2026-07-11
**Status**: Draft
**Epic**: E6 — Analysis, Explainability & Reporting

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Action Explanation Container (Priority: P1)

A security researcher needs a single structured object that captures everything a defender needs to know about one evaded action: what it is, how often it evaded, what technique category it maps to, and what to do about it. They pass this object to the report generator (F24) or read it directly.

**Why this priority**: All other stories produce or consume `ActionExplanation`. Without the container, nothing else can be composed or tested.

**Independent Test**: Construct an `ActionExplanation` by hand with known field values and verify all eight fields are accessible and correctly stored.

**Acceptance Scenarios**:

1. **Given** an `ActionExplanation` is constructed with known values for all eight fields, **When** each field is accessed, **Then** it equals the value provided at construction.
2. **Given** `evasion_rate` is provided as `0.75`, **When** accessed, **Then** it equals `0.75`.
3. **Given** an `ActionExplanation`, **When** any field is assigned a new value, **Then** the assignment is rejected (the container is immutable).

---

### User Story 2 — Evasion Analysis (Priority: P2)

A defender runs an adversarial test session and has a list of episode records. They call `explain_evasions` to get a ranked list of blind spots — the actions that most frequently evaded detection — each paired with a concrete remediation hint. The list tells them exactly where their detection ruleset is weakest and what to tune.

**Why this priority**: This is the core function of the feature. Without it, episode data has no defender-actionable output.

**Independent Test**: Supply hand-crafted episode records with known detected/evaded patterns; verify the returned list is ranked correctly, each entry's evasion_rate is arithmetically correct, and only genuinely evaded actions appear.

**Acceptance Scenarios**:

1. **Given** episode records where action A evaded 3 of 4 steps and action B evaded 1 of 4 steps, **When** `explain_evasions` is called, **Then** action A appears before action B in the result.
2. **Given** an action that was detected on every step it appeared (evasion_rate = 0.0), **When** `explain_evasions` is called, **Then** that action does not appear in the result.
3. **Given** episode records where every action was always detected, **When** `explain_evasions` is called, **Then** the result is an empty list.
4. **Given** an empty episode records list, **When** `explain_evasions` is called, **Then** the result is an empty list with no error.
5. **Given** episode records containing a known action_id, **When** `explain_evasions` is called, **Then** each explanation's `suricata_category` and `description` match the values in the registry for that action_id.

---

### User Story 3 — Remediation and Risk Hints (Priority: P3)

A defender looks at the top-ranked blind spots and needs to know not just what failed but what to do about it. Each `ActionExplanation` carries a plain-language remediation hint and a false-positive-risk note. These come from a built-in lookup table keyed by technique category — no external call, no rerun needed.

**Why this priority**: Without remediation hints, the ranked list is diagnostic but not actionable. Satisfies constitution Principle V (Explainability): "every blind spot MUST be paired with a concrete fix suggestion."

**Independent Test**: Supply episode records from actions with a known technique category; verify the returned explanations carry non-empty `remediation` and `false_positive_risk` strings matching the built-in hints for that category.

**Acceptance Scenarios**:

1. **Given** an evaded action whose technique category is in the built-in lookup table, **When** `explain_evasions` is called, **Then** `remediation` and `false_positive_risk` are non-empty strings.
2. **Given** an evaded action whose technique category is not in the built-in lookup table, **When** `explain_evasions` is called, **Then** `remediation` and `false_positive_risk` are non-empty generic fallback strings (not an error).
3. **Given** two actions with the same technique category, **When** `explain_evasions` is called, **Then** both carry identical `remediation` and `false_positive_risk` text.

---

### Edge Cases

- What if episode records contain an action_id not present in the registry? The system raises an error — caller is responsible for supplying a registry that matches the experiment's action set.
- What if two actions have the same evasion_rate? Ties are broken by action_id ascending (lexicographic) for deterministic output.
- What if all steps for every action_id have evasion_rate = 0.0? Return empty list.
- What if episode records list contains duplicate episode records? Count all steps including duplicates — caller is responsible for deduplication if needed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an `ActionExplanation` data structure capturing eight fields: action_id, suricata_category, description, evasion_count (integer), total_count (integer), evasion_rate (float), remediation (string), false_positive_risk (string). The structure MUST be immutable.
- **FR-002**: The system MUST provide an `explain_evasions` function that accepts a list of episode records and an action registry and returns a list of `ActionExplanation` objects.
- **FR-003**: `explain_evasions` MUST compute for each unique action_id across all episode steps: `evasion_count` (steps where detected is false), `total_count` (all steps for that action_id), and `evasion_rate` (evasion_count / total_count).
- **FR-004**: `explain_evasions` MUST look up each action_id in the registry to populate `suricata_category` and `description` from the matching action definition.
- **FR-005**: `explain_evasions` MUST populate `remediation` and `false_positive_risk` from a built-in lookup table keyed by `suricata_category`. When a category is not in the table, non-empty generic fallback strings MUST be used.
- **FR-006**: `explain_evasions` MUST exclude any action with `evasion_rate = 0.0` from the result.
- **FR-007**: `explain_evasions` MUST return results sorted by `evasion_rate` descending. Ties MUST be broken by `action_id` ascending (lexicographic).
- **FR-008**: `explain_evasions` MUST return an empty list when passed an empty episode records list or when no steps were evaded.
- **FR-009**: Both `ActionExplanation` and `explain_evasions` MUST be importable from `aatf.explainability`.
- **FR-010**: The function MUST be pure and stateless: no file I/O, no network calls, no subprocess calls, no access to live defence systems.

### Key Entities

- **ActionExplanation**: Immutable result record for a single evaded action. Produced by `explain_evasions`; consumed by F24 (report generator).
- **Action registry**: Caller-supplied lookup structure mapping action IDs to their definition metadata (technique category, description). Not defined by this feature — queried read-only.
- **Episode records**: Caller-supplied list of logged episode results, each containing a list of step records. Not defined by this feature — consumed from F20/F16 output.
- **Built-in remediation table**: Module-level constant mapping known technique category values to `(remediation, false_positive_risk)` string pairs. Not user-configurable in Phase 1.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `explain_evasions` returns results in correct rank order for any hand-crafted input — verifiable by comparing `evasion_rate` of consecutive pairs.
- **SC-002**: Every `ActionExplanation` in the result has non-empty `remediation` and `false_positive_risk` strings for any registered technique category — verifiable by `len(s) > 0` assertion.
- **SC-003**: `explain_evasions` called with an empty list or all-detected steps returns `[]` with no exception — verifiable by equality assertion.
- **SC-004**: `evasion_count / total_count == evasion_rate` holds for every returned explanation — verifiable by arithmetic assertion.
- **SC-005**: Both components are importable from `aatf.explainability` in a single statement with no error.

## Assumptions

- **A1**: The `suricata_category` values in Phase 1 action definitions form a closed, known set. The built-in table covers all of them; unknown categories get generic fallback strings.
- **A2**: Caller is responsible for supplying a registry that covers all action_ids present in episode records. Missing action_id propagates as `KeyError` — this feature does not catch it.
- **A3**: Each action_id encountered in episode records has at least one step (total_count ≥ 1), so division-by-zero cannot occur.
- **A4**: The remediation table is a module-level constant (Phase 1). Caller-configurable tables are Phase 2 scope.
- **A5**: `EpisodeRecord` is imported from `aatf.metrics` (F20); `ActionRegistry` and `ActionDefinition` from `aatf.action_library` (F10). Both modules are already on `main`.

## Scope Boundaries

**In scope**: `ActionExplanation` frozen dataclass, `explain_evasions` function, built-in remediation lookup table — all in `aatf.explainability`.

**Out of scope**: Suricata SID number lookup (Phase 2), ML-based feature attribution (Phase 2), report generation (F24), statistical significance of evasion rate (F21 — done), CLI integration (F25), user-configurable remediation tables (Phase 2).
