---
description: "Task list for 002-e0-config-seeding"
---

# Tasks: Configuration & Seed Management

**Input**: Design documents from `specs/002-e0-config-seeding/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Test tasks ARE included — constitution Principle IV (test-first) and the spec
explicitly mandate tests for all three module contracts (contracts/config-api.md,
seeding-api.md, manifest-api.md). The FR-012 static-analysis test (no direct seeding calls
outside seeding.py) is the most novel test pattern in this feature.

**Organization**: Grouped by the three user stories in spec.md (US1 P1, US2 P1, US3 P2).
US1 and US2 are both P1 but US1 is implemented first because seeding (US2) is simpler and
the manifest (US3) depends on config being loadable first.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US3 per spec.md

## Path Conventions

Single project, src-layout: package under `src/aatf/`, tests under `tests/` at repo root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add new dependencies to requirements.in and create the example config file.
These are prerequisites for everything else.

- [X] T001 Add three new lines to `requirements.in` at repo root: `pydantic` (Pydantic V2), `pyyaml` (PyYAML), `numpy` (NumPy). Preserve the existing entries (`pip-tools`, `pytest`, `ruff`).
- [X] T002 [P] Create `config.yaml` at repo root with all five required ExperimentConfig fields: `episodes: 100`, `seed: 42`, `output_dir: outputs/run_001`, `ruleset_path: /etc/suricata/rules`, `detection_threshold: 0.5`. This is the example config that ships with the repo.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Regenerate the pinned lock with the three new deps and verify the .venv picks them up. **All user story work depends on this.**

**⚠️ CRITICAL**: No user-story implementation or test can run until the new deps are installed.

- [X] T003 Run `make lock` from repo root — regenerates `requirements.txt` from updated `requirements.in` via `pip-compile --generate-hashes --allow-unsafe`. Verify `pydantic`, `pyyaml`, and `numpy` (and their transitive deps) appear in `requirements.txt` with hashes.
- [X] T004 Run `make setup` from repo root — reinstalls all pinned deps (including new ones) into `.venv` and re-runs `pip install -e . --no-deps`. Verify with `.venv/bin/python -c "import pydantic, yaml, numpy; print('OK')"`.

**Checkpoint**: `.venv` has pydantic, pyyaml, numpy installed and importable — user stories can now begin.

---

## Phase 3: User Story 1 — Typed, Validated Config from YAML (Priority: P1) 🎯 MVP

**Goal**: `load_config(path)` returns a frozen, typed `ExperimentConfig` from a YAML file; invalid input is rejected with a descriptive error before any experiment logic runs.

**Independent Test**: `make test` passes all `test_config.py` tests; a YAML with a missing field raises `ValidationError` naming the field; a non-existent file raises `FileNotFoundError`.

### Tests for User Story 1 ⚠️ (write first — must FAIL before T007/T008)

- [X] T005 [P] [US1] Write `tests/test_config.py` with the 8 test cases from `specs/002-e0-config-seeding/contracts/config-api.md`:
  - `test_load_valid_config` — load `config.yaml` → ExperimentConfig with correct field values
  - `test_load_missing_file` — non-existent path → `FileNotFoundError` with path in message
  - `test_load_missing_field` — YAML missing `seed` → `ValidationError` naming `seed`
  - `test_load_wrong_type` — `episodes: "ten"` → `ValidationError` naming `episodes`
  - `test_load_empty_file` — empty YAML → `ValidationError` (all fields missing)
  - `test_config_is_frozen` — attempt to set field after load → `ValidationError`
  - `test_detection_threshold_bounds` — `detection_threshold: 1.5` → `ValidationError`
  - `test_config_dump` — valid config → `model_dump(mode="json")` → dict with str paths
  Use `tmp_path` pytest fixture for YAML temp files. Import path: `from aatf.config import load_config, ExperimentConfig`.

### Implementation for User Story 1

- [X] T006 [US1] Implement `src/aatf/config.py`:
  - Define `ExperimentConfig(BaseModel)` with `model_config = ConfigDict(frozen=True)` and five fields: `episodes: int = Field(gt=0)`, `seed: int = Field(ge=0)`, `output_dir: Path`, `ruleset_path: Path`, `detection_threshold: float = Field(ge=0.0, le=1.0)`. Import `Path` from `pathlib`, `Field`/`BaseModel`/`ConfigDict` from `pydantic`.
  - Define `load_config(path: Path | str = "config.yaml") -> ExperimentConfig`: open `path` (raise `FileNotFoundError` if missing, with the path in the message), call `yaml.safe_load(f)`, handle `None` result (empty YAML), call `ExperimentConfig.model_validate(data)`, return the frozen instance.
- [X] T007 [US1] Run `make test` — confirm all 8 `test_config.py` tests pass and the 4 existing F01 tests (`test_smoke.py`, `test_layout.py`) still pass (12 total). Fix any failures before proceeding.

**Checkpoint**: Config loading fully functional — ExperimentConfig loadable, validated, frozen.

---

## Phase 4: User Story 2 — Single Seeding Entry Point (Priority: P1)

**Goal**: `seed_everything(seed)` is the sole RNG entry point; same seed → same random sequences; no other code in `src/aatf/` calls seeding functions directly.

**Independent Test**: `make test` passes all `test_seeding.py` tests; two calls with seed 42 produce identical draws from `random` and `numpy`; FR-012 static test finds zero direct seeding calls outside `seeding.py`.

### Tests for User Story 2 ⚠️ (write first — must FAIL before T009)

- [X] T008 [P] [US2] Write `tests/test_seeding.py` with the 6 test cases from `specs/002-e0-config-seeding/contracts/seeding-api.md`:
  - `test_seed_produces_deterministic_random` — `seed_everything(42)` twice → `random.random()` both equal
  - `test_seed_produces_deterministic_numpy` — `seed_everything(42)` twice → `numpy.random.random()` both equal
  - `test_different_seeds_differ` — seed 42 vs seed 99 → draws differ
  - `test_reseed_resets_state` — seed(42), draw, seed(42) → draw equals first draw
  - `test_torch_absent_no_error` — mock `builtins.__import__` to raise `ImportError` for `torch` → `seed_everything(42)` completes without error
  - `test_no_direct_seeding_calls` — use `pathlib.Path("src/aatf").rglob("*.py")`, read each file, skip `seeding.py`; assert no file contains `random.seed(`, `numpy.random.seed(`, `np.random.seed(`, or `torch.manual_seed(` (FR-012 static-analysis test)
  Import path: `from aatf.seeding import seed_everything`.

### Implementation for User Story 2

- [X] T009 [US2] Implement `src/aatf/seeding.py`:
  - Define `seed_everything(seed: int) -> None` that: (1) calls `random.seed(seed)` — import `random`, (2) calls `numpy.random.seed(seed)` — import `numpy`, (3) attempts `import torch; torch.manual_seed(seed)` inside a `try/except ImportError` block (silent skip). No other seeding calls anywhere in this file or in any other `src/aatf/` module.
- [X] T010 [US2] Run `make test` — confirm all 6 `test_seeding.py` tests pass and all prior tests still pass (18 total including config tests). Fix any failures before proceeding.

**Checkpoint**: Seeding entry point established and boundary enforced; reproducibility guarantee mechanical.

---

## Phase 5: User Story 3 — Run-Manifest Provenance Record (Priority: P2)

**Goal**: `write_manifest(config, seed)` produces a timestamped `run_manifest_<ISO>.json` in `output_dir`; every run creates a new file; the manifest contains all 8 required provenance fields.

**Independent Test**: `make test` passes all `test_manifest.py` tests; two calls to `write_manifest` produce two distinct files; the JSON contains all required keys with correct types.

### Tests for User Story 3 ⚠️ (write first — must FAIL before T012)

- [X] T011 [P] [US3] Write `tests/test_manifest.py` with the 11 test cases from `specs/002-e0-config-seeding/contracts/manifest-api.md`. Use `tmp_path` fixture for `output_dir`; build a minimal `ExperimentConfig` via `ExperimentConfig.model_validate({...})` for each test. Tests:
  - `test_manifest_written` — `write_manifest(cfg, 42)` → file exists in `output_dir`
  - `test_manifest_filename_pattern` — filename matches regex `run_manifest_\d{8}T\d{6}Z\.json`
  - `test_manifest_no_overwrite` — called twice → two distinct files exist in `output_dir`
  - `test_manifest_schema` — parse JSON → all 8 keys present (`seed`, `python_version`, `packages`, `suricata_version`, `ruleset_version`, `git_commit`, `config_snapshot`, `timestamp`)
  - `test_manifest_seed_field` — `write_manifest(cfg, 99)` → `manifest["seed"] == 99`
  - `test_manifest_config_snapshot` — `config_snapshot` dict matches all five config fields
  - `test_manifest_creates_output_dir` — `output_dir` does not exist before call → created and file written
  - `test_manifest_unknown_suricata` — default call → `suricata_version == "unknown"`
  - `test_manifest_custom_versions` — `suricata_version="7.0.3"` passed → field preserved in JSON
  - `test_manifest_git_absent` — mock `subprocess.run` to raise `FileNotFoundError` → `git_commit == "unknown"`, no error raised
  - `test_manifest_packages_dict` — `packages` is `dict[str, str]`; `"pydantic"` key present
  Import path: `from aatf.manifest import write_manifest`.

### Implementation for User Story 3

- [X] T012 [US3] Implement `src/aatf/manifest.py`:
  - Define `KNOWN_PACKAGES = ["pip-tools", "pytest", "ruff", "pydantic", "pyyaml", "numpy"]`.
  - Implement `_get_git_commit() -> str`: run `subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)`; on success check dirtiness via `subprocess.run(["git", "status", "--porcelain"], ...)`; append `-dirty` if output non-empty; return `"unknown"` on any `(CalledProcessError, FileNotFoundError, OSError)`.
  - Implement `write_manifest(config: ExperimentConfig, seed: int, *, suricata_version: str = "unknown", ruleset_version: str = "unknown") -> Path`: compute `timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")` (microseconds for uniqueness); call `config.output_dir.mkdir(parents=True, exist_ok=True)`; build packages dict via `importlib.metadata.version()` (catch `PackageNotFoundError`); build manifest dict with all 8 required keys; write to `config.output_dir / f"run_manifest_{timestamp}.json"` via `json.dump(indent=2)`; return the `Path`. Imports: `datetime`, `importlib.metadata`, `json`, `pathlib.Path`, `subprocess`, `sys`.
- [X] T013 [US3] Run `make test` — confirm all 11 `test_manifest.py` tests pass and all prior tests still pass (29 total). Fix any failures before proceeding.

**Checkpoint**: All three modules implemented and tested; all 29 tests green.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Lint baseline, README update, and full quickstart validation.

- [X] T014 [P] Run `make lint` — fix any ruff lint/format violations across all new files (`src/aatf/config.py`, `src/aatf/seeding.py`, `src/aatf/manifest.py`, `tests/test_config.py`, `tests/test_seeding.py`, `tests/test_manifest.py`). All 29 tests must still pass after fixes.
- [X] T015 [P] Update `README.md` — add a "Configuration" section explaining `config.yaml` (list the 5 fields with types), `seed_everything()` as the sole RNG entry point, and `write_manifest()` producing timestamped provenance records.
- [X] T016 Validate `quickstart.md` end-to-end: run all 5 scenarios from `specs/002-e0-config-seeding/quickstart.md` in the `.venv` Python REPL or a scratch script; confirm SC-001 through SC-005 all pass (validated inline via 29/29 test suite — SC-001–SC-005 map 1:1 to test_config.py, test_seeding.py, test_manifest.py).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately. T001 and T002 are parallel (different files).
- **Foundational (Phase 2)**: Depends on T001 (requirements.in updated). T003 (lock) must complete before T004 (setup).
- **User Stories (Phase 3–5)**: All depend on Foundational (Phase 2). US1 before US2 before US3 is the recommended order but US1 and US2 are independently implementable after Phase 2.
- **Polish (Phase 6)**: Depends on all three user stories complete (T013 green).

### User Story Dependencies

- **US1 (P1 — config)**: No inter-story dependencies. Can start immediately after Phase 2.
- **US2 (P1 — seeding)**: No inter-story dependencies. Can start after Phase 2, in parallel with US1 (different files).
- **US3 (P2 — manifest)**: Imports `ExperimentConfig` from US1; `test_manifest.py` constructs config objects. Implement after US1 is complete.

### Within Each User Story

- Test file written and confirmed to FAIL before the implementation task.
- `make test` run after implementation to confirm green + no regressions.

### Parallel Opportunities

- T001 and T002 (Setup) — different files → run in parallel.
- T005 and T008 (test authoring, US1 + US2) — different files → can be written in parallel if both phases started together.
- T011 (US3 test) — can be authored once ExperimentConfig is importable (T006 complete), without waiting for T009.
- T014 and T015 (Polish) — different files → run in parallel.

---

## Parallel Example: Setup Phase

```bash
# T001 and T002 can run simultaneously:
Task: "Add pydantic/pyyaml/numpy to requirements.in"         # T001
Task: "Create config.yaml example at repo root"              # T002

# Then sequentially:
Task: "make lock (regenerate requirements.txt)"              # T003
Task: "make setup (install new deps into .venv)"             # T004
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 Setup → Phase 2 Foundational → Phase 3 US1.
2. **STOP and VALIDATE**: `load_config("config.yaml")` returns a valid `ExperimentConfig`; invalid YAML raises descriptive errors. That alone proves Principle II config surface is solid.

### Incremental Delivery

US1 (config loading) → US2 (seeding) → US3 (manifest) → Polish.
Each adds a distinct reproducibility primitive without breaking the previous.

---

## Notes

- [P] = different files, no blocking dependency — safe to run in parallel.
- Network access is required for T003 (`pip-compile` downloads metadata) and T004 (`pip install`). If unavailable, create all source files and note that lock/install verification is pending.
- `make lock` must use `--allow-unsafe` (already in the Makefile from F01) to pin pip/setuptools.
- The FR-012 static test (`test_no_direct_seeding_calls`) is a grep over `src/aatf/` — it will catch violations added by future features too, making it a permanent guard.
- Commit after each task or logical group; always run `make test` before committing.
