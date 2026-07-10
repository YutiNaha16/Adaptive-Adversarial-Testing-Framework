# Tasks: Reward Function (F14)

**Feature**: `014-e4-reward-function` | **Branch**: `014-e4-reward-function`
**Input**: Design documents from `specs/014-e4-reward-function/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/reward-contract.md ✅

**Tests**: TDD — write tests first, verify red, implement, verify green.
**Baseline**: 176 passed, 4 skipped. Target: ≥182 passed, 4 skipped (+6 unit tests).

**Files to create**:
- `src/aatf/reward.py` — `REWARD_DETECTED`, `REWARD_PROGRESS`, `REWARD_STALL` constants + `compute_reward` function
- `tests/test_reward.py` — 6 unit tests (C-001 to C-006)

---

## Phase 1: Setup

**Purpose**: Record baseline, write tests red, create stub.

- [X] T001 Record pytest baseline: run `python -m pytest --tb=no -q` → confirm 176 passed, 4 skipped
- [X] T002 [P] Write `tests/test_reward.py` with all 6 tests (C-001 to C-006) — import `from aatf.reward import compute_reward, REWARD_DETECTED, REWARD_PROGRESS, REWARD_STALL`; test bodies as specified in contracts/reward-contract.md (see Phase 3 for exact test bodies)
- [X] T003 Create `src/aatf/reward.py` stub — `from __future__ import annotations` + docstring only; verify `python -c "import aatf.reward"` exits 0
- [X] T004 Run `python -m pytest tests/test_reward.py --tb=short` → confirm all 6 tests FAIL with ImportError or AttributeError (red phase verified)

---

## Phase 2: Foundational

**Purpose**: Add constants and implement `compute_reward` — the complete implementation is ~10 lines.

- [X] T005 Add `REWARD_DETECTED = -1.0`, `REWARD_PROGRESS = 1.0`, `REWARD_STALL = -0.1` and `compute_reward(detected: bool, stage_progress: bool) -> float` to `src/aatf/reward.py`: `if detected: return REWARD_DETECTED`; `if stage_progress: return REWARD_PROGRESS`; `return REWARD_STALL`
- [X] T006 Verify import: `python -c "from aatf.reward import compute_reward, REWARD_DETECTED, REWARD_PROGRESS, REWARD_STALL; print(compute_reward(True, False))"` → must print `-1.0`

---

## Phase 3: User Story 1 — Detection Penalty (Priority: P1)

**Goal**: `compute_reward(detected=True, ...)` always returns −1.0 regardless of `stage_progress`.

**Independent Test**: `pytest tests/test_reward.py -k "detected"`

### Tests for US1

- [X] T007 [US1] Write `test_detected_no_progress` in `tests/test_reward.py` — C-001: `assert compute_reward(detected=True, stage_progress=False) == REWARD_DETECTED`; `assert compute_reward(detected=True, stage_progress=False) == -1.0`
- [X] T008 [US1] Write `test_detected_with_progress` in `tests/test_reward.py` — C-002: `assert compute_reward(detected=True, stage_progress=True) == REWARD_DETECTED`; `assert compute_reward(detected=True, stage_progress=True) == -1.0` (detection wins over progress)
- [X] T009 [US1] Run `python -m pytest tests/test_reward.py -k "detected" -v` → confirm T007–T008 PASS

---

## Phase 4: User Story 2 — Progress Reward (Priority: P2)

**Goal**: `compute_reward(detected=False, stage_progress=True)` returns +1.0.

**Independent Test**: `pytest tests/test_reward.py -k "progress"`

### Tests for US2

- [X] T010 [US2] Write `test_undetected_with_progress` in `tests/test_reward.py` — C-003: `assert compute_reward(detected=False, stage_progress=True) == REWARD_PROGRESS`; `assert compute_reward(detected=False, stage_progress=True) == 1.0`
- [X] T011 [US2] Run `python -m pytest tests/test_reward.py -k "progress" -v` → confirm T010 PASS

---

## Phase 5: User Story 3 — No-Progress Penalty (Priority: P3)

**Goal**: `compute_reward(detected=False, stage_progress=False)` returns −0.1; return type is float; named constants correct.

**Independent Test**: `pytest tests/test_reward.py -k "stall or constant or type"`

### Tests for US3

- [X] T012 [US3] Write `test_undetected_no_progress` in `tests/test_reward.py` — C-004: `assert compute_reward(detected=False, stage_progress=False) == REWARD_STALL`; `assert abs(compute_reward(detected=False, stage_progress=False) - (-0.1)) < 1e-9`
- [X] T013 [US3] Write `test_return_type_is_float` in `tests/test_reward.py` — C-005: `result = compute_reward(detected=False, stage_progress=True)`; `assert isinstance(result, float)`
- [X] T014 [US3] Write `test_named_constants` in `tests/test_reward.py` — C-006: `assert REWARD_DETECTED == -1.0`; `assert REWARD_PROGRESS == 1.0`; `assert abs(REWARD_STALL - (-0.1)) < 1e-9`
- [X] T015 [US3] Run `python -m pytest tests/test_reward.py -v` → confirm all 6 tests PASS

---

## Phase 6: Polish

**Purpose**: Lint, format, final count, commit.

- [X] T016 Run `ruff check src/aatf/reward.py tests/test_reward.py` — fix any issues
- [X] T017 Run `ruff format src/aatf/reward.py tests/test_reward.py` — apply formatting
- [X] T018 Run full test suite `python -m pytest --tb=short -q` → confirm ≥182 passed, 4 skipped
- [X] T019 Commit: `git add src/aatf/reward.py tests/test_reward.py && git commit -m "feat(F14): add compute_reward — 3-branch Phase 1 reward function with named constants"`

---

## Dependencies & Execution Order

- **Phase 1 (Setup)**: Start immediately — tests written red before implementation
- **Phase 2 (Foundational)**: After T004 red verified — implement constants + function
- **Phase 3–5 (US1–US3)**: Tests already written in T002; run pytest per-story to verify green
- **Phase 6 (Polish)**: After all user story phases

## Notes

- All 6 test bodies can be written in T002 upfront (before implementation) since contracts are fully specified
- `REWARD_STALL = -0.1` — use `abs(val - (-0.1)) < 1e-9` in tests, not `==`, to avoid float representation edge cases
- After T019 commit, merge `014-e4-reward-function` to main and continue with F15 (feedback collector)
