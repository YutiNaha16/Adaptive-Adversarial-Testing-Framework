# Adaptive Adversarial Testing Framework

A **safe, simulation-based measurement instrument** that evaluates an intrusion-detection
configuration (Suricata + ET Open) against an *adaptive, learning* attacker and explains the
discovered weaknesses in defender-actionable terms. It is defence-centric — the goal is to
measure and explain *how* defences break so they can be fixed. **It is not an attack tool.**

Development follows a spec-driven workflow. The governing principles live in
[`.specify/memory/constitution.md`](.specify/memory/constitution.md); the feature roadmap is in
[`docs/backlog.md`](docs/backlog.md).

## Status

Early scaffold (Feature F01). No experiment logic yet — this repository currently provides the
reproducible project foundation that later features build on.

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

## Project layout

```
src/aatf/
├── live/       # Live experiment loop (attacker, executor, feedback) — added by later features
│               #   MUST NOT import any concrete defence (constitution Principle III)
└── analysis/   # Offline analysis (evaluator, explainability, report) — added by later features
tests/          # pytest suite
```

## License / use

Intended for authorized, isolated security research and education. All attacker behaviour is
defanged and confined to an isolated lab; see the constitution's Safety & Isolation principle.
