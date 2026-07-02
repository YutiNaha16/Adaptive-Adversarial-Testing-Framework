# Feature Specification: Project Scaffold & Pinned Dependencies

**Feature Branch**: `001-e0-project-scaffold`
**Created**: 2026-06-30
**Status**: Draft
**Input**: User description: "Feature F01 (Epic E0 — Foundation & Reproducibility): Project scaffold & pinned dependencies. Establish the Python package layout, pinned dependency management, and the test + entrypoint skeleton that every other feature builds on."

## Clarifications

### Session 2026-06-30

- Q: How should `make setup` isolate the Python environment when installing the pinned dependencies? → A: Create/use a project-local virtual environment (`.venv`) and install into it; `.venv` is gitignored.
- Q: Is an actual CI workflow file a deliverable of F01, or just CI-readiness? → A: Include a minimal CI workflow that runs `make setup` + `make test` on push/PR.
- Q: Should code-quality tooling (lint + format) be part of the scaffold? → A: Yes — add ruff (lint + format) with a `make lint` target and config in `pyproject.toml`.

## User Scenarios & Testing *(mandatory)*

The "users" of this feature are the **project contributors** building later features and the
**automation/CI** that must run the project reproducibly. This is foundational infrastructure:
it delivers a coherent, deterministic starting point, not end-user behaviour.

### User Story 1 - Reproducible environment setup from a clean checkout (Priority: P1)

A contributor clones the repository and, with a single documented command, installs the exact
same dependency versions every time, on any machine, with no ambiguity about what is installed.

**Why this priority**: Reproducibility is a NON-NEGOTIABLE project principle and a Phase 1 gate
criterion. Every later feature depends on a deterministic environment; without it, no result the
project produces can be trusted or replicated.

**Independent Test**: From a clean checkout, run the documented setup command and confirm it
installs a fully-pinned dependency set; repeating it on another machine yields the identical
versions.

**Acceptance Scenarios**:

1. **Given** a clean checkout, **When** the contributor runs the setup command, **Then** all
   dependencies install at exact pinned versions with no unpinned/floating resolutions.
2. **Given** the pinned dependency lock, **When** it is inspected, **Then** every transitive
   dependency is pinned to a specific version (and integrity-verifiable), traceable to a
   human-edited top-level dependency list.
3. **Given** two different machines running the same Python 3.1x baseline, **When** each runs
   setup, **Then** the resolved dependency versions are identical.

---

### User Story 2 - Run the test suite with one command (Priority: P1)

A contributor (or CI) runs a single command to execute the automated test suite and gets a clear
pass/fail result, so that every later feature can be developed test-first.

**Why this priority**: The project mandates a test-first discipline. A runnable test harness must
exist before any feature contract can be locked by tests.

**Independent Test**: Run the test command on a clean checkout; at least one trivial test
collects and passes, and the command exits non-zero if any test fails.

**Acceptance Scenarios**:

1. **Given** an installed environment, **When** the contributor runs the test command, **Then**
   the test runner discovers and executes tests and reports a clear pass/fail summary.
2. **Given** a passing baseline, **When** a deliberately failing test is added, **Then** the test
   command exits with a non-zero status.

---

### User Story 3 - Clear, layered package structure to build into (Priority: P2)

A contributor opening the repository finds package locations that mirror the system architecture
(a live experiment loop layer and an offline analysis layer), so they know exactly where a new
feature's code belongs without guessing or restructuring later.

**Why this priority**: A correct boundary up front prevents the live-loop layer from coupling to
a specific defence (a NON-NEGOTIABLE architectural principle) and avoids costly reorganisation as
features land. It is P2 because it enables clean growth but does not itself run anything.

**Independent Test**: Inspect the repository; confirm distinct, importable package locations
exist for the live-loop layer and the offline-analysis layer, each importable in a test.

**Acceptance Scenarios**:

1. **Given** the scaffold, **When** a contributor imports the live-loop and offline-analysis
   packages, **Then** both import successfully as empty, well-named skeletons.
2. **Given** the scaffold, **When** the layout is reviewed, **Then** no live-loop package
   references or depends on any concrete defence implementation.

---

### User Story 4 - Single entrypoint stub for the eventual experiment run (Priority: P3)

A contributor runs the project's "run" command and sees a clearly-marked, not-yet-implemented
entrypoint, establishing the one-command run surface that later features will fill in.

**Why this priority**: It reserves the one-command run contract (a reproducibility requirement)
without implementing experiment logic. P3 because it is a placeholder, not functionality.

**Independent Test**: Run the run command; it executes the stub and exits cleanly with a message
indicating the experiment loop is not yet implemented.

**Acceptance Scenarios**:

1. **Given** the scaffold, **When** the contributor runs the run command, **Then** it invokes a
   single documented entrypoint and exits cleanly with an explicit "not yet implemented" signal.

---

### Edge Cases

- **Wrong Python version**: When a contributor uses a Python version outside the supported 3.1x
  baseline, setup MUST surface a clear, early indication rather than installing silently against
  an unsupported interpreter.
- **Stale lock**: When the human-edited dependency list changes but the pinned lock is not
  regenerated, there MUST be a documented, repeatable way to recompile the lock so the two cannot
  silently diverge.
- **Generated artifacts in version control**: When tests or runs produce caches, logs, or
  reports, these MUST be ignored by version control so they never pollute the repository or a
  diff.
- **Running tests before setup**: When the test command is run without dependencies installed,
  the failure MUST be understandable (clearly about missing setup), not a cryptic error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository MUST provide importable package locations that mirror the two
  architectural layers — the live experiment loop and the offline analysis pipeline — as empty,
  well-named skeletons ready to receive later features.
