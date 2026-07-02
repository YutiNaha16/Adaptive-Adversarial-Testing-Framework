---
description: "Task list for 001-e0-project-scaffold"
---

# Tasks: Project Scaffold & Pinned Dependencies

**Input**: Design documents from `specs/001-e0-project-scaffold/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Test tasks ARE included — the spec mandates a trivial harness test (FR-008) and the
constitution requires the live/analysis boundary to be enforced by a test (Principle III). These
are the only two tests in scope; no domain tests exist yet.

**Organization**: Grouped by the four user stories in spec.md (US1 P1, US2 P1, US3 P2, US4 P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US4 per spec.md

## Path Conventions

Single project, src-layout: package under `src/aatf/`, tests under `tests/` at repo root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Repository structure and the static config files every story relies on.

- [X] T001 Create the directory structure at repo root: `src/aatf/`, `src/aatf/live/`, `src/aatf/analysis/`, `tests/`, `.github/workflows/`
- [X] T002 [P] Create `requirements.in` at repo root listing direct dev dependencies: `pip-tools`, `pytest`, `ruff` (per data-model.md "Top-level dependency list")
- [X] T003 [P] Create `.gitignore` at repo root ignoring `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `*.egg-info/`, `.pytest_cache/`, `.ruff_cache/`, `logs/`, `reports/` (FR-010, FR-015)
- [X] T004 [P] Create `pyproject.toml` at repo root: project metadata, `requires-python = ">=3.12,<3.13"` (FR-005), src-layout package discovery, `[tool.pytest.ini_options]` with `testpaths = ["tests"]`, and `[tool.ruff]` lint+format config (research.md D1, D3, D5, D9)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Importable package skeletons, the pinned lock, and the single task surface. **All user
stories depend on these.**

**⚠️ CRITICAL**: No user-story validation can run until this phase is complete.

- [X] T005 Create package skeletons: `src/aatf/__init__.py` (with a `__version__`), `src/aatf/live/__init__.py`, `src/aatf/analysis/__init__.py`, and `tests/__init__.py` (FR-001; data-model.md "Package layer skeletons")
- [X] T006 Generate the pinned lock `requirements.txt` from `requirements.in` via `pip-compile --generate-hashes` (fully pinned + hashed) and commit it (FR-004; research.md D2)
- [X] T007 Create the `Makefile` at repo root exposing the full task surface — `setup` (create/reuse `.venv`, install `--require-hashes` from lock, editable-install the package), `test` (run pytest), `run` (`.venv` python `-m aatf`), `lint` (`ruff check .` + `ruff format --check .`), `lock` (`pip-compile --generate-hashes`), and a default `help` listing targets (FR-006, FR-007, FR-009, FR-012, FR-013; contracts/make-targets.md)

**Checkpoint**: Package imports resolve, lock exists, and every command has a home.

---

## Phase 3: User Story 1 - Reproducible environment setup (Priority: P1) 🎯 MVP

**Goal**: One command produces an identical, isolated, fully-pinned environment from a clean
checkout.

**Independent Test**: From a clean checkout run `make setup`; a `.venv` is created and `import aatf`
succeeds using only pinned, hashed dependencies.

### Implementation for User Story 1

- [X] T008 [US1] Run `make setup`; verify it creates `.venv`, installs from `requirements.txt` with `--require-hashes`, and editable-installs the package so `.venv/bin/python -c "import aatf"` succeeds (FR-006; SC-001, SC-002). Fix the `setup`/`lock` targets in `Makefile` if needed.
- [X] T009 [US1] Verify `make lock` regenerates `requirements.txt` fully pinned + hashed from `requirements.in`, leaving zero unpinned entries (FR-011; SC-002)

**Checkpoint**: Reproducible, isolated environment available — the foundation other stories run on.

---

## Phase 4: User Story 2 - Run the test suite with one command (Priority: P1)

**Goal**: One command runs the suite with a clear pass/fail and non-zero exit on failure; CI runs the
same on every push/PR.

**Independent Test**: `make test` discovers and passes the trivial test; adding a failing test makes
it exit non-zero; CI runs `make setup` + `make test`.

### Tests for User Story 2 ⚠️ (write first)

- [X] T010 [P] [US2] Write `tests/test_smoke.py` — a trivial passing test proving the harness collects and runs (FR-008)

### Implementation for User Story 2

