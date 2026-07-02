# Implementation Plan: Core Data Contracts

**Branch**: `003-e0-core-contracts` | **Date**: 2026-07-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/003-e0-core-contracts/spec.md`

## Summary

Define five frozen Pydantic V2 types (`Action`, `DetectionResult`, `ContextVector`,
`EpisodeRecord`, `RunManifest`) in a single flat module `src/aatf/contracts.py`. No new
dependencies — Pydantic V2 is already installed from F02. The critical design constraint is
that `DetectionResult` must unify binary (Suricata) and continuous (ML) detection modes in
one type, and `EpisodeRecord` must round-trip through JSONL without information loss.

## Technical Context

**Language/Version**: Python 3.12 (pinned per F01)
**Primary Dependencies**: Pydantic V2 (`pydantic`) — already in `.venv` from F02; stdlib
only (`datetime`, `typing`, `Annotated`) for everything else. No new packages required.
**Storage**: N/A — pure in-memory data shapes; serialisation is via `model_dump(mode="json")`
and `model_validate()` (Pydantic built-ins), not a storage layer.
**Testing**: pytest (already configured); `make test` is the single test runner.
**Target Platform**: Linux / Python 3.12, same environment as F01/F02.
**Performance Goals**: N/A — construction of small data objects; latency is negligible.
**Constraints**: `contracts.py` MUST import nothing from defence, attacker, or loop modules
(FR-009, enforced by static-analysis test FR-010). All five types MUST be frozen.
**Scale/Scope**: One flat module (~120–150 lines); five types; ~25–30 tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I — Safety & Isolation | ✅ PASS | Pure data shapes — no execution, no network, no exploit code possible |
| II — Reproducibility | ✅ PASS | Frozen types + validated fields; construction from same input always yields equal output |
| III — Pluggable Defence | ✅ PASS | `contracts.py` is the shared vocabulary layer — zero imports from any concrete defence; `DetectionResult.coverage` enables blind-spot classification independent of Suricata internals |
| IV — Scientific Validity / Test-first | ✅ PASS | Tests written before implementation for all five type contracts and the JSONL round-trip |
| V — Explainability | ✅ PASS | `DetectionResult.coverage` field (`"covered"/"uncovered"/"unknown"`) directly feeds the explainability engine (F23) |
| VI — Observability | ✅ PASS | `EpisodeRecord` JSONL round-trip enables full offline replay without re-running the lab |
| VII — Phased Delivery | ✅ PASS | No Phase 2 code; `DetectionResult` unified type enables Phase 2 ML score without schema change |

**Gate result: ALL PASS — proceed to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/003-e0-core-contracts/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── contracts-api.md # Construction API for all five types
└── tasks.md             # Phase 2 output (/sp.tasks — not created here)
```

### Source Code

```text
src/aatf/
├── contracts.py         # NEW — five frozen Pydantic V2 types (this feature)
├── config.py            # existing (F02)
├── seeding.py           # existing (F02)
└── manifest.py          # existing (F02)

tests/
├── test_contracts.py    # NEW — all contract type tests (this feature)
├── test_config.py       # existing
├── test_seeding.py      # existing
├── test_manifest.py     # existing
├── test_layout.py       # existing
└── test_smoke.py        # existing
```

**Structure Decision**: Single project, src-layout. One new source file (`contracts.py`)
and one new test file (`test_contracts.py`). All existing files unchanged.

## Complexity Tracking

No constitution violations — table not required.
