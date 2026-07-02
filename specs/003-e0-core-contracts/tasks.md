---
description: "Task list for 003-e0-core-contracts"
---

# Tasks: Core Data Contracts

**Input**: Design documents from `specs/003-e0-core-contracts/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/contracts-api.md

**Tests**: Test tasks ARE included — constitution Principle IV (test-first) and the spec
mandate tests for all five type contracts. The FR-010 static isolation guard (no forbidden
imports in contracts.py) mirrors the FR-012 pattern from F02.

**Organization**: Grouped by the three user stories from spec.md. Note: `ContextVector`
(technically US3) is implemented in Phase 4 alongside US2 (EpisodeRecord) because
`EpisodeRecord` nests `ContextVector` — writing EpisodeRecord tests without a real
ContextVector would require overly complex stubs. `RunManifest` (the rest of US3) is
implemented in Phase 5 as it has no inter-type dependencies.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US3 per spec.md

## Path Conventions

Single project, src-layout: `src/aatf/`, tests at `tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm no new dependencies are needed and create the module skeleton.

- [X] T001 Verify Pydantic V2 is installed in `.venv` by running `.venv/bin/python -c "import pydantic; print(pydantic.__version__)"` — must print a 2.x version. No `requirements.in` changes needed.
- [X] T002 Create `src/aatf/contracts.py` with shared imports only (no types yet): `from __future__ import annotations`, `from datetime import datetime`, `from typing import Any, Literal, Annotated`, `from pydantic import BaseModel, ConfigDict, Field`. Leave the rest of the file empty.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No additional foundational work beyond Phase 1 — all infrastructure (Pydantic V2,
pytest, ruff, src-layout) already exists from F01/F02.

**Checkpoint**: `src/aatf/contracts.py` exists with imports; `make test` still shows 29 passed.

---

## Phase 3: User Story 1 — Action and Detection Exchange Types (Priority: P1) 🎯 MVP

**Goal**: `Action` and `DetectionResult` are importable, validated, frozen, and fully tested.
`DetectionResult` accepts binary mode, continuous mode, and both simultaneously.

**Independent Test**: `make test` passes all 12 new `test_contracts.py` tests for
Action and DetectionResult; invalid inputs raise `ValidationError` naming the offending field;
frozen assignment raises `ValidationError`.

### Tests for User Story 1 ⚠️ (write first — must FAIL before T005)

- [X] T003 [US1] Write `tests/test_contracts.py` with 12 test cases for `Action` (T-A1 through
  T-A5) and `DetectionResult` (T-DR1 through T-DR7) from `specs/003-e0-core-contracts/contracts/contracts-api.md`:
  - `test_action_valid` — construct with all fields → frozen instance, correct values
  - `test_action_missing_action_id` — omit `action_id` → `ValidationError` naming `action_id`
  - `test_action_missing_category` — omit `category` → `ValidationError` naming `category`
  - `test_action_empty_parameters` — `parameters={}` → valid (no params allowed)
  - `test_action_is_frozen` — assign `action.category = "x"` after construction → `ValidationError`
  - `test_detection_binary_mode` — `alerted=True, rule_ids=["SID:2100498"], anomaly_score=0.0, coverage="covered"` → valid
  - `test_detection_continuous_mode` — `alerted=True, rule_ids=[], anomaly_score=0.87, coverage="covered"` → valid
  - `test_detection_both_modes` — `alerted=True, rule_ids=["SID:1234"], anomaly_score=0.91, coverage="covered"` → valid
  - `test_detection_undetected` — `alerted=False, rule_ids=[], anomaly_score=0.0, coverage="uncovered"` → valid
  - `test_detection_score_too_high` — `anomaly_score=1.5` → `ValidationError` naming `anomaly_score`
  - `test_detection_bad_coverage` — `coverage="maybe"` → `ValidationError` naming `coverage`
  - `test_detection_score_negative` — `anomaly_score=-0.1` → `ValidationError` naming `anomaly_score`
  Import: `from aatf.contracts import Action, DetectionResult`. Use `datetime.now(UTC)` for timestamps.