- **FR-002**: The live-loop package skeleton MUST NOT contain or depend on any concrete defence
  implementation, preserving the pluggable-defence boundary from the outset.
- **FR-003**: Top-level (direct) dependencies MUST be declared in a single human-edited list that
  is the source of truth for what the project depends on.
- **FR-004**: A fully-pinned, integrity-verifiable lock of all dependencies (direct and
  transitive) MUST be generated from that list and committed, so installs are identical across
  machines and time.
- **FR-005**: The project MUST target the Python 3.1x baseline, and this expectation MUST be
  recorded where contributors and tooling can discover it.
- **FR-006**: A single documented command MUST install the project into a working state using the
  pinned lock, installing into a **project-local virtual environment** (`.venv`) that it creates
  or reuses, so installation never pollutes or depends on the system/active interpreter.
- **FR-007**: A single documented command MUST run the automated test suite, returning a clear
  pass/fail result and a non-zero exit code on failure.
- **FR-008**: The test harness MUST be configured and include at least one trivial passing test
  that proves the harness works on a clean checkout.
- **FR-009**: A single documented command MUST invoke a project entrypoint stub that exits cleanly
  and clearly signals that the experiment loop is not yet implemented.
- **FR-010**: Version control MUST ignore generated and environment-specific artifacts
  (bytecode caches, virtual environments, logs, and generated reports).
- **FR-011**: There MUST be a documented, repeatable procedure to regenerate the pinned lock when
  the top-level dependency list changes.
- **FR-012**: The setup, test, run, and lint commands MUST be discoverable from one place (a single
  task surface) so a newcomer can find them without reading the whole codebase.
- **FR-013**: The project MUST provide code-quality tooling (linting and formatting) exposed via a
  single documented command, with its configuration recorded in project metadata, so every later
  feature inherits a consistent quality baseline.
- **FR-014**: A continuous-integration workflow MUST be included that, on push and pull request,
  installs via the pinned lock and runs the test suite, failing the build on any test failure — so
  reproducibility and the test gate are enforced automatically from the first feature.
- **FR-015**: Version control MUST ignore the project-local virtual environment directory so it is
  never tracked.

### Key Entities *(include if feature involves data)*

- **Top-level dependency list**: The human-curated set of direct dependencies; the source of
  truth from which the pinned lock is derived.
- **Pinned dependency lock**: The fully-resolved, integrity-verifiable record of every dependency
  version installed; the artifact that guarantees identical environments.
- **Package layer skeletons**: The empty, importable package locations representing the live-loop
  and offline-analysis architectural layers.
- **Task surface**: The single, discoverable list of project commands (setup, test, run, lint, and
  the lock-regeneration command).
- **Project virtual environment**: The project-local, gitignored environment (`.venv`) into which
  `make setup` installs the pinned dependencies, guaranteeing isolation from the system interpreter.
- **CI workflow**: The automation definition that, on push/PR, installs from the pinned lock and
  runs the test suite, enforcing reproducibility and the test gate.
- **Code-quality configuration**: The lint/format tool configuration (recorded in project metadata)
  that establishes the shared quality baseline for all later code.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A contributor can go from a clean checkout to an installed, test-passing environment
  by running at most two documented commands (setup, then test).
- **SC-002**: Running setup on two separate machines (same Python 3.1x baseline) yields identical
  resolved dependency versions, with zero unpinned dependencies in the committed lock.
- **SC-003**: The test command discovers and runs the suite, passes on a clean checkout, and exits
  non-zero when any test fails — verifiable in a single run each way.
- **SC-004**: The live-loop and offline-analysis packages both import successfully, and no
  reviewer can find a live-loop dependency on a concrete defence (architectural boundary holds).
- **SC-005**: The run command executes the entrypoint stub and exits cleanly with an explicit
  not-yet-implemented signal.
- **SC-006**: A newcomer can discover the setup, test, run, and lint commands from a single task
  surface without reading source code.
- **SC-007**: On push/pull request, the CI workflow installs from the pinned lock and runs the test
  suite to a green result on a clean checkout, and turns red if any test fails.
- **SC-008**: The lint command runs the quality tooling over the codebase and reports a clean result
  on the scaffold (zero violations), establishing the baseline for later features.

## Assumptions

- The scaffold intentionally contains **no domain/business logic**; configuration + seeding (F02),
  core data contracts (F03), the Docker lab (F04+), and the experiment loop are out of scope and
  handled by later features.
- "Python 3.1x" refers to the current CPython 3.1x baseline the project standardises on; the exact
  minor version is recorded during planning/implementation.
- A Makefile-style task runner is an acceptable "single task surface"; the precise tool is an
  implementation choice deferred to planning, provided it satisfies FR-012.
- Code-quality tooling is satisfied by ruff (combined linter + formatter); the `make lint` target
  checks formatting and lint rules. Exact rule selection is an implementation detail for planning.
- The CI workflow targets the project's hosting platform's standard CI (e.g., a GitHub Actions
  workflow); the concrete provider/syntax is an implementation detail, provided it satisfies FR-014.
- Dependency pinning with integrity verification (hashes) is expected; the specific tooling
  (e.g. a pip-tools-style compile workflow) is an implementation detail for planning.
- This feature does not stand up any container or network; it only prepares the repository so that
  later features can.

## Dependencies

- **Upstream**: None. This is the first feature in the backlog; nothing precedes it.
- **Downstream**: All subsequent features (F02 onward) depend on this scaffold for their package
  location, dependency management, test harness, and run/task surface.
