# Feature Specification: Configuration & Seed Management

**Feature Branch**: `002-e0-config-seeding`
**Created**: 2026-07-02
**Status**: Draft
**Epic**: E0 — Foundation & Reproducibility
**Backlog ref**: [docs/backlog.md — F02](../../docs/backlog.md)

## Clarifications

### Session 2026-07-02

- Q: Should `ExperimentConfig` be implemented with Pydantic V2 or a stdlib dataclass + manual validation? → A: Pydantic V2 — add `pydantic` to `requirements.in`; automatic type coercion and descriptive field-level error messages satisfy FR-002–FR-007 without hand-written validation code.
- Q: Which YAML library should be used to load the config file? → A: PyYAML — simple `yaml.safe_load()` API, de facto standard, no comment round-trip needed since the researcher edits the YAML source directly.
- Q: What should happen when `run_manifest.json` already exists in `output_dir`? → A: Timestamp the filename — write `run_manifest_<ISO-timestamp>.json` so every run's manifest is preserved; silent overwrite risks losing provenance, which violates Principle II (Reproducibility).

## Overview

Every AATF experiment must be reproducible from a single command: same config + same seed → same result. This feature delivers the three primitives that make that possible:

1. A **typed, validated configuration** loaded from one human-editable YAML file — the single source of truth for every experiment tunable.
2. A **seeding function** that seeds every random-number source in the codebase in one call — the only permitted seeding entry point.
3. A **run-manifest writer** that records enough provenance alongside each run's outputs that the run can be reproduced exactly later.

This is pure foundation infrastructure. No experiment logic is implemented here.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Typed, Validated Config from YAML (Priority: P1)

A researcher edits a single YAML file to tune experiment parameters (number of episodes, seed, output path, ruleset path, evaluation thresholds) and then starts the framework. The framework loads and validates the config at startup, rejecting bad values with a clear error before any experiment logic runs.

**Why this priority**: Without a valid config, nothing else can run. Config loading is the first thing called and must fail fast on bad input rather than crashing mid-experiment.

**Independent Test**: Load a valid YAML file → inspect the resulting config object; load a YAML with a missing required field → assert an error is raised with a description of which field is missing; load a YAML with a wrong type → assert a type error is raised.

**Acceptance Scenarios**:

1. **Given** a valid `config.yaml` with all required fields, **When** the config loader is called, **Then** it returns a typed config object whose fields match the YAML values exactly.
2. **Given** a `config.yaml` missing a required field (e.g., `seed`), **When** the config loader is called, **Then** it raises a descriptive validation error naming the missing field before any experiment code runs.
3. **Given** a `config.yaml` with a field of the wrong type (e.g., `episodes: "ten"` instead of an integer), **When** the config loader is called, **Then** it raises a type error naming the offending field and its expected type.
4. **Given** no config file at the expected path, **When** the config loader is called, **Then** it raises a `FileNotFoundError` with the path that was tried.

---

### User Story 2 — Single Seeding Entry Point (Priority: P1)