- [X] T004 [US1] Run `make test` — confirm exactly 12 new tests FAIL (ImportError or AttributeError
  because types don't exist yet) and all 29 prior tests still pass. Fix if prior tests break.

### Implementation for User Story 1

- [X] T005 [US1] Implement `Action` and `DetectionResult` in `src/aatf/contracts.py`:
  - `Action(BaseModel)` with `model_config = ConfigDict(frozen=True)` and fields:
    `action_id: str`, `category: str`, `parameters: dict[str, Any]`, `timestamp: datetime`.
  - `DetectionResult(BaseModel)` with `model_config = ConfigDict(frozen=True)` and fields:
    `alerted: bool`, `rule_ids: list[str]`,
    `anomaly_score: float = Field(ge=0.0, le=1.0)`,
    `coverage: Literal["covered", "uncovered", "unknown"]`.

- [X] T006 [US1] Run `make test` — confirm all 12 Action/DetectionResult tests pass and all 29
  prior tests still pass (41 total). Fix any failures before proceeding.

**Checkpoint**: `Action` and `DetectionResult` functional and tested — the core exchange types
for the experiment loop are locked.

---

## Phase 4: User Story 2 — EpisodeRecord JSONL Observability (Priority: P1)

**Goal**: `EpisodeRecord` is importable, frozen, and round-trips through JSONL without
information loss. `ContextVector` is implemented here as a prerequisite (it is nested inside
`EpisodeRecord`; its own test suite is in Phase 5 / US3).

**Independent Test**: `make test` passes all 15 new tests (8 ContextVector + 7 EpisodeRecord);
`EpisodeRecord.model_dump(mode="json")` → `json.dumps` → `json.loads` → `model_validate`
produces a field-for-field equal instance.

### Tests for User Story 2 ⚠️ (write first — must FAIL before T010)

- [X] T007 [US2] Append 8 `ContextVector` test cases to `tests/test_contracts.py` (T-CV1 through
  T-CV8 from contracts-api.md). ContextVector is authored here because EpisodeRecord nests it:
  - `test_context_vector_valid` — all fields valid → frozen instance
  - `test_context_vector_alert_history_valid` — `alert_history=[0.0, 1.0, 0.0]` → valid
  - `test_context_vector_alert_history_out_of_range` — `alert_history=[0.0, 1.5, 0.0]` → `ValidationError`
  - `test_context_vector_attack_progress_negative` — `attack_progress=-0.1` → `ValidationError`
  - `test_context_vector_current_stage_out_of_range` — `current_stage=4` → `ValidationError`
  - `test_context_vector_technique_rates_out_of_range` — `technique_detection_rates={"ssh": 1.7}` → `ValidationError`
  - `test_context_vector_time_negative` — `time_since_last_alert=-1.0` → `ValidationError`
  - `test_context_vector_empty_technique_rates` — `technique_detection_rates={}` → valid
  Import: `from aatf.contracts import ContextVector`.

- [X] T008 [US2] Append 7 `EpisodeRecord` test cases to `tests/test_contracts.py` (T-ER1 through
  T-ER7 from contracts-api.md):
  - `test_episode_record_valid` — all fields valid → frozen instance
  - `test_episode_record_negative_step` — `step=-1` → `ValidationError` naming `step`
  - `test_episode_record_any_reward` — `reward=999.9` → valid (no reward bound)
  - `test_episode_record_bad_reward_type` — `reward="high"` → `ValidationError` naming `reward`
  - `test_episode_record_jsonl_roundtrip` — `model_dump(mode="json")` → `json.dumps` →
    `json.loads` → `EpisodeRecord.model_validate(data)` → assert `restored == record`
  - `test_episode_record_jsonl_multi_line` — write 3 records to a tmp JSONL file (one per line),
    read back and reconstruct all 3, assert each equals its original
  - `test_episode_record_missing_episode_id` — omit `episode_id` → `ValidationError`
  Import: `from aatf.contracts import EpisodeRecord`. Use `tmp_path` pytest fixture for JSONL files.

- [X] T009 [US2] Run `make test` — confirm exactly 15 new tests FAIL and all 41 prior tests
  pass. Fix if prior tests break.

### Implementation for User Story 2

- [X] T010 [US2] Implement `ContextVector` in `src/aatf/contracts.py`:
  - `ContextVector(BaseModel)` with `model_config = ConfigDict(frozen=True)` and fields:
    `alert_history: list[Annotated[float, Field(ge=0.0, le=1.0)]]`,
    `attack_progress: float = Field(ge=0.0, le=1.0)`,
    `current_stage: int = Field(ge=0, le=3)`,
    `technique_detection_rates: dict[str, Annotated[float, Field(ge=0.0, le=1.0)]]`,
    `time_since_last_alert: float = Field(ge=0.0)`.

- [X] T011 [US2] Implement `EpisodeRecord` in `src/aatf/contracts.py`:
  - `EpisodeRecord(BaseModel)` with `model_config = ConfigDict(frozen=True)` and fields:
    `episode_id: str`, `step: int = Field(ge=0)`, `action: Action`,
    `detection: DetectionResult`, `reward: float`, `context_before: ContextVector`,
    `context_after: ContextVector`, `timestamp: datetime`.

- [X] T012 [US2] Run `make test` — confirm all 15 ContextVector + EpisodeRecord tests pass
  and all 41 prior tests still pass (56 total). Fix any failures before proceeding.

**Checkpoint**: `EpisodeRecord` JSONL round-trip verified — the offline analysis pipeline
(E6) has a lossless logging contract it can depend on.

---

## Phase 5: User Story 3 — RunManifest Supporting Type (Priority: P2)

**Goal**: `RunManifest` is importable, frozen, and validates any file written by
`aatf.manifest.write_manifest()` (F02). `ContextVector` tests already pass from Phase 4.

**Independent Test**: `make test` passes all 6 new RunManifest tests; parsing a real F02
manifest file via `RunManifest.model_validate(json.loads(...))` succeeds without error.

### Tests for User Story 3 ⚠️ (write first — must FAIL before T015)

- [X] T013 [US3] Append 6 `RunManifest` test cases to `tests/test_contracts.py` (T-RM1 through
  T-RM6 from contracts-api.md):
  - `test_run_manifest_valid` — all fields valid → frozen instance
  - `test_run_manifest_negative_seed` — `seed=-1` → `ValidationError` naming `seed`
  - `test_run_manifest_unknown_suricata` — `suricata_version="unknown"` → valid
  - `test_run_manifest_empty_packages` — `packages={}` → valid
  - `test_run_manifest_roundtrip` — `model_dump(mode="json")` → `model_validate()` → equal instance
  - `test_run_manifest_from_f02_file` — call `write_manifest(cfg, 42)` from `aatf.manifest`
    to produce a real JSON file, then `RunManifest.model_validate(json.loads(path.read_text()))`
    → valid, `manifest.seed == 42`, `"pydantic" in manifest.packages`
  Import: `from aatf.contracts import RunManifest`. Use `tmp_path` fixture for output_dir.

- [X] T014 [US3] Run `make test` — confirm exactly 6 new tests FAIL and all 56 prior tests
  pass. Fix if prior tests break.

### Implementation for User Story 3

- [X] T015 [US3] Implement `RunManifest` in `src/aatf/contracts.py`:
  - `RunManifest(BaseModel)` with `model_config = ConfigDict(frozen=True)` and fields:
    `seed: int = Field(ge=0)`, `python_version: str`, `packages: dict[str, str]`,
    `suricata_version: str`, `ruleset_version: str`, `git_commit: str`,
    `config_snapshot: dict[str, Any]`, `timestamp: str`.

- [X] T016 [US3] Run `make test` — confirm all 6 RunManifest tests pass and all 56 prior
  tests still pass (62 total). Fix any failures before proceeding.

**Checkpoint**: All five contract types implemented and tested — 62/62 tests green.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Static isolation guard (FR-010), lint, README update, quickstart validation.

- [X] T017 Append the static isolation test to `tests/test_contracts.py` (FR-010):
  ```python
  def test_no_forbidden_imports():
      source = pathlib.Path("src/aatf/contracts.py").read_text()
      forbidden = ["aatf.defender", "aatf.attacker", "aatf.environment", "suricata"]
      for term in forbidden:
          assert term not in source, f"Forbidden import found in contracts.py: {term}"
  ```
  Import `pathlib` at the top of the test file. Run `make test` — confirm 63 tests pass
  (29 prior + 34 new). The static test verifies FR-009 (zero coupling to defence/loop).

- [X] T018 [P] Run `make lint` — fix any ruff violations in `src/aatf/contracts.py` and
  `tests/test_contracts.py`. All 63 tests must still pass after any fixes.

- [X] T019 [P] Update `README.md` — add `contracts.py` to the Project layout section with a
  one-line description: `contracts.py  # five frozen Pydantic V2 types: Action, DetectionResult, ContextVector, EpisodeRecord, RunManifest`.

- [X] T020 Validate `quickstart.md` end-to-end: run all 5 scenarios from
  `specs/003-e0-core-contracts/quickstart.md` — confirm SC-001 through SC-005 all pass
  (validated inline via 63/63 test suite).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately. T001 and T002 are sequential
  (T002 creates the file T001 confirms is unnecessary to change).
- **Foundational (Phase 2)**: Nothing to do — skipped.
- **US1 (Phase 3)**: Depends on T002 (skeleton exists). T003 (tests) before T005 (impl).
- **US2 (Phase 4)**: Depends on US1 complete (Action + DetectionResult importable for
  EpisodeRecord). T007+T008 (tests) before T010+T011 (impl). T010 before T011.
- **US3 (Phase 5)**: Depends on Phase 1 only (RunManifest is standalone). Can start after
  T002 — but write tests (T013) after T012 passes to avoid file conflicts.
- **Polish (Phase 6)**: Depends on all three stories complete (T016 green).

### Implementation dependency note

`ContextVector` is implemented in Phase 4 (US2) not Phase 5 (US3) because `EpisodeRecord`
nests it. This is the only deviation from strict story-order; it is a technical necessity
of the single-file module design and does not affect test independence.

### Parallel Opportunities

- T007 and T008 (ContextVector + EpisodeRecord tests) — different test functions in the
  same file; write T007 first, then append T008 (sequential to avoid conflicts).
- T018 and T019 (lint + README) — different files → run in parallel.

---

## Parallel Example: Phase 3 (US1)

```bash
# Sequential within US1 (same file):
Task: "Write Action + DetectionResult tests in tests/test_contracts.py"  # T003
Task: "Run make test — confirm 12 FAIL"                                   # T004
Task: "Implement Action + DetectionResult in src/aatf/contracts.py"       # T005
Task: "Run make test — confirm 12 pass (41 total)"                        # T006
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 Setup → Phase 3 US1.
2. **STOP and VALIDATE**: `Action` and `DetectionResult` importable from `aatf.contracts`;
   binary + continuous + hybrid DetectionResult all valid; frozen. That proves the core
   exchange types are sound — the rest of the loop can be sketched against these.

### Incremental Delivery

US1 (Action + DetectionResult) → US2 (ContextVector + EpisodeRecord JSONL) →
US3 (RunManifest) → Polish.
Each phase adds a distinct contract primitive without breaking the previous.

---

## Notes

- [P] = different files, no blocking dependency — safe to run in parallel.
- All five types live in one file (`contracts.py`). When appending test cases, always
  run `make test` after each append to confirm no file corruption.
- The static isolation test (T017) is a permanent CI guard — it will catch future features
  that accidentally import concrete defence/loop modules into contracts.py.
- `make test` target count after each phase: Phase 3 → 41, Phase 4 → 56, Phase 5 → 62,
  Phase 6 → 63.
- Network not required — all work is local Python/Pydantic.
