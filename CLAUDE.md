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
- Python 3.12 (pinned per F01) + stdlib only — `dataclasses`, `ipaddress`, `typing`; Pydantic V2 (already in `.venv`) for `Action` contract via F03 (010-e2-action-library)
- N/A — pure in-memory module-level constant (010-e2-action-library)
- Python 3.12 (pinned per F01) + stdlib only — `socket`, `http.client`, `random`, `ipaddress`, `struct`, `dataclasses`, `time`; Pydantic V2 (already in `.venv`) for `Action` via F03 (011-e2-action-executor)
- N/A — stateless per-call execution; no persistence (011-e2-action-executor)
- Python 3.12 (pinned per F01) + numpy (already in requirements); stdlib: dataclasses, time (013-e4-context-vector)
- N/A — pure in-memory function (013-e4-context-vector)
- Python 3.12 (pinned per F01) + stdlib only — no imports required (014-e4-reward-function)
- N/A — pure function (014-e4-reward-function)
- Python 3.12 (pinned per F01) + stdlib only — `dataclasses`; existing project deps: `aatf.attack_graph` (F09), `aatf.context_vector` (F13) (015-e4-feedback-collector)
- N/A — pure in-memory mutation; no persistence (015-e4-feedback-collector)
- Python 3.12 (pinned per F01) + stdlib only — `dataclasses`, `datetime`, `typing`; existing project deps: Pydantic V2 (for `Action` construction), numpy (unused here) (016-e4-episode-loop)
- N/A — pure in-memory orchestration; no persistence (016-e4-episode-loop)
- Python 3.12 (pinned per F01) + numpy (already in requirements); stdlib only — `math` (for sqrt) (017-e4-attacker-update)
- N/A — pure in-memory; no file I/O (017-e4-attacker-update)
- Python 3.12 (pinned per F01) + stdlib only — `abc`, `random`, `itertools`; numpy (already in requirements); `aatf.linucb.LinUCBModel` (from spec-017) (018-e5-attacker-baselines)
- Python 3.12 (pinned per F01) + stdlib only — `dataclasses`; `aatf.episode.StepRecord` (from F16, already in codebase). No new pip dependencies. (020-e6-evaluator-metrics)
- Python 3.12 (pinned per F01 scaffold) + numpy (already in venv), scipy>=1.12 (NEW — must add to requirements.in), dataclasses + typing (stdlib) (021-e6-statistical-rigor)
- Python 3.12 (pinned per F01 scaffold) + stdlib only (`dataclasses`); `aatf.metrics` (F20), `aatf.action_library` (F10) (022-e6-explainability-engine)
- Python 3.12 (pinned per F01 scaffold) + `jinja2>=3.1` (NEW); stdlib: `pathlib`, `datetime`; `aatf.metrics` (F20), `aatf.statistics` (F21), `aatf.explainability` (F23), `aatf.action_library` (F10) (023-e6-report-generator)
- Local filesystem — writes `output_path` (caller-supplied); reads template from `src/aatf/templates/report.md.j2` (023-e6-report-generator)
- Python 3.12 (pinned per F01 scaffold) + stdlib only — `dataclasses`; `aatf.explainability.ActionExplanation` (F23) (024-e6-ground-truth-validation)

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
- 024-e6-ground-truth-validation: Added Python 3.12 (pinned per F01 scaffold) + stdlib only — `dataclasses`; `aatf.explainability.ActionExplanation` (F23)
- 023-e6-report-generator: Added Python 3.12 (pinned per F01 scaffold) + `jinja2>=3.1` (NEW); stdlib: `pathlib`, `datetime`; `aatf.metrics` (F20), `aatf.statistics` (F21), `aatf.explainability` (F23), `aatf.action_library` (F10)
- 022-e6-explainability-engine: Added Python 3.12 (pinned per F01 scaffold) + stdlib only (`dataclasses`); `aatf.metrics` (F20), `aatf.action_library` (F10)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
