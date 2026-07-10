# Tasks: Context Vector Builder (F13)

**Feature**: `013-e4-context-vector` | **Branch**: `013-e4-context-vector`
**Input**: Design documents from `specs/013-e4-context-vector/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/context-vector-contract.md ✅

**Tests**: TDD — write tests first, verify red, implement, verify green.
**Baseline**: 160 passed, 4 skipped. Target: ≥176 passed, 4 skipped (+16 unit tests).

**Files to create**:
- `src/aatf/context_vector.py` — `EpisodeState` dataclass, `build_context`, `CONTEXT_DIM=50`, 5 private helpers, module constants
- `tests/test_context_vector.py` — 16 unit tests (C-001 to C-016)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Record baseline, create importable stub.

- [X] T001 Record pytest baseline: run `python -m pytest --tb=no -q` → confirm 160 passed, 4 skipped
- [X] T002 Create `src/aatf/context_vector.py` stub — `from __future__ import annotations` + module docstring only; verify `python -c "import aatf.context_vector"` exits 0

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `EpisodeState` dataclass + all module constants + `build_context` skeleton — must exist before any test can import.

**⚠️ CRITICAL**: Complete T003–T009 before any user story phase.

- [X] T003 Add module constants to `src/aatf/context_vector.py`: `CONTEXT_DIM = 50`, `ALERT_WINDOW = 10`, `MAX_STEPS = 100`, `MAX_EPISODE_SECONDS = 3600`, `ET_CATEGORIES = ["ET SCAN", "ET EXPLOIT", "ET BRUTE_FORCE", "ET WEB_SPECIFIC_APPS", "ET DNS", "ET POLICY", "ET TROJAN", "ET INFO"]`; imports: `from __future__ import annotations`, `from dataclasses import dataclass, field`, `import time`, `import numpy as np`, `from aatf.action_library import REGISTRY`
- [X] T004 Add `_SORTED_ACTION_IDS: list[str]` module-level constant to `src/aatf/context_vector.py`: `_SORTED_ACTION_IDS = sorted(d.action_id for d in REGISTRY.list_actions())` — computed once at import; verify `len(_SORTED_ACTION_IDS) == 15`
- [X] T005 Add `EpisodeState` dataclass to `src/aatf/context_vector.py`: `@dataclass` with fields `completed_actions: set[str]`, `detection_history: dict[str, list[bool]]`, `alert_history: list[bool]`, `step: int`, `start_time: float`, `fired_categories: set[str]`; add `__post_init__` that raises `ValueError("step must be non-negative")` if `self.step < 0`, and raises `ValueError(f"unknown action_id: {aid!r}")` for any id in `completed_actions` not in `set(_SORTED_ACTION_IDS)`
- [X] T006 Add 5 private helper functions to `src/aatf/context_vector.py`:
  - `_build_alert_history(alert_history: list[bool]) -> np.ndarray`: take last `ALERT_WINDOW` entries, convert True→1.0/False→0.0, pad left with 0.0 to length 10; return `np.array(..., dtype=np.float32)`
  - `_build_attack_progress(completed: set[str]) -> np.ndarray`: for each id in `_SORTED_ACTION_IDS`, 1.0 if in completed else 0.0; return float32 array shape (15,)
  - `_build_technique_history(history: dict[str, list[bool]]) -> np.ndarray`: for each id in `_SORTED_ACTION_IDS`, rate = `sum(history.get(id, [])) / max(len(history.get(id, [])), 1)`; return float32 array shape (15,)
  - `_build_timing(step: int, start_time: float, current_time: float) -> np.ndarray`: `[min(step / MAX_STEPS, 1.0), min((current_time - start_time) / MAX_EPISODE_SECONDS, 1.0)]`; return float32 array shape (2,)
  - `_build_rule_categories(fired: set[str]) -> np.ndarray`: for each cat in `ET_CATEGORIES`, 1.0 if in fired else 0.0; return float32 array shape (8,)
- [X] T007 Add `build_context(episode_state: EpisodeState, current_time: float | None = None) -> np.ndarray` to `src/aatf/context_vector.py`: resolve `current_time = current_time if current_time is not None else time.time()`; call all 5 helpers; return `np.concatenate([alert, progress, technique, timing, cats]).astype(np.float32)`
- [X] T008 Verify import: `python -c "from aatf.context_vector import EpisodeState, build_context, CONTEXT_DIM; print(CONTEXT_DIM)"` → must print `50`
- [X] T009 Verify construction: `python -c "import time; from aatf.context_vector import EpisodeState, build_context; s = EpisodeState(set(), {}, [], 0, time.time(), set()); v = build_context(s); print(v.shape, v.dtype)"` → must print `(50,) float32`

**Checkpoint**: Foundation ready — `EpisodeState` importable, `build_context` returns correct shape/dtype.

---

## Phase 3: User Story 1 — Entry-Point Observation (Priority: P1) 🎯 MVP

**Goal**: Fresh `EpisodeState` (step=0, empty collections) produces a float32 array of shape (50,) that is deterministic.

**Independent Test**: `pytest tests/test_context_vector.py -k "shape or dtype or dim or deterministic or fresh or zeros"`

### Tests for US1

- [X] T010 [US1] Write `test_output_shape_and_dtype` in `tests/test_context_vector.py` — C-001: `import time, numpy as np; from aatf.context_vector import EpisodeState, build_context, CONTEXT_DIM; state = EpisodeState(set(), {}, [], 0, time.time(), set()); vec = build_context(state); assert vec.shape == (CONTEXT_DIM,); assert vec.dtype == np.float32`
- [X] T011 [US1] Write `test_context_dim_equals_50` in `tests/test_context_vector.py` — C-002: `from aatf.context_vector import CONTEXT_DIM; assert CONTEXT_DIM == 50`
- [X] T012 [US1] Write `test_build_context_is_deterministic` in `tests/test_context_vector.py` — C-003: construct state with fixed `start_time=1000.0`; call `build_context(state, current_time=1000.0)` twice; `assert np.array_equal(v1, v2)`
- [X] T013 [US1] Write `test_fresh_state_all_zeros` in `tests/test_context_vector.py` — C-004: state with step=0, all empty, `current_time=start_time`; `assert np.all(vec == 0.0)`
- [X] T014 [US1] Run `python -m pytest tests/test_context_vector.py -v` — confirm T010–T013 (4 tests) PASS

**Checkpoint**: Entry-point baseline verified (shape, dtype, CONTEXT_DIM, determinism, all-zeros fresh state).

---

## Phase 4: User Story 2 — Attack Progress & Technique History (Priority: P2)

**Goal**: Completed actions set attack_progress flags; per-action detection rates fill technique_history; zero-division never occurs.

**Independent Test**: `pytest tests/test_context_vector.py -k "progress or technique or rate or zero_div"`

### Tests for US2

- [X] T015 [US2] Write `test_alert_history_padding` in `tests/test_context_vector.py` — C-005: `state.alert_history = [True, False, True]`; `vec = build_context(state, current_time=state.start_time)`; `expected = np.array([0,0,0,0,0,0,0,1,0,1], dtype=np.float32)`; `assert np.array_equal(vec[0:10], expected)`
- [X] T016 [US2] Write `test_alert_history_truncation` in `tests/test_context_vector.py` — C-006: `state.alert_history = [True]*2 + [False]*10`; `vec = build_context(state, current_time=state.start_time)`; `assert np.all(vec[0:10] == 0.0)` (last 10 are all False)
- [X] T017 [US2] Write `test_attack_progress_flag` in `tests/test_context_vector.py` — C-007: `state.completed_actions = {"tcp_port_scan"}`; `vec = build_context(state, current_time=state.start_time)`; `progress = vec[10:25]`; `from aatf.context_vector import _SORTED_ACTION_IDS`; `tcp_idx = _SORTED_ACTION_IDS.index("tcp_port_scan")`; `assert progress[tcp_idx] == 1.0`; `assert progress.sum() == 1.0`
- [X] T018 [US2] Write `test_technique_history_rate` in `tests/test_context_vector.py` — C-008: `state.detection_history = {"ssh_brute_force": [True, True, False]}`; `vec = build_context(state, current_time=state.start_time)`; `tech = vec[25:40]`; `ssh_idx = _SORTED_ACTION_IDS.index("ssh_brute_force")`; `assert abs(tech[ssh_idx] - 2/3) < 1e-5`
- [X] T019 [US2] Write `test_technique_history_no_nan_for_zero_executions` in `tests/test_context_vector.py` — C-009: `state.detection_history = {}`; `vec = build_context(state, current_time=state.start_time)`; `assert not np.any(np.isnan(vec[25:40]))`; `assert np.all(vec[25:40] == 0.0)`
- [X] T020 [US2] Run `python -m pytest tests/test_context_vector.py -v` — confirm T015–T019 (5 new tests) PASS

**Checkpoint**: Alert history, attack_progress, technique_history all verified.

---

## Phase 5: User Story 3 — Alert History & Rule Category Signals (Priority: P3)

**Goal**: Timing slots normalise and clip correctly; rule category flags match fired set; unknown categories ignored; no NaN/inf.

**Independent Test**: `pytest tests/test_context_vector.py -k "timing or category or nan or negative or unknown"`

### Tests for US3

- [X] T021 [US3] Write `test_timing_step_normalisation` in `tests/test_context_vector.py` — C-010a: `state.step = 50`; `vec = build_context(state, current_time=state.start_time)`; `assert abs(vec[40] - 0.5) < 1e-5`; then `state.step = 200`; check `vec[40] == pytest.approx(1.0)`
- [X] T022 [US3] Write `test_timing_elapsed_normalisation` in `tests/test_context_vector.py` — C-011: `state.step = 0`; `vec = build_context(state, current_time=state.start_time + 1800)`; `assert abs(vec[41] - 0.5) < 1e-5`
- [X] T023 [US3] Write `test_rule_category_flags` in `tests/test_context_vector.py` — C-012: `state.fired_categories = {"ET SCAN", "ET DNS"}`; `vec = build_context(state, current_time=state.start_time)`; `cats = vec[42:50]`; `assert cats[0] == 1.0`; `assert cats[4] == 1.0`; `assert cats.sum() == 2.0`
- [X] T024 [US3] Write `test_unknown_fired_category_ignored` in `tests/test_context_vector.py` — C-013: `state.fired_categories = {"ET SCAN", "UNKNOWN_XYZ"}`; `vec = build_context(state, current_time=state.start_time)`; `assert vec[42:50].sum() == 1.0`
- [X] T025 [US3] Write `test_negative_step_raises` in `tests/test_context_vector.py` — C-014: `import pytest`; `with pytest.raises(ValueError, match="step must be non-negative"): EpisodeState(set(), {}, [], -1, time.time(), set())`
- [X] T026 [US3] Write `test_unknown_action_id_raises` in `tests/test_context_vector.py` — C-015: `with pytest.raises(ValueError, match="unknown action_id"): EpisodeState({"nonexistent_xyz"}, {}, [], 0, time.time(), set())`
- [X] T027 [US3] Write `test_no_nan_or_inf_in_valid_state` in `tests/test_context_vector.py` — C-016: construct state with 2 completed actions, mixed detection_history, 3-step alert_history, step=5, elapsed=300s, fired_categories={"ET SCAN"}; `vec = build_context(state)`; `assert not np.any(np.isnan(vec))`; `assert not np.any(np.isinf(vec))`
- [X] T028 [US3] Run `python -m pytest tests/test_context_vector.py -v` — confirm T021–T027 (7 new tests) PASS

**Checkpoint**: All 16 tests green. All 3 user stories verified.

---

## Phase 6: Polish

**Purpose**: Lint, format, final count, commit.

- [X] T029 Run `ruff check src/aatf/context_vector.py tests/test_context_vector.py` — fix any issues (UP006/UP035: use `collections.abc`; F401: remove unused; E501: wrap long lines)
- [X] T030 Run `ruff format src/aatf/context_vector.py tests/test_context_vector.py` — apply formatting
- [X] T031 Run full test suite `python -m pytest --tb=short -q` — confirm ≥176 passed, 4 skipped
- [X] T032 Commit: `git add src/aatf/context_vector.py tests/test_context_vector.py && git commit -m "feat(F13): add EpisodeState, build_context, CONTEXT_DIM=50 — context vector for RL attacker"`

---

## Dependencies & Execution Order

- **Phase 1 (Setup)**: Start immediately
- **Phase 2 (Foundational)**: After Phase 1 — BLOCKS all user stories
- **Phase 3–5 (US1–US3)**: After Phase 2 — sequential (each adds to same test file)
- **Phase 6 (Polish)**: After all user story phases

---

## Notes

- `_SORTED_ACTION_IDS` is computed at import time from REGISTRY — tests that reference slot indices must use it directly rather than hardcoding indices
- `current_time` is always injected as a fixed float in tests (e.g. `current_time=state.start_time`) to keep tests deterministic
- Alert history ordering: slot 0 = oldest, slot 9 = most recent; zero-padded at the LEFT
- After T032 commit, merge `013-e4-context-vector` to main and continue with F14 (reward function)
