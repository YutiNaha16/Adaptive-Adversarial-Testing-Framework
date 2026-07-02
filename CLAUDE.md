# Adaptive-Adversarial-Testing-Framework Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-06-30

## Active Technologies
- Python 3.12 (pinned per F01 scaffold) + Pydantic V2 (`pydantic`), PyYAML (`pyyaml`), NumPy (`numpy`) — all new additions to `requirements.in`; existing: pip-tools, pytest, ruff (002-e0-config-seeding)
- Local filesystem — YAML input (`config.yaml`), JSON output (`run_manifest_<ISO>.json` in `output_dir`) (002-e0-config-seeding)

- Python 3.12 (current CPython 3.1x baseline; confirmed `python3.12` available) + pip-tools (dependency compilation/pinning), pytest (test harness). No (001-e0-project-scaffold)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.12 (current CPython 3.1x baseline; confirmed `python3.12` available): Follow standard conventions

## Recent Changes
- 002-e0-config-seeding: Added Python 3.12 (pinned per F01 scaffold) + Pydantic V2 (`pydantic`), PyYAML (`pyyaml`), NumPy (`numpy`) — all new additions to `requirements.in`; existing: pip-tools, pytest, ruff

- 001-e0-project-scaffold: Added Python 3.12 (current CPython 3.1x baseline; confirmed `python3.12` available) + pip-tools (dependency compilation/pinning), pytest (test harness). No

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
