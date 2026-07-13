# Feature Specification: Unified Blind-Spot Report (F29)

**Feature Branch**: `029-e10-unified-report`
**Created**: 2026-07-13
**Status**: Draft
**Epic**: E10 — Unified Reporting

## User Scenarios & Testing *(mandatory)*

### User Story 1 — ML Section Auto-Appears in Report (Priority: P1)

A security analyst runs the experiment with the ML anomaly detector active and opens the report.
They see a new "ML Anomaly Defence Analysis" section alongside the existing Suricata blind-spot
table — in a single document, with no extra steps. When the same analyst runs the experiment with
only the rule-based Suricata detector (no ML), the ML section is absent and the report looks
exactly as before.

**Why this priority**: Without this story, F29 has no value — the section must appear correctly
and only when relevant. It is also the gating condition for US2 and US3.

**Independent Test**: Generate a report from episode records where all anomaly_score values equal
0.0 — confirm no ML section. Generate a report where at least one step has anomaly_score > 0 —
confirm the ML section is present. Existing Phase 1 content must be unchanged in both cases.

**Acceptance Scenarios**:

1. **Given** episode records where every `anomaly_score == 0.0`, **When** the report is generated,
   **Then** the output contains no "ML Anomaly Defence Analysis" heading and is identical in
   content to a Phase 1-only report.

2. **Given** episode records where at least one step has `anomaly_score > 0`, **When** the report
   is generated, **Then** the output contains an "ML Anomaly Defence Analysis" section and all
   existing Phase 1 sections (Headline Metrics, Blind Spots) are preserved unchanged.

3. **Given** the same episode records and the same generation timestamp, **When** the report is
   generated twice, **Then** both outputs are byte-for-byte identical (determinism guarantee).

---

### User Story 2 — Evasion and Suspicion Tables (Priority: P2)

A defender reads the ML section and immediately sees which specific attack actions scored lowest
on anomaly detection (most evasive) and which scored highest (most suspicious). Both tables cite
the number of episodes the statistics are drawn from, so the defender can judge confidence.

**Why this priority**: The CAE headline number alone is not actionable. The per-action breakdown
tells the defender exactly where the ML model has blind spots — which actions to investigate for
retraining data.

**Independent Test**: Generate a report from synthetic episode records with known anomaly scores
for specific action IDs. Assert the top-5 evasive table ranks actions by ascending mean
anomaly_score (undetected steps only) and the top-5 suspicious table ranks by descending mean
anomaly_score.

**Acceptance Scenarios**:

1. **Given** episode records with varied anomaly scores across multiple action IDs, **When** the
   ML section is rendered, **Then** the "Most Evasive Actions" table lists up to 5 actions sorted
   by ascending mean anomaly_score, considering only steps where the action was not detected.

2. **Given** the same records, **When** the ML section is rendered, **Then** the "Most Suspicious
   Actions" table lists up to 5 actions sorted by descending mean anomaly_score across all steps.

3. **Given** records with fewer than 5 unique action IDs, **When** tables are rendered, **Then**
   both tables contain only the available actions (no padding or placeholder rows).

---

### User Story 3 — Retraining Recommendation (Priority: P3)

A defender reads the ML section and finds a concrete list of action categories that reliably evaded
the ML detector (mean anomaly_score below the evasion threshold while also going undetected). The
recommendation tells them exactly which behaviour types to add to the next ML training batch to
close the gaps.

**Why this priority**: The tables in US2 diagnose the problem; the recommendation tells the
defender what to do. It is the actionable output that makes the report operationally useful.

**Independent Test**: Generate a report from records where two specific actions have mean
anomaly_score < 0.3 while undetected. Assert the retraining recommendation names the category of
those actions and advises including representative traffic for those categories in the next training
batch.

**Acceptance Scenarios**:

1. **Given** records where at least one action has mean anomaly_score below 0.3 and was not
   detected, **When** the report is generated, **Then** the retraining recommendation section
   lists the category names of those actions and states they should be included in the next
   training batch.

2. **Given** records where no action falls below the evasion threshold, **When** the report is
   generated, **Then** the retraining section states no ML gap was identified and suggests
   re-evaluating after longer training runs.

