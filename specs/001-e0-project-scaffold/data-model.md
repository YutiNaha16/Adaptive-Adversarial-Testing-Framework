# Phase 1 Data Model: Project Scaffold & Pinned Dependencies

This feature has **no runtime/domain data**. The "entities" are repository artifacts. They are
modelled here so the tasks and tests have a precise target.

## Artifact: Top-level dependency list (`requirements.in`)

- **Represents**: The human-curated set of direct dependencies; source of truth.
- **Fields/contents**: One pinned-or-unpinned direct dependency per line. For the scaffold:
  `pip-tools`, `pytest`, `ruff`.
- **Rules**:
  - Edited by humans only; never auto-overwritten.
  - Every entry must be a real, resolvable distribution.
- **Relationships**: Compiled into `requirements.txt` (1 → 1 generation).

## Artifact: Pinned dependency lock (`requirements.txt`)

- **Represents**: Fully resolved, integrity-verifiable record of all installed dependencies.
- **Fields/contents**: Every direct + transitive dependency pinned to `==<version>` with
  `--hash=sha256:...` entries; a header noting it is generated.
- **Rules**:
  - Generated only by `make lock` (pip-compile `--generate-hashes`); never hand-edited.
  - Zero unpinned entries (SC-002); install uses `--require-hashes` (fails closed).
- **Relationships**: Derived from `requirements.in`; consumed by `make setup`.

## Artifact: Package layer skeletons (`src/aatf/...`)

- **Represents**: The two architectural layers as importable packages.
- **Members**:
  - `aatf` — top-level package.
  - `aatf.live` — live experiment loop layer (empty skeleton).
  - `aatf.analysis` — offline analysis layer (empty skeleton).
  - `aatf.__main__` — entrypoint stub.
- **Rules (invariants tested)**:
  - `aatf`, `aatf.live`, `aatf.analysis` all import successfully (FR-001).
  - Importing `aatf.live` introduces no concrete-defence module (FR-002, Principle III).
- **Relationships**: Both layers will later depend on shared contracts (F03); none of that exists
  yet.

## Artifact: Task surface (`Makefile`)

- **Represents**: The single discoverable list of project commands.
- **Targets**:
  - `setup` — create/reuse `.venv` and install from the pinned, hashed lock (+ editable package).
  - `test` — run pytest; non-zero exit on failure.
  - `run` — invoke the entrypoint stub.
  - `lint` — run ruff lint + format check; non-zero exit on violations.
  - `lock` — recompile `requirements.txt` from `requirements.in`.
- **Rules**: Targets are the only sanctioned way to perform these actions (FR-012); each maps to
  one documented behaviour.

## Artifact: Ignore rules (`.gitignore`)

- **Represents**: Version-control exclusions for generated/environment artifacts.
- **Contents**: `__pycache__/`, `*.pyc`, virtualenv dirs (`.venv/`, `venv/`), `*.egg-info/`,
  `.pytest_cache/`, `.ruff_cache/`, `logs/`, `reports/`.
- **Rules**: Generated caches/logs/reports and the `.venv` never tracked (FR-010, FR-015, edge case).

## Artifact: Project virtual environment (`.venv/`)

- **Represents**: The isolated, project-local Python environment.
- **Rules**: Created/reused by `make setup`; gitignored (FR-015); every other target uses its
  interpreter (`.venv/bin/python`). Guarantees installs are isolated from the system interpreter
  (SC-002).

## Artifact: Code-quality configuration (`[tool.ruff]` in `pyproject.toml`)

- **Represents**: The shared lint + format baseline.
- **Rules**: Single ruff configuration governs `make lint` and CI; later features inherit it
  unchanged (FR-013, SC-008).

## Artifact: CI workflow (`.github/workflows/ci.yml`)

- **Represents**: The automation that enforces reproducibility + the test gate.
- **Fields/contents**: Triggers (push, pull_request); steps (checkout → Python 3.12 → `make setup`
  → `make test`).
- **Rules**: Must run on push/PR and fail on any test failure (FR-014, SC-007).
