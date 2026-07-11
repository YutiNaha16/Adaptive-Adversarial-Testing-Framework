# Feature Specification: Report Generator (F24)

**Feature Branch**: `023-e6-report-generator`  
**Created**: 2026-07-11  
**Status**: Draft  
**Epic**: E6 — Analysis, Explainability & Reporting

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Report Generation from Episode Logs (Priority: P1)

A security researcher has run an adversarial experiment and has a list of episode records. They call `generate_report` with those records, the action registry, and an output path. They get back a Markdown file that they can open in any text editor or render in a browser, containing everything a defender needs to act: what was run, how detections performed, and exactly which actions evaded detection with concrete fix suggestions. They do not need to understand the experiment internals.

**Why this priority**: This is the core deliverable — the entire E6 epic exists to produce this report. Without it, all analysis outputs (F20 metrics, F21 statistics, F23 explanations) have no defender-facing presentation layer.

**Independent Test**: Call `generate_report` with hand-crafted episode records and verify the returned string is non-empty, parseable Markdown, and contains the known action_ids from the input.

**Acceptance Scenarios**:

1. **Given** a list of episode records with known evaded actions, **When** `generate_report` is called, **Then** a non-empty Markdown string is returned and the same content is written to the output file.
2. **Given** the same episode records and registry, **When** `generate_report` is called twice, **Then** the output is byte-for-byte identical both times (determinism).
3. **Given** an empty episode records list, **When** `generate_report` is called, **Then** the report renders without error, shows zero episodes and 0.0 metrics, and contains an empty blind-spots table.
4. **Given** a valid output path, **When** `generate_report` completes, **Then** the file at output_path contains the same content as the returned string.

---

### User Story 2 — Headline Metrics Section (Priority: P2)

A defender reading the report wants to know at a glance how their IDS performed during the experiment: what fraction of attack steps were detected, how the detector behaved in the most recent episodes, and what the reward distribution looked like across episodes. These are the numbers they need to justify tuning time or escalate to management.

**Why this priority**: Metrics give the blind-spots table context. Without them a reader cannot assess severity: 100% evasion on 2 steps is very different from 100% evasion on 500 steps.

**Independent Test**: Supply records with a known detection rate (e.g., half of all steps detected); verify the report contains the correct rate value and reward summary values.

**Acceptance Scenarios**:

1. **Given** episode records where half the steps were detected, **When** the report is generated, **Then** the headline metrics section contains a detection rate value equal to 0.5 (±tolerance).
2. **Given** episode records with known total_reward values, **When** the report is generated, **Then** the headline metrics section contains the correct mean total_reward.
3. **Given** fewer than 10 episodes, **When** the report is generated, **Then** robustness_score (last-10 window) is computed over all available episodes without error.

---

### User Story 3 — Blind-Spots Table (Priority: P3)

A defender reads the blind-spots section to find out which specific technique categories their ruleset missed most often and what to tune first. The table is ranked so the worst blind spot is at the top. Each row carries a concrete remediation hint so the defender can act immediately without needing to re-read the experiment code.

**Why this priority**: This is the actionable output that delivers on constitution Principle V ("every blind spot MUST be paired with a concrete fix"). The headline metrics section provides context, but the blind-spots table is what the defender actually tunes from.

**Independent Test**: Supply records with two evaded actions having different evasion rates; verify the report's blind-spots section lists them in descending evasion-rate order and each row has non-empty remediation text.

**Acceptance Scenarios**:

1. **Given** records where action A evaded more often than action B, **When** the report is generated, **Then** the blind-spots section lists A before B.
2. **Given** an evaded action with a known suricata_category, **When** the report is generated, **Then** the blind-spots row for that action contains non-empty remediation text.
3. **Given** episode records where every action was always detected, **When** the report is generated, **Then** the blind-spots section contains an empty table (zero rows, no error).

---

### User Story 4 — Run Metadata and Footer (Priority: P4)

A researcher who returns to a report weeks later needs to know when it was generated, what attacker was used, how many episodes ran, and what seeds were used — so they can reproduce the experiment. The footer reminds them the data came from logged records, not a live rerun.

**Why this priority**: Metadata is mandatory for reproducibility (constitution Principle II). Without it, reports are not self-describing and cannot be cited or reproduced.

**Independent Test**: Supply a known attacker_class and seed value; verify the report metadata section contains both values as provided.

**Acceptance Scenarios**:

1. **Given** records with a known `attacker_class`, **When** the report is generated, **Then** the metadata section contains that attacker class name.
2. **Given** records with known seed values, **When** the report is generated, **Then** the metadata section lists those seeds.
3. **Given** a caller-supplied generation timestamp, **When** the report is generated, **Then** the metadata section contains that timestamp in ISO 8601 format.
4. **Given** any input, **When** the report is generated, **Then** the footer is present and non-empty.