3. **Given** the same records across two report generations, **When** the recommendations are
   compared, **Then** they are identical (deterministic).

---

### Edge Cases

- What happens when the episode list is empty? → ML section must not appear; no exception raised.
- What if all steps have anomaly_score > 0 but all actions were detected (no evasion)? → Evasive
  table is empty; suspicious table is populated; retraining section reports no ML gap.
- What if only a single episode is in records? → All statistics cite "1 episode" explicitly.
- What if more than 5 action IDs are eligible for the tables? → Top 5 by score are shown; the
  rest are silently omitted.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The report generator MUST produce a single output file containing both the existing
  Phase 1 Suricata blind-spot content and the new ML Anomaly Defence Analysis section (when
  applicable) — no separate output files.

- **FR-002**: The ML Anomaly Defence Analysis section MUST be present if and only if at least one
  step across all episode records has `anomaly_score > 0`; the section MUST be absent otherwise.

- **FR-003**: The ML section MUST display the Cumulative Anomaly Exposure (CAE) value alongside
  the episode count from which it was computed.

- **FR-004**: The ML section MUST display a "Most Evasive Actions" table listing up to 5 action
  IDs ranked by ascending mean anomaly_score, considering only steps where the action was not
  detected.

- **FR-005**: The ML section MUST display a "Most Suspicious Actions" table listing up to 5 action
  IDs ranked by descending mean anomaly_score across all steps.

- **FR-006**: The ML section MUST display a retraining recommendation listing action categories
  whose mean anomaly_score (undetected steps) is below the evasion threshold (0.3), advising the
  defender to include representative traffic for those categories in the next training batch.

- **FR-007**: When no action category falls below the evasion threshold, the retraining section
  MUST state that no ML gap was identified in the current evaluation.

- **FR-008**: All existing Phase 1 report content (Run Metadata, Headline Metrics, Blind Spots
  table, explainability) MUST be preserved unchanged regardless of whether the ML section
  is present.

- **FR-009**: The report MUST regenerate identically from the same episode records and the same
  timestamp argument (deterministic; no runtime state may affect output).

- **FR-010**: No changes may be made to the Defence interface, the episode loop, the attacker
  interface, or any metric computation module beyond what is needed to render the report.

### Key Entities

- **MLActionStats**: Per-action summary derived from episode records — action ID, mean anomaly
  score across all steps, mean anomaly score across undetected steps only, total step count,
  undetected step count.

- **MLAnalysisSummary**: The full ML section payload — CAE value, episode count, list of up to
  5 evasive actions (sorted ascending by undetected mean score), list of up to 5 suspicious
  actions (sorted descending by overall mean score), list of category names below the evasion
  threshold.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Report with ML section is generated from episode records alone in under 2 seconds
  with no access to any live system.

- **SC-002**: ML section is absent when all `anomaly_score` values are 0.0, and present when any
  value exceeds 0.0 — verified by ≥2 test contracts (C-001, C-002).

- **SC-003**: Evasive and suspicious action tables rank correctly against a synthetic dataset of
  known scores — verified by ≥2 test contracts (C-003, C-004).

- **SC-004**: Retraining recommendation correctly identifies categories below 0.3 and produces the
  "no gap" message when no category qualifies — verified by ≥1 test contract (C-005).

- **SC-005**: All 345 existing tests continue to pass with no regressions after the change; the
  existing `generate_report()` call signature remains backward-compatible.

- **SC-006**: Report output is deterministic: two calls with the same records and the same
  `generated_at` argument produce byte-identical output.

---

## Assumptions

- `StepRecord.anomaly_score: float = 0.0` is already in the codebase (added in F28).
- `cumulative_anomaly_exposure()` is already in `metrics.py` (added in F28).
- The evasion threshold constant (0.3) is fixed at this stage; YAML configurability is out of
  scope for F29.
- "Category" means the `suricata_category` field of the action's registry definition — the same
  classification used by the existing explainability engine (e.g. "ET POLICY", "ET DNS").
- The `generate_report()` function accepts an additional optional parameter (defaulting to no
  ML analysis) so all existing callers work without modification.
