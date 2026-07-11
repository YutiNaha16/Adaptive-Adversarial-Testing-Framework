# Feature Specification: One-Command Reproducibility (F25)

**Feature Branch**: `025-e7-repro-oneshot`
**Created**: 2026-07-11
**Status**: Draft
**Epic**: E7 — Phase 1 Gate & Hardening

## User Scenarios & Testing *(mandatory)*

### User Story 1 — End-to-End Experiment Execution (Priority: P1)

A researcher clones the repository, runs a single command (`make run`), and the system
automatically sets up the environment, executes a full adversarial experiment, and writes
a Markdown report plus run manifest to the output directory — all without any manual
intermediate steps.

**Why this priority**: This is the core deliverable of F25 and the prerequisite for F26
(Phase 1 gate). If the experiment cannot run from one command, the gate cannot be evaluated.

**Independent Test**: Run `make run` from a clean clone; confirm output directory contains
a Markdown report and run manifest JSON; confirm no manual steps were required.

**Acceptance Scenarios**:

1. **Given** a clean clone with `.venv` not yet created, **When** the researcher runs `make run`, **Then** the experiment executes end-to-end and produces a Markdown report and `run_manifest_<ISO>.json` in `output/`.
2. **Given** a successful `make run`, **When** the output files are inspected, **Then** the Markdown report contains headline metrics (detection rate, robustness score) and a blind-spots table.
3. **Given** a failed or missing Docker lab, **When** `make run` is invoked, **Then** the system prints a clear error or falls back gracefully (action executor skips live traffic but the rest of the pipeline still completes).

---

### User Story 2 — Deterministic Reproducibility (Priority: P2)

A researcher runs the experiment twice under the same fixed seed and gets byte-identical
metrics and report content.

**Why this priority**: Determinism is a constitution requirement (Principle II) and a
prerequisite for the gate's Adaptation Gain measurement to be trustworthy.

**Independent Test**: Run `make run` twice with identical `config.yaml` (same seed); diff
the two output reports; confirm metric values are identical.

**Acceptance Scenarios**:

1. **Given** two runs with the same `config.seed`, **When** both complete, **Then** `detection_rate`, `robustness_score`, and `total_reward` values are identical across both runs.
2. **Given** a run with seed A and a run with seed B, **When** both complete, **Then** the metric values differ (confirming the seed actually controls randomness).

---

### User Story 3 — Quick-Start Documentation (Priority: P3)

A new user reads the README and can reproduce the experiment from scratch by following
the documented single command, with clear description of expected outputs.

**Why this priority**: Documentation is the acceptance criterion for constitution Principle II
("one-command reproducibility under fixed seed") and required by F25 acceptance criteria.

**Independent Test**: Follow the README Quick Start section literally; confirm `make run`
works as documented; confirm expected output descriptions match actual output.

**Acceptance Scenarios**:

1. **Given** the README Quick Start section, **When** the researcher follows it, **Then** they can run `make run` and see the expected output without any additional guidance.
2. **Given** the README, **When** the researcher reads the expected outputs section, **Then** they understand what files are produced and what the key metrics mean.

---

### Edge Cases

- What happens when `output/` directory does not exist? → It must be created automatically.
- What happens when `config.yaml` is missing? → Clear error message naming the missing file.
- What happens when the Docker lab is not running? → Action executor falls back gracefully; experiment completes with simulated/skipped traffic; report is still written.
- What happens when `make run` is interrupted mid-run? → Partial output is acceptable; no corruption of previously existing output files.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a single command (`make run`) that executes the full experiment pipeline end-to-end.
- **FR-002**: The experiment entrypoint MUST load configuration from `config.yaml` in the repository root.
- **FR-003**: The entrypoint MUST call `seed_everything(seed)` before any stochastic operation to guarantee determinism.
- **FR-004**: The entrypoint MUST run N episodes (from config) using the configured attacker class via the existing episode loop.
- **FR-005**: The entrypoint MUST call the report generator and write a Markdown report to `output_dir` (from config).
- **FR-006**: The entrypoint MUST write a `run_manifest_<ISO>.json` recording experiment provenance (seed, episode count, attacker class, timestamp).
- **FR-007**: The entrypoint MUST print a human-readable summary to stdout on completion.
- **FR-008**: The `output/` directory MUST be created automatically if it does not exist.
- **FR-009**: The `make run` target MUST work from a clean clone without manual setup steps beyond installing system dependencies (Docker, Python, make).
- **FR-010**: The README MUST include a Quick Start section documenting `make run` and describing expected outputs.
- **FR-011**: Running with the same `config.seed` MUST produce identical metric values across runs (determinism guarantee).
- **FR-012**: The entrypoint MUST NOT require internet access during experiment execution (only during initial lab setup via `make lab-up`).

### Key Entities

- **Experiment entrypoint** (`src/run_experiment.py`): Orchestrates config loading, seeding, episode execution, report generation, and manifest writing.
- **Run manifest** (`run_manifest_<ISO>.json`): JSON record of seed, attacker class, episode count, timestamp, output path, and key metrics summary.
- **Makefile `run` target**: Shell target that activates the venv and invokes the entrypoint.
- **config.yaml**: Single configuration surface (already exists from F02) — seed, episodes, output_dir, attacker_class fields are consumed here.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `make run` completes successfully (exit 0) from a clean environment within 5 minutes on a laptop-class machine (lab pre-running).
- **SC-002**: Two runs with the same seed produce identical `detection_rate` and `robustness_score` values (0% variance).
- **SC-003**: The output directory contains at least 2 files after each run: a `.md` report and a `run_manifest_*.json`.
- **SC-004**: The README Quick Start section fits on a single screen (≤30 lines) and requires no domain expertise to follow.
- **SC-005**: The entrypoint exits with a non-zero code and a clear message if `config.yaml` is missing.

---

## Assumptions

- Docker and Docker Compose V2 are already installed on the target machine (prerequisite from E1).
- The `.venv` is created by `make setup` (F01 Makefile target already exists); `make run` depends on `make setup`.
- `config.yaml` exists in the repo root with valid defaults (F02 already provides this).
- The attacker class specified in config is one of the F18 baselines (RandomAttacker or LinUCBAttacker).
- `make lab-up` is a separate step the researcher runs before `make run` to start the Docker lab; `make run` does not start the lab itself (keeps concerns separate).
- No new pip dependencies are introduced — all imports are already in `requirements.txt`.

---

## Out of Scope

- Automatic Docker lab startup from `make run` (lab lifecycle is managed separately via `make lab-up`/`make lab-down`).
- CI/CD pipeline configuration.
- Windows support (Linux/macOS target only; WSL acceptable).
- Parallel multi-seed runs.
