# Adaptive-Adversarial-Testing-Framework Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-06-30

## Active Technologies
- Python 3.12 (pinned per F01 scaffold) + Pydantic V2 (`pydantic`), PyYAML (`pyyaml`), NumPy (`numpy`) — all new additions to `requirements.in`; existing: pip-tools, pytest, ruff (002-e0-config-seeding)
- Local filesystem — YAML input (`config.yaml`), JSON output (`run_manifest_<ISO>.json` in `output_dir`) (002-e0-config-seeding)
- Python 3.12 (pinned per F01) + Pydantic V2 (`pydantic`) — already in `.venv` from F02; stdlib (003-e0-core-contracts)
- N/A — pure in-memory data shapes; serialisation is via `model_dump(mode="json")` (003-e0-core-contracts)
- Shell (bash/sh) for scripts; YAML for Compose config; no Python changes + Docker Engine (host prerequisite); Docker Compose V2 plugin; `alpine:3.19` (pinned stub image) (004-e1-docker-lab)
- N/A — no persistent volumes at this stage (004-e1-docker-lab)
- Python 3.12 (pinned per F01) + PyYAML (already in requirements.txt — for parsing docker-compose.yml); (005-e1-isolation-verify)
- N/A — reads `lab/docker-compose.yml` (owned by F04); writes nothing (005-e1-isolation-verify)
- Shell (bash/sh) for all new scripts; YAML for Docker Compose and + Docker Engine (≥ 20); Docker Compose V2; `jasonish/suricata:7.0.5` (006-e1-suricata-etopen)
- Named Docker volume `aatf-eve` for eve.json; `lab/rules/disabled.conf` (006-e1-suricata-etopen)

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
- 006-e1-suricata-etopen: Added Shell (bash/sh) for all new scripts; YAML for Docker Compose and + Docker Engine (≥ 20); Docker Compose V2; `jasonish/suricata:7.0.5`
- 005-e1-isolation-verify: Added Python 3.12 (pinned per F01) + PyYAML (already in requirements.txt — for parsing docker-compose.yml);
- 004-e1-docker-lab: Added Shell (bash/sh) for scripts; YAML for Compose config; no Python changes + Docker Engine (host prerequisite); Docker Compose V2 plugin; `alpine:3.19` (pinned stub image)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