A researcher calls one function with the seed from the loaded config. After that call, every random draw in the experiment (from Python's built-in random module, from NumPy, and from PyTorch in Phase 2) is deterministic. No other code in the codebase seeds anything directly.

**Why this priority**: Reproducibility is a NON-NEGOTIABLE constitution principle (Principle II). If any code path seeds its own RNG, results will diverge between runs without warning. Enforcing one entry point makes this guarantee mechanical, not conventional.

**Independent Test**: Call `seed_everything(42)` twice in succession; after each call sample one value from Python `random` and one from NumPy — both pairs must be equal. Call again with a different seed — values must differ from the 42-seeded run.

**Acceptance Scenarios**:

1. **Given** `seed_everything(42)` has been called, **When** `random.random()` and `numpy.random.random()` are sampled, **Then** they produce the same values as any other run where `seed_everything(42)` was called first.
2. **Given** `seed_everything(42)` is called, then `seed_everything(99)` is called, **When** samples are drawn, **Then** the values match those of a fresh run seeded with 99 (the re-seed takes effect).
3. **Given** `torch` is not installed, **When** `seed_everything(42)` is called, **Then** it completes without error (the torch seeding is a no-op stub).
4. **Given** `torch` is installed, **When** `seed_everything(42)` is called, **Then** it seeds torch in addition to `random` and NumPy.

---

### User Story 3 — Run-Manifest Provenance Record (Priority: P2)

After an experiment run concludes (or at the point of writing outputs), the framework writes a JSON manifest file alongside the outputs. The manifest captures everything a future researcher needs to reproduce the run: what seed was used, which code version ran, which dependencies were installed, what config was active, and placeholder fields for the Suricata + ET Open versions that E1 will fill in.

**Why this priority**: Without the manifest, reproducibility is aspirational rather than auditable. The manifest is the audit trail. It is P2 (not P1) because the config + seeding must exist first as prerequisites.

**Independent Test**: Call the manifest writer with a known config and seed; read back the JSON file; assert all required keys are present with correct values; assert the manifest passes the typed-dict schema check.

**Acceptance Scenarios**:

1. **Given** a run has completed with a known config and seed, **When** the manifest writer is called, **Then** it creates a `run_manifest_<ISO-timestamp>.json` file in the configured output directory; calling it twice produces two distinct files.
2. **Given** a manifest file is written, **When** it is parsed, **Then** it contains: `seed` (int), `python_version` (str), `packages` (dict of name→version), `suricata_version` (str placeholder `"unknown"`), `ruleset_version` (str placeholder `"unknown"`), `git_commit` (str, or `"unknown"` if not in a git repo), `config_snapshot` (dict of all config tunables), `timestamp` (ISO-8601 string).
3. **Given** the output directory does not yet exist, **When** the manifest writer is called, **Then** it creates the directory and writes the manifest.
4. **Given** the project is not inside a git repository, **When** the manifest is written, **Then** `git_commit` is recorded as `"unknown"` and no error is raised.

---

### Edge Cases

- What if the YAML file exists but is empty or contains only whitespace?
- What if a config field is present but set to `null`/`None` for a required numeric field?
- What if `seed_everything` is called with a negative integer or zero?
- What if `seed_everything` is never called before random draws? (no guard — callers are responsible; CI tests enforce the pattern)
- What if the manifest output directory path is invalid or on a read-only filesystem?
- What if the git command is not available on the system PATH?
- What if a package version cannot be determined via `importlib.metadata`?

## Requirements *(mandatory)*

### Functional Requirements

**Config loading (US1)**

- **FR-001**: The system MUST provide a config loader that reads experiment parameters from a single YAML file.
- **FR-002**: The config object MUST be typed: every field has a declared type and invalid types are rejected on load.
- **FR-003**: The config MUST include the following required fields: `episodes` (positive integer — number of experiment episodes), `seed` (non-negative integer — global RNG seed), `output_dir` (path string — where run outputs and manifest are written), `ruleset_path` (path string — path to the Suricata ET Open ruleset directory, used by later features), `detection_threshold` (float in [0, 1] — minimum detection score for classifying traffic as malicious, used by later evaluation features).
- **FR-004**: The loader MUST raise a descriptive validation error naming any missing required field before returning.
- **FR-005**: The loader MUST raise a descriptive type error naming the offending field and its expected type when a field has an incompatible value.
- **FR-006**: If the config YAML file is not found at the given path, the loader MUST raise `FileNotFoundError` with the attempted path in the message.
- **FR-007**: An empty or whitespace-only config file MUST be treated as a missing-all-fields validation error, not a parse error.

**Seeding (US2)**

- **FR-008**: The system MUST expose a single function `seed_everything(seed: int)` as the sole randomness seeding entry point.
- **FR-009**: `seed_everything` MUST seed Python's built-in `random` module with the given seed.
- **FR-010**: `seed_everything` MUST seed NumPy's random number generator with the given seed.
- **FR-011**: `seed_everything` MUST attempt to seed PyTorch if the `torch` package is importable; if not importable, it MUST silently skip the torch seeding (no-op stub, no error).
- **FR-012**: No other module in `src/aatf/` may directly call `random.seed()`, `numpy.random.seed()`, or `torch.manual_seed()`. This constraint is enforced by a static-analysis test.
- **FR-013**: `seed_everything` MUST be idempotent per call: calling it again with the same seed resets all RNGs to the same state.

**Run manifest (US3)**

- **FR-014**: The system MUST provide a manifest writer that produces a manifest file named `run_manifest_<ISO-timestamp>.json` (e.g., `run_manifest_20260702T120000Z.json`) in `output_dir`. Each run produces a distinct file — no existing manifest is ever overwritten.
- **FR-015**: The manifest MUST be written to the `output_dir` specified in the config.
- **FR-016**: If `output_dir` does not exist, the manifest writer MUST create it before writing.
- **FR-017**: The manifest MUST contain all of the following keys: `seed`, `python_version`, `packages`, `suricata_version`, `ruleset_version`, `git_commit`, `config_snapshot`, `timestamp`.
- **FR-018**: `packages` MUST be a dict mapping each direct dependency name (from `requirements.in`) to its installed version string; packages not installed are omitted.
- **FR-019**: `suricata_version` and `ruleset_version` MUST default to the placeholder string `"unknown"` in this feature; later features (E1) will pass real values.
- **FR-020**: `git_commit` MUST be the full SHA of the current HEAD commit; if the working tree is dirty (uncommitted changes), it MUST be annotated as `"<sha>-dirty"`; if git is unavailable or the project is not a repo, it MUST record `"unknown"`.
- **FR-021**: `timestamp` MUST be an ISO-8601 UTC datetime string recorded at manifest-write time.
- **FR-022**: The manifest writer MUST accept optional `suricata_version` and `ruleset_version` string arguments (defaulting to `"unknown"`) so E1 can supply real values without changing the writer's interface.

### Key Entities

- **ExperimentConfig**: A **Pydantic V2 BaseModel**. Fields: `episodes` (int), `seed` (int), `output_dir` (Path), `ruleset_path` (Path), `detection_threshold` (float). Loaded once at startup from YAML; Pydantic enforces types and required fields automatically; treated as read-only by all downstream code.
- **RunManifest**: The provenance record written to disk. Fields: `seed`, `python_version`, `packages`, `suricata_version`, `ruleset_version`, `git_commit`, `config_snapshot`, `timestamp`. Produced by the manifest writer after each run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A researcher can change any experiment parameter (seed, episodes, paths, thresholds) by editing the YAML file only — zero code changes required.
- **SC-002**: Two runs started with the same config YAML and the same seed produce identical sequences of random values for every random draw taken through the seeding function — verified by automated test.
- **SC-003**: A timestamped `run_manifest_<ISO-timestamp>.json` file is present in the output directory after every run; no prior manifest is ever overwritten; it contains all required provenance fields verified by an automated schema assertion.
- **SC-004**: A config file with a missing required field causes the framework to halt at startup with a clear error message naming the missing field — verified by automated test.
- **SC-005**: The seeding entry point is the only place in the codebase that seeds any RNG — verified by an automated grep-based test scanning `src/aatf/` for direct seeding calls.

## Assumptions

- `ExperimentConfig` is implemented as a **Pydantic V2 BaseModel**; `pydantic` is added to `requirements.in`. Automatic type coercion and field-level error messages satisfy FR-002–FR-007 without hand-written validation.
- YAML is the config format; **PyYAML** (`pyyaml`) is added to `requirements.in`. Config is loaded via `yaml.safe_load()` — no round-trip write-back, so comment preservation is not needed.
- The default config file path is `config.yaml` at the repo root; it can be overridden by passing an explicit path to the loader.
- Package version capture uses `importlib.metadata` (stdlib in Python 3.8+); no extra dependency needed.
- Git SHA capture uses `subprocess` calling `git rev-parse HEAD`; the `git` binary is assumed to be on PATH in CI and developer machines.
- NumPy must be added to `requirements.in` (it was not a Phase 1 scaffold dependency).
- The manifest writer does not compress or encrypt the manifest; it is a plain, human-readable JSON file.
- `detection_threshold` is a float reserved for the evaluation pipeline (F20–F24); its value is validated but not used by any logic in this feature.

## Dependencies & Traceability

- **Depends on**: F01 (`001-e0-project-scaffold`) — provides `src/aatf/` layout, `requirements.in`, Makefile, pytest, `.venv`.
- **Depended on by**: All later features that need config, seeding, or provenance (F04 lab, F10 Suricata adapter, F13 experiment engine, F20 evaluator).
- **Constitution**: Principle II (Reproducibility/Determinism — NON-NEGOTIABLE), Principle IV (Scientific Validity).
- **Objectives**: O5 (one-command reproducibility).
- **Research questions**: RQ1, RQ2 (validity of results depends on reproducible random state).
