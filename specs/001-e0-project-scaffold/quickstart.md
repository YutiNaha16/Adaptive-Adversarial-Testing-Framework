# Quickstart: Project Scaffold

The scaffold gives you a reproducible Python environment, a test harness, and a run entrypoint —
no domain logic yet.

## Prerequisites

- Python 3.12 (CPython 3.1x baseline). Check: `python3.12 --version`.
- GNU Make.

## One-time setup

```bash
make setup        # creates/uses .venv and installs the pinned, hashed dependencies
```

This creates a project-local virtual environment (`.venv`, gitignored) and installs exactly the
versions in `requirements.txt` (fully pinned + hashed) into it, so every machine gets an identical,
isolated environment.

## Run the tests

```bash
make test         # runs pytest; exits non-zero if anything fails
```

Expected: a trivial smoke test and a layout test pass on a clean checkout. The same `make setup` +
`make test` runs in CI on every push/PR (`.github/workflows/ci.yml`).

## Check code quality

```bash
make lint         # ruff lint + format check; exits non-zero on any violation
```

Expected: clean on the scaffold. Run this before committing; CI-style quality is enforced from F01.

## Run the entrypoint (stub)

```bash
make run          # python -m aatf
```

Expected: prints that the experiment loop is not yet implemented, then exits cleanly. Later
features fill this in.

## Change dependencies

1. Edit `requirements.in` (direct dependencies only).
2. Recompile the lock:

   ```bash
   make lock       # pip-compile --generate-hashes
   ```

3. Re-run `make setup`. Commit both `requirements.in` and `requirements.txt`.

## Where code goes

- `src/aatf/live/` — live experiment loop (attacker, executor, feedback). **Never** import a
  concrete defence here.
- `src/aatf/analysis/` — offline analysis (evaluator, explainability, reports).
- `tests/` — pytest suite.

## What's intentionally NOT here

Configuration + seeding (F02), core data contracts (F03), the Docker lab (F04+), and the
experiment loop itself — all delivered by later features.
