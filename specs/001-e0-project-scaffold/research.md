# Phase 0 Research: Project Scaffold & Pinned Dependencies

All Technical Context items were resolvable from the constitution's mandated stack and the local
environment; there were no open NEEDS CLARIFICATION markers. This document records the decisions.

## D1 — Python baseline version

- **Decision**: Python 3.12 (pin `requires-python = ">=3.12,<3.13"` in `pyproject.toml`).
- **Rationale**: The constitution mandates "Python 3.1x." `python3.12` is present in the
  environment, and the pre-existing prototype artifacts were compiled as `cpython-312`, so 3.12 is
  the established baseline. Bounding below 3.13 keeps the pinned lock reproducible against one
  minor line.
- **Alternatives considered**: 3.11 (also present) — rejected to standardise on the newest 3.1x
  already in use; an unbounded `>=3.12` — rejected because a future 3.13 could change transitive
  resolutions and break determinism (Principle II).

## D2 — Dependency pinning workflow

- **Decision**: pip-tools. `requirements.in` (human-edited direct deps) compiled with
  `pip-compile --generate-hashes` into a fully pinned `requirements.txt`; both committed.
  `make setup` installs via `pip install --require-hashes -r requirements.txt`.
- **Rationale**: Directly satisfies FR-003/FR-004/FR-011 and Principle II: a clear source-of-truth
  vs. lock split, transitive pinning, and hash integrity so installs are byte-identical across
  machines. `--require-hashes` makes an unpinned/untrusted install fail closed.
- **Alternatives considered**: Poetry/PDM (heavier, manage their own venvs and metadata — more than
  a scaffold needs, and the constitution explicitly names pip-tools); bare `pip freeze` (no
  source/lock separation, no hashes — fails FR-003/FR-011); uv (fast, but not the mandated tool;
  can be revisited later without changing the contract).

## D3 — Test harness

- **Decision**: pytest, configured in `pyproject.toml` (`[tool.pytest.ini_options]` with
  `testpaths = ["tests"]`). Invoked via `make test`.
- **Rationale**: Constitution-mandated; standard, zero-ceremony discovery; non-zero exit on
  failure satisfies FR-007/SC-003. Config in `pyproject.toml` keeps one metadata file.
- **Alternatives considered**: unittest (more boilerplate, weaker fixtures); a separate
  `pytest.ini` (rejected to avoid a second config file).

## D4 — Task surface

- **Decision**: A `Makefile` exposing `setup`, `test`, `run`, and `lock` (lock = recompile the
  pinned file). `make` confirmed available (GNU Make 4.3).
- **Rationale**: Satisfies FR-006/FR-007/FR-009/FR-012 with one discoverable surface; `lock`
  covers FR-011's "documented, repeatable" recompile. Make is ubiquitous and dependency-free.
- **Alternatives considered**: A `tasks.py`/invoke or shell scripts — rejected as adding a runtime
  dependency or scattering commands; npm-style runner — irrelevant to a Python project.

## D5 — Package layout (src-layout + layer split)

- **Decision**: `src/aatf/` with subpackages `aatf.live` (live experiment loop) and
  `aatf.analysis` (offline analysis). Tests live in top-level `tests/`.
- **Rationale**: src-layout prevents accidental imports of un-installed code and forces tests to
  run against the installed package — a reproducibility safeguard. The two subpackages give
  FR-001's layered skeletons a concrete home and let a test enforce FR-002's boundary (live must
  not import a concrete defence).
- **Alternatives considered**: flat layout (`aatf/` at root) — rejected for weaker import hygiene;
  splitting into multiple distributions — unnecessary complexity for one project (Principle of
  simplicity).

## D6 — Boundary enforcement (Principle III) as a test

- **Decision**: `tests/test_layout.py` imports `aatf.live` and `aatf.analysis`, and asserts that
  importing `aatf.live` pulls in no module whose name marks it a concrete defence (e.g. a
  `suricata`/`defence` implementation). Since no such modules exist yet, the test documents and
  guards the boundary from day one.
- **Rationale**: Makes Principle III a property the suite checks, not a convention, exactly as the
  constitution requires for non-negotiables.
- **Alternatives considered**: import-linter (a dependency + config) — deferred; a lightweight
  in-test check is sufficient at scaffold scale and adds no dependency.

## D7 — Entrypoint stub behaviour

- **Decision**: `python -m aatf` (and `make run`) prints a clear "experiment loop not yet
  implemented" message and exits 0.
- **Rationale**: Reserves the one-command run surface (FR-009/SC-005) without faking experiment
  behaviour. Exit 0 because a stub is not an error condition.
- **Alternatives considered**: exit non-zero — rejected; a not-yet-built stub being invoked as
  designed is success, not failure.

## D8 — Environment isolation (`.venv`) *(clarified 2026-06-30)*

- **Decision**: `make setup` creates/reuses a project-local virtual environment at `.venv` and
  installs into it (`python3.12 -m venv .venv`, then `--require-hashes` install + editable install
  of the package). `.venv/` is gitignored. All other targets invoke the `.venv` interpreter.
- **Rationale**: Strongest isolation/reproducibility (FR-006, SC-002) — installs never depend on or
  pollute the system/active interpreter, and every machine gets the same env from one command.
- **Alternatives considered**: install into the active interpreter (simpler Makefile, but
  reproducibility depends on the caller pre-creating a clean env) — rejected for weaker guarantees.

## D9 — Lint/format tooling (ruff) *(clarified 2026-06-30)*

- **Decision**: ruff provides both linting and formatting; configured under `[tool.ruff]` in
  `pyproject.toml`; `make lint` runs `ruff check .` and `ruff format --check .`. ruff added to
  `requirements.in`.
- **Rationale**: One fast tool covers lint + format (FR-013, SC-008) with minimal dependencies,
  setting a quality baseline every later feature inherits. `--check` form makes `make lint` and CI
  fail on violations rather than silently reformat.
- **Alternatives considered**: black + flake8 (two tools, two configs, more deps) — rejected;
  deferring lint entirely — rejected because retrofitting touches the scaffold and all existing
  files.

## D10 — Continuous integration (GitHub Actions) *(clarified 2026-06-30)*

- **Decision**: A minimal workflow at `.github/workflows/ci.yml` runs on push and pull_request:
  checkout → set up Python 3.12 → `make setup` → `make test`.
- **Rationale**: Enforces the reproducibility + test gate automatically from the first feature
  (FR-014, SC-007); trivial to add now, friction to retrofit. The spec already referenced
  "CI-style invocation."
- **Alternatives considered**: defer CI to the E7 hardening feature — rejected so the gate is live
  from day one; other CI providers — GitHub Actions chosen as the repo's host platform, behind the
  same `make` targets so the provider is swappable.
