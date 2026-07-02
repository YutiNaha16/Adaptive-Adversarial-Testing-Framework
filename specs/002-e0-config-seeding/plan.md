# Implementation Plan: Configuration & Seed Management

**Branch**: `002-e0-config-seeding` | **Date**: 2026-07-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/002-e0-config-seeding/spec.md`

## Summary

Deliver three pure-Python infrastructure modules — `config.py`, `seeding.py`, `manifest.py` — that together make every AATF experiment deterministic and auditable. Uses Pydantic V2 for validated config loading from YAML (PyYAML), a single `seed_everything()` function as the sole RNG entry point (Python random + NumPy + optional PyTorch stub), and a timestamped JSON manifest writer that captures full provenance. Three new `requirements.in` entries: `pydantic`, `pyyaml`, `numpy`.

## Technical Context

**Language/Version**: Python 3.12 (pinned per F01 scaffold)
**Primary Dependencies**: Pydantic V2 (`pydantic`), PyYAML (`pyyaml`), NumPy (`numpy`) — all new additions to `requirements.in`; existing: pip-tools, pytest, ruff
**Storage**: Local filesystem — YAML input (`config.yaml`), JSON output (`run_manifest_<ISO>.json` in `output_dir`)
**Testing**: pytest (existing from F01); three new test files: `test_config.py`, `test_seeding.py`, `test_manifest.py`
**Target Platform**: Linux (CI: ubuntu-latest via GitHub Actions); developer machines
**Project Type**: Single project, src-layout (`src/aatf/` per F01)
**Performance Goals**: Config load < 100ms; seeding < 10ms; manifest write < 200ms — all trivially achievable; no performance gate
**Constraints**: No external network access; no Docker dependency in this feature; must not import any concrete defence module (Principle III); must pass existing `test_layout.py` boundary test after new modules are added
**Scale/Scope**: 3 new source modules, 3 new test files, 1 example config file, updated requirements.in/lock

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate? | Status | Notes |
|-----------|-------|--------|-------|
| I — Safety & Isolation | — | ✅ PASS | No network access, no Docker, no action execution in this feature |
| II — Reproducibility (NON-NEGOTIABLE) | ✅ GATE | ✅ PASS | `seed_everything` is the sole RNG entry point; FR-012 enforced by static-analysis test; timestamped manifest prevents overwrite; manifest captures seed + dependency versions + git commit |
| III — Pluggable Defence (NON-NEGOTIABLE) | ✅ GATE | ✅ PASS | `config.py`, `seeding.py`, `manifest.py` import no concrete defence; `aatf.live` still imports no defence (existing test_layout boundary test remains green) |
| IV — Scientific Validity | — | ✅ PASS | Tests written before implementation for all three module contracts; seeding correctness verified by identical-sequence test |
| V — Explainability | — | ✅ N/A | No explainability output in this feature |
| VI — Observability | — | ✅ PARTIAL | Manifest IS the primary observability primitive for this feature; structured logging deferred to F13 (experiment engine) — acceptable at this stage |
| VII — Phased Delivery | — | ✅ PASS | Phase 1 feature only; PyTorch seeding is a no-op stub (no Phase 2 code imported) |

**Gate result: PASS — no violations. Proceed to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/002-e0-config-seeding/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/           ← Phase 1 output
│   ├── config-api.md
│   ├── seeding-api.md
│   └── manifest-api.md
├── checklists/
│   └── requirements.md  ← already complete
└── tasks.md             ← /sp.tasks output (not this command)
```

### Source Code (repository root)

```text
src/aatf/
├── __init__.py           # unchanged (F01) — exposes __version__
├── __main__.py           # unchanged (F01) — entrypoint stub
├── config.py             # NEW — ExperimentConfig (Pydantic V2) + load_config()
├── seeding.py            # NEW — seed_everything(seed: int)
├── manifest.py           # NEW — write_manifest()
├── live/__init__.py      # unchanged (F01 skeleton)
└── analysis/__init__.py  # unchanged (F01 skeleton)

tests/
├── __init__.py           # unchanged (F01)
├── test_smoke.py         # unchanged (F01)
├── test_layout.py        # unchanged (F01) — boundary test still passes
├── test_config.py        # NEW — US1 contract tests (load, validate, error paths)
├── test_seeding.py       # NEW — US2 contract tests (determinism, idempotency, torch stub)
└── test_manifest.py      # NEW — US3 contract tests (schema, timestamp, no-overwrite)

config.yaml               # NEW — example config at repo root (not committed to .gitignore)
requirements.in           # UPDATED — add pydantic, pyyaml, numpy
requirements.txt          # REGENERATED — make lock
```

**Structure Decision**: Single project, src-layout (same as F01). All new modules go directly in `src/aatf/` — no sub-packages needed at this stage. Tests mirror module names (`test_config.py` ↔ `config.py`).

## Complexity Tracking

No constitution violations — table not required.