---

### Edge Cases

- What if `output_path`'s parent directory does not exist? The function raises an error — caller is responsible for ensuring the parent directory exists (no implicit mkdir).
- What if episode records contain no steps at all? Metrics compute as 0.0 and the blind-spots table is empty; the report still renders without error.
- What if all steps were evaded (detection_rate = 0.0)? All actions appear in the blind-spots table; report renders without division-by-zero error.
- What if records come from multiple distinct `attacker_class` values? All unique attacker classes appear in the metadata section.
- What if the same seed appears in multiple records? Seeds are deduplicated and sorted for display in the metadata section.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a `generate_report` function accepting: a list of episode records, an action registry, an output file path, and an optional generation timestamp.
- **FR-002**: `generate_report` MUST return the rendered Markdown string and write the same content to the output path.
- **FR-003**: `generate_report` MUST produce byte-for-byte identical output for the same inputs (including identical timestamp argument).
- **FR-004**: The report MUST include a metadata section containing: unique attacker class(es) sorted, unique seed(s) sorted, total episode count, and generation timestamp in ISO 8601 format.
- **FR-005**: The report MUST include a headline metrics section containing: detection_rate, robustness_score (last 10 episodes window), and total_reward mean ± std with 95% CI; robustness_score uses all available episodes when fewer than 10 exist.
- **FR-006**: The report MUST include a blind-spots section with a ranked table of evaded actions ordered by evasion_rate descending (ties broken by action_id ascending), containing: action_id, suricata_category, evasion_rate (%), evasion_count, total_count, and remediation hint.
- **FR-007**: The report MUST include a footer stating that data was generated from logged episode records with no live defence access.
- **FR-008**: `generate_report` MUST handle an empty episode records list without error, producing a valid Markdown report with zero/empty values in all sections.
- **FR-009**: `generate_report` MUST raise an error if the output path's parent directory does not exist.
- **FR-010**: `generate_report` MUST be importable from `aatf.report`.

### Key Entities

- **Report data**: Intermediate bundle assembled from episode records, registry, and computed metrics before rendering. Ensures all template inputs are deterministically ordered.
- **Episode records**: Caller-supplied list of logged experiment results (from F20/F16). Not defined by this feature — consumed read-only.
- **Action registry**: Caller-supplied mapping from action IDs to definitions (from F10). Not defined by this feature — queried read-only via `explain_evasions` (F23).
- **Markdown template**: Versioned template file that renders report sections from the report data bundle. Lives alongside the module code.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Calling `generate_report` twice with identical inputs produces byte-for-byte identical output — verifiable by string equality assertion.
- **SC-002**: The returned string and the file written to output_path contain the same content — verifiable by equality assertion.
- **SC-003**: The report for non-empty inputs contains the correct detection_rate and mean total_reward — verifiable by substring or numeric value assertions.
- **SC-004**: `generate_report` with an empty records list completes without raising an exception and returns a non-empty Markdown string — verifiable by type and length assertions.
- **SC-005**: The blind-spots section lists evaded actions in correct descending evasion-rate order — verifiable by finding action_ids in the rendered string in the expected sequence.
- **SC-006**: `generate_report` is importable from `aatf.report` — verifiable by import assertion at test-collection time.

## Assumptions

- **A1**: Jinja2 is a new pip dependency; it must be added to `requirements.in` before implementation.
- **A2**: The generation timestamp is caller-supplied (defaulting to `datetime.now(UTC)` when not provided) so tests can supply a fixed value for determinism.
- **A3**: `adaptation_gain` requires two separate record lists (baseline vs learner); the single-list `generate_report` omits this metric or labels it "N/A" in the report.
- **A4**: The output path accepts both `str` and `pathlib.Path`; the function normalises internally via `pathlib.Path`.
- **A5**: Determinism is achieved by: sorted collections before template rendering, caller-supplied fixed timestamp, and no random elements in template or data assembly.
- **A6**: The Jinja2 template is loaded from the `src/aatf/templates/` directory alongside the module, via a path relative to the module file or `importlib.resources`.

## Scope Boundaries

**In scope**: `generate_report` function, Jinja2 Markdown template (`report.md.j2`), deterministic data assembly, file write, four report sections (metadata, headline metrics, blind spots, footer) — all in `aatf.report`.

**Out of scope**: HTML rendering (Phase 2), adaptation_gain in single-list report (requires two lists), Suricata SID lookup (F22/Phase 2), CLI integration (F25), ground-truth validation (F22), caller-configurable templates (Phase 2).
