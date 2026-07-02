# Implementation Plan: Project Scaffold & Pinned Dependencies

**Branch**: `001-e0-project-scaffold` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-e0-project-scaffold/spec.md`

## Summary

Establish the repository's foundation: a `src/` package layout whose top-level packages mirror
the two architectural layers (live experiment loop vs. offline analysis pipeline), pip-tools
based dependency pinning (`requirements.in` → hashed `requirements.txt`) installed into a
project-local `.venv`, a pytest harness with a trivial passing test, ruff for lint+format, a
`Makefile` as the single task surface (`setup` / `test` / `run` / `lint` / `lock`), a minimal
GitHub Actions CI workflow running setup+test on push/PR, an entrypoint stub that signals
"experiment loop not yet implemented," and a `.gitignore` for generated artifacts (incl. `.venv`).
No domain logic. This feature exists to make every later feature reproducible (Principle II), to
enforce the test gate automatically (Principle IV), and to lock the live-loop/defence boundary
from the start (Principle III).

## Technical Context

**Language/Version**: Python 3.12 (current CPython 3.1x baseline; confirmed `python3.12` available)
**Primary Dependencies**: pip-tools (dependency compilation/pinning), pytest (test harness), ruff
(combined linter + formatter). No runtime/domain dependencies are added in this feature.
**Storage**: N/A (no persistence in the scaffold)
**Testing**: pytest, invoked via `make test`; CI runs `make setup` + `make test` on push/PR
**Environment**: project-local virtual environment `.venv` created/reused by `make setup`
  (gitignored); installs never touch the system/active interpreter
**CI**: GitHub Actions workflow (`.github/workflows/ci.yml`) — checkout → Python 3.12 → `make setup`
  → `make test`
**Lint/format**: ruff, configured in `pyproject.toml`, invoked via `make lint`
**Target Platform**: Linux (developer + CI); container work deferred to F04+
**Project Type**: single project (Python package under `src/`)
**Performance Goals**: N/A — `make setup` + `make test` complete in well under a minute on a clean
checkout
**Constraints**: Deterministic installs (fully pinned + hashed lock); one-command setup; no
network access required at test time; live-loop package MUST NOT import any concrete defence
**Scale/Scope**: Tiny — a handful of empty package skeletons, one lockfile, one Makefile, one
trivial test, one entrypoint stub. ~10 files, no business logic.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.0.0. This is infrastructure with no
attack/defence behaviour, so several principles are "structurally satisfied / not exercised yet."

| Principle | Applies? | Status & how this feature complies |
|-----------|----------|------------------------------------|
| I. Safety & Isolation First (NN) | Partially | No traffic, no executor, no network in scope. The scaffold adds nothing that could reach outside a lab. Compliant by absence; enforcement lands in F04/F06. |
| II. Reproducibility & Determinism (NN) | **Yes (core)** | pip-tools produces a fully pinned, `--generate-hashes` lock; `make setup` is the single documented install command; Python baseline recorded in `pyproject.toml`. No randomness exists yet (seed management is F02). **PASS** |
| III. Pluggable Defence Interface (NN) | **Yes (boundary)** | Package layout creates a live-loop layer with no dependency on any concrete defence; a unit test asserts the live-loop package imports without importing a defence. The interface itself is F10; here we only protect the boundary. **PASS** |
| IV. Scientific Validity & Test-First | Partially | A runnable pytest harness is delivered so later features can be test-first; a CI workflow runs it on every push/PR. The trivial test is written before/with the scaffold it verifies. No metrics/experiments in scope. **PASS** |
| V. Explainability as a Deliverable | No | No reporting in scope. Deferred to E6. |
| VI. Observability & Honest Feedback | No | No feedback loop in scope. Deferred to E4. |
| VII. Phased Delivery Behind a Hard Gate | Yes | Strictly Phase 1, foundational. No Phase 2 code. **PASS** |

**Tech-stack alignment**: Python 3.1x ✔, pip-tools ✔, pytest ✔, Makefile task surface ✔ — all
match the constitution's mandated stack. ruff (lint/format) and a CI workflow are additive
quality/automation tooling consistent with Principles II and IV; they introduce no domain logic.

**Gate result**: PASS. No violations; Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/001-e0-project-scaffold/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (entities: dep list, lock, package skeletons, task surface)
├── quickstart.md        # Phase 1 output (how to setup/test/run)
├── contracts/
│   ├── make-targets.md   # The setup/test/run/lint/lock command contract
│   └── package-layout.md # The importable-package + boundary contract
└── checklists/
    └── requirements.md  # Spec quality checklist (from /sp.specify)
```

### Source Code (repository root)

```text
pyproject.toml              # Project metadata, Python 3.12 pin, pytest config, ruff config, packaging
requirements.in             # Human-edited direct dependencies (pip-tools, pytest, ruff)
requirements.txt            # Fully pinned + hashed lock (generated; committed)
Makefile                    # Single task surface: setup / test / run / lint / lock
.gitignore                  # Ignore __pycache__, .venv/, logs/, reports/, *.egg-info, .pytest_cache, .ruff_cache
README.md                   # Updated: one-command setup/test/run/lint + link to constitution

.github/
└── workflows/
    └── ci.yml              # CI: checkout → Python 3.12 → make setup → make test (on push/PR)

src/
└── aatf/                   # Top-level package (Adaptive Adversarial Testing Framework)
    ├── __init__.py
    ├── __main__.py         # Entrypoint stub → `make run` / `python -m aatf`
    ├── live/               # LIVE EXPERIMENT LOOP layer (attacker, executor, feedback — later)
    │   └── __init__.py     #   MUST NOT import any concrete defence
    └── analysis/           # OFFLINE ANALYSIS layer (evaluator, explainability, report — later)
        └── __init__.py

tests/
├── __init__.py
├── test_smoke.py          # Trivial passing test (harness proof)
└── test_layout.py         # Asserts live/ and analysis/ import; live/ has no defence dependency
```

**Structure Decision**: Single-project Python layout with a `src/aatf/` package (src-layout to
keep imports honest and avoid accidental top-level imports). The two architectural layers are
top-level subpackages `aatf.live` and `aatf.analysis`, created empty now so later features have a
defined home. The src-layout + `tests/` split is the standard pytest-friendly structure and
directly supports FR-001 (layered skeletons), FR-002 (boundary), and FR-008 (trivial test).

## Complexity Tracking

> No constitution violations. Section intentionally empty.