- [X] T011 [US2] Run `make test`; confirm pytest discovers and passes `test_smoke`. Temporarily add a failing assertion to confirm non-zero exit, then revert (FR-007; SC-003)
- [X] T012 [US2] Create `.github/workflows/ci.yml`: on push + pull_request → checkout → set up Python 3.12 → `make setup` → `make test` (FR-014; SC-007; research.md D10)

**Checkpoint**: Tests run locally and in CI; the test gate is live.

---

## Phase 5: User Story 3 - Clear, layered package structure (Priority: P2)

**Goal**: Two importable architectural layers exist, and the live layer's no-concrete-defence
boundary is enforced by a test.

**Independent Test**: `aatf.live` and `aatf.analysis` import; importing `aatf.live` pulls in no
concrete-defence module.

### Tests for User Story 3 ⚠️ (write first)

- [X] T013 [P] [US3] Write `tests/test_layout.py` — assert `import aatf.live` and `import aatf.analysis` succeed, and that after importing `aatf.live` no concrete-defence module (e.g. dotted name matching `*defence*`/`*suricata*` under `aatf`) is present in `sys.modules` (FR-002, Principle III; contracts/package-layout.md)

### Implementation for User Story 3

- [X] T014 [US3] Run `make test`; confirm `test_layout` passes (boundary holds with the empty skeletons from T005) (SC-004)

**Checkpoint**: Layered layout in place; Principle III boundary guarded by CI from day one.

---

## Phase 6: User Story 4 - Single entrypoint stub (Priority: P3)

**Goal**: The one-command run surface exists and clearly signals "not yet implemented."

**Independent Test**: `make run` exits 0 and prints an explicit not-implemented message.

### Implementation for User Story 4

- [X] T015 [US4] Implement `src/aatf/__main__.py` — print an explicit "experiment loop not yet implemented" message and exit 0 (FR-009; research.md D7)
- [X] T016 [US4] Run `make run`; confirm it invokes `python -m aatf` via `.venv` and exits cleanly with the not-implemented message (SC-005)

**Checkpoint**: Run surface reserved for later features.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Quality baseline, docs, and full-quickstart validation.

- [X] T017 [P] Run `make lint`; fix any ruff lint/format violations so the scaffold reports clean (FR-013; SC-008)
- [X] T018 [P] Update `README.md` — document one-command `setup`/`test`/`run`/`lint`, the `.venv` workflow, and link to `.specify/memory/constitution.md`
- [X] T019 Validate `quickstart.md` end-to-end on a clean checkout: `make setup` → `make test` → `make lint` → `make run`, confirming SC-001 through SC-008

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup. T006 (lock) needs `requirements.in` (T002); T005 needs the dirs (T001).
- **User Stories (Phase 3–6)**: All depend on Foundational. Because validation requires an installed
  environment, **US2/US3/US4 execution depends on US1** (`make setup`). Authoring the test files
  (T010, T013) has no such dependency and can happen earlier.
- **Polish (Phase 7)**: Depends on all stories complete.

### Within Each User Story

- US2/US3: test file written before the run/validation task.
- US1 is the MVP and the practical prerequisite environment for the others.

### Parallel Opportunities

- T002, T003, T004 (Setup) are different files → run in parallel.
- T010 and T013 (test authoring) are different files → run in parallel, and can be written any time
  after T005.
- T017 and T018 (Polish) are different files → run in parallel.

---

## Parallel Example: Setup Phase

```bash
# After T001 creates directories, author the three config files together:
Task: "Create requirements.in (pip-tools, pytest, ruff)"      # T002
Task: "Create .gitignore"                                     # T003
Task: "Create pyproject.toml (python pin, pytest, ruff cfg)"  # T004
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 Setup → Phase 2 Foundational → Phase 3 US1.
2. **STOP and VALIDATE**: `make setup` yields a reproducible, isolated `.venv` with `import aatf`
   working. That alone is a usable foundation for every later feature.

### Incremental Delivery

US1 (reproducible env) → US2 (tests + CI) → US3 (layered boundary) → US4 (run stub) → Polish.
Each adds value without breaking the previous.

---

## Notes

- [P] = different files, no dependencies.
- Network access is required for T006 (lock) and T008 (install). If unavailable, create the files
  and note that lock/install verification is pending an online run.
- Commit after each task or logical group.
- This feature contains no domain logic; the only tests are the harness smoke test and the
  Principle III boundary test.
