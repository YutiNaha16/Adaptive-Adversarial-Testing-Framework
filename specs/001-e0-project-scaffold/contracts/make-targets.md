# Contract: Make Targets (the task surface)

This is the command-interface contract for the scaffold. Each target has a defined behaviour and
an observable outcome a test or a human can verify. "API contracts" for an infra feature are these
commands, not HTTP endpoints.

## `make setup`

- **Purpose**: Install the project into a working state from the pinned lock, in an isolated env.
- **Behaviour**: Creates/reuses a project-local virtual environment at `.venv`
  (`python3.12 -m venv .venv`), then installs into it via
  `.venv/bin/pip install --require-hashes -r requirements.txt`, then installs the local package
  editable (`.venv/bin/pip install -e .`) so `aatf` is importable.
- **Success**: Exit 0; afterwards `.venv/bin/python -c "import aatf"` succeeds.
- **Failure modes**: Missing/mismatched hashes → pip aborts (fail closed). Wrong Python baseline →
  surfaced early.
- **Satisfies**: FR-005, FR-006, FR-015; SC-001, SC-002.

## `make test`

- **Purpose**: Run the automated test suite.
- **Behaviour**: Runs `pytest` over `tests/`.
- **Success**: Exit 0 when all tests pass.
- **Failure**: Exit non-zero if any test fails (verified by temporarily adding a failing test).
- **Satisfies**: FR-007, FR-008; SC-003.

## `make run`

- **Purpose**: Invoke the project entrypoint.
- **Behaviour**: Runs `.venv/bin/python -m aatf`.
- **Success**: Exit 0; prints an explicit message that the experiment loop is not yet implemented.
- **Satisfies**: FR-009; SC-005.

## `make lint`

- **Purpose**: Check code quality (lint + formatting) across the codebase.
- **Behaviour**: Runs `ruff check .` and `ruff format --check .` using the `.venv` interpreter.
- **Success**: Exit 0 when there are zero lint violations and formatting is already correct.
- **Failure**: Exit non-zero on any violation or formatting drift (used by contributors and CI).
- **Satisfies**: FR-013; SC-008.

## `make lock`

- **Purpose**: Regenerate the pinned lock from the human-edited list.
- **Behaviour**: Runs `pip-compile --generate-hashes requirements.in -o requirements.txt`.
- **Success**: Exit 0; `requirements.txt` is fully pinned + hashed and reflects `requirements.in`.
- **Satisfies**: FR-003, FR-004, FR-011.

## CI workflow (`.github/workflows/ci.yml`)

- **Purpose**: Enforce reproducibility + the test gate automatically.
- **Behaviour**: On push and pull_request — checkout → set up Python 3.12 → `make setup` →
  `make test`.
- **Success**: Green when the pinned install succeeds and all tests pass; red if any test fails.
- **Satisfies**: FR-014; SC-007.

## Discoverability

- All targets are defined in one `Makefile`; `make` with no/`help` target lists setup, test, run,
  lint, and lock.
- **Satisfies**: FR-012; SC-006.
