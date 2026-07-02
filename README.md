# Adaptive Adversarial Testing Framework

A **safe, simulation-based measurement instrument** that evaluates an intrusion-detection
configuration (Suricata + ET Open) against an *adaptive, learning* attacker and explains the
discovered weaknesses in defender-actionable terms. It is defence-centric — the goal is to
measure and explain *how* defences break so they can be fixed. **It is not an attack tool.**

Development follows a spec-driven workflow. The governing principles live in
[`.specify/memory/constitution.md`](.specify/memory/constitution.md); the feature roadmap is in
[`docs/backlog.md`](docs/backlog.md).

## Status

F01 + F02 complete (Epic E0 — Foundation & Reproducibility). Config loading, seeding, and
run-manifest provenance are operational. No experiment loop yet.

## Requirements

- Python 3.12 (CPython 3.1x baseline)
- GNU Make

## Quickstart

```bash
make setup   # create .venv and install pinned, hashed dependencies (one-time)
make test    # run the test suite
make lint    # check lint + formatting (ruff)
make run     # run the entrypoint stub (prints "not yet implemented")
```

Run `make` (or `make help`) to list all targets.

## Reproducibility

Dependencies are pinned and hash-verified. `requirements.in` is the human-edited source of truth;
`requirements.txt` is the generated, fully pinned + hashed lock installed into a project-local
`.venv`. To change dependencies, edit `requirements.in` then run `make lock` and commit both files.

## Configuration

Edit `config.yaml` at the repo root to tune experiment parameters:

```yaml
episodes: 100            # number of experiment episodes
seed: 42                 # global RNG seed — same seed → same results
output_dir: outputs/run_001   # where run outputs and manifests are written
ruleset_path: /etc/suricata/rules  # Suricata ET Open ruleset directory (used by E1+)
detection_threshold: 0.5  # minimum detection score (used by E6+ evaluator)
```

Before running an experiment, call `seed_everything(cfg.seed)` once — this is the **sole
randomness entry point**; no other code may seed RNGs directly. After each run, `write_manifest()`
produces a timestamped `run_manifest_<ISO>.json` in `output_dir` capturing seed, dependency
versions, git commit, and the full config snapshot for reproducibility auditing.

## Project layout

```
src/aatf/
├── config.py   # ExperimentConfig (Pydantic V2) + load_config()
├── seeding.py  # seed_everything() — sole RNG entry point
├── manifest.py # write_manifest() — timestamped JSON provenance record
├── contracts.py # five frozen Pydantic V2 types: Action, DetectionResult, ContextVector, EpisodeRecord, RunManifest
├── live/       # Live experiment loop — added by later features
│               #   MUST NOT import any concrete defence (constitution Principle III)
└── analysis/   # Offline analysis pipeline — added by later features
tests/          # pytest suite (29 tests)
config.yaml     # example configuration (edit to tune experiments)
```

## License / use

Intended for authorized, isolated security research and education. All attacker behaviour is
defanged and confined to an isolated lab; see the constitution's Safety & Isolation principle.
