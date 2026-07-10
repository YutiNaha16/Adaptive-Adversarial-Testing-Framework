# Tasks: Feedback Collector (F15)

**Feature**: `015-e4-feedback-collector` | **Branch**: `015-e4-feedback-collector`
**Input**: Design documents from `specs/015-e4-feedback-collector/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/feedback-contract.md ✅

**Tests**: TDD — write all 10 tests upfront (red phase), then implement incrementally per user story.
**Baseline**: 182 passed, 4 skipped. Target: ≥192 passed, 4 skipped (+10 unit tests).

**Files to create**:
- `src/aatf/feedback.py` — `FeedbackResult` frozen dataclass + `collect_feedback` function (~30 lines)
- `tests/test_feedback.py` — 10 unit tests (C-001 to C-010) + `_TEST_GRAPH` fixture

---

## Phase 1: Setup

**Purpose**: Record baseline, write all tests red, create stub, verify red.

- [X] T001 Record pytest baseline: run `python -m pytest --tb=no -q` → confirm 182 passed, 4 skipped
- [X] T002 Write `tests/test_feedback.py` with all 10 tests (C-001 to C-010): import `from aatf.feedback import FeedbackResult, collect_feedback`; define `_TEST_GRAPH = AttackGraph(entry_points=frozenset({"recon-syn-scan"}), edges={"recon-syn-scan": frozenset({"exploit-vsftpd-backdoor"}), "exploit-vsftpd-backdoor": frozenset({"lateral-move-smb"})})` as module-level fixture; implement all 10 test functions per contracts/feedback-contract.md
- [X] T003 Create `src/aatf/feedback.py` stub — `from __future__ import annotations`, module docstring, `from dataclasses import dataclass`, `from aatf.attack_graph import ATTACK_GRAPH, AttackGraph`, `from aatf.context_vector import EpisodeState` — no FeedbackResult class, no collect_feedback yet; verify `python -c "import aatf.feedback"` exits 0
- [X] T004 Run `python -m pytest tests/test_feedback.py --tb=short -q` → confirm all 10 tests FAIL with ImportError or NameError (red phase verified)

---

## Phase 2: Foundational

**Purpose**: Add FeedbackResult dataclass — prerequisite for all user story implementations.

- [X] T005 Add `@dataclass(frozen=True)\nclass FeedbackResult:\n    detected: bool\n    stage_progress: bool` to `src/aatf/feedback.py`
- [X] T006 Verify: `python -c "from aatf.feedback import FeedbackResult; r = FeedbackResult(detected=True, stage_progress=False); print(r)"` → must print `FeedbackResult(detected=True, stage_progress=False)`

---

## Phase 3: User Story 1 — Episode State Recording (Priority: P1) 🎯 MVP

**Goal**: All 5 EpisodeState fields mutated correctly on every `collect_feedback` call.

**Independent Test**: `pytest tests/test_feedback.py -k "alert_history or detection_history or completed or step" -v` → C-001 to C-004 PASS

### Implementation for US1

- [X] T007 [US1] Implement `collect_feedback` skeleton in `src/aatf/feedback.py` with the 5 EpisodeState mutations and placeholder `stage_progress=False`:
  ```
  def collect_feedback(episode_state, action_id, alert_fired, *, attack_graph=ATTACK_GRAPH, category=None):
      episode_state.alert_history.append(alert_fired)
      episode_state.detection_history.setdefault(action_id, []).append(alert_fired)
      episode_state.completed_actions.add(action_id)
      episode_state.step += 1
      if alert_fired and category is not None:
          episode_state.fired_categories.add(category)
      return FeedbackResult(detected=alert_fired, stage_progress=False)  # placeholder
  ```
  Add full type annotations: `(episode_state: EpisodeState, action_id: str, alert_fired: bool, *, attack_graph: AttackGraph = ATTACK_GRAPH, category: str | None = None) -> FeedbackResult`
- [X] T008 [US1] Run `python -m pytest tests/test_feedback.py -k "alert_history or detection_history or completed or step" -v` → confirm C-001 to C-004 PASS (4 tests)

**Checkpoint**: US1 — all 5 EpisodeState mutation fields verified correct.

---

## Phase 4: User Story 2 — Stage Progress Detection (Priority: P2)

**Goal**: `stage_progress` correctly True when new actions unlocked, False when terminal or all successors already reachable.

**Independent Test**: `pytest tests/test_feedback.py -k "stage_progress or detected" -v` → C-005 to C-007 PASS

### Implementation for US2

- [X] T009 [US2] Replace `stage_progress=False` placeholder in `collect_feedback` in `src/aatf/feedback.py` with real logic (FR-009 — snapshot BEFORE mutation):
  - Add `before_actions = set(attack_graph.available_actions(episode_state.completed_actions))` as the FIRST line of the function (before any mutation)
  - After all 5 mutations, add `after_actions = set(attack_graph.available_actions(episode_state.completed_actions))`
  - Add `stage_progress = bool(after_actions - before_actions)`
  - Update return to `FeedbackResult(detected=alert_fired, stage_progress=stage_progress)`
- [X] T010 [US2] Run `python -m pytest tests/test_feedback.py -k "stage_progress or detected" -v` → confirm C-005 to C-007 PASS (3 tests)

**Checkpoint**: US2 — stage_progress correctly computed via set-difference before/after snapshot.

---

## Phase 5: User Story 3 — Alert Category Tracking (Priority: P3)

**Goal**: `fired_categories` updated only when `alert_fired=True` AND `category` is not None.

**Independent Test**: `pytest tests/test_feedback.py -k "category" -v` → C-008 to C-010 PASS

### Verification for US3

- [X] T011 [US3] Run `python -m pytest tests/test_feedback.py -k "category" -v` → confirm C-008 to C-010 PASS (3 tests) — `fired_categories` conditional already implemented in T007

**Checkpoint**: US3 — all 3 category branches verified (alert+category, no-alert, no-category).

---

## Phase 6: Polish

**Purpose**: Full verification, lint, format, final count, commit.

- [X] T012 Run `python -m pytest tests/test_feedback.py -v` → confirm all 10 tests PASS
- [X] T013 Run `ruff check src/aatf/feedback.py tests/test_feedback.py` — fix any E501/F401/I001 issues
- [X] T014 Run `ruff format src/aatf/feedback.py tests/test_feedback.py` — apply formatting
- [X] T015 Run full test suite `python -m pytest --tb=short -q` → confirm ≥192 passed, 4 skipped
- [X] T016 Commit: `git add src/aatf/feedback.py tests/test_feedback.py && git commit -m "feat(F15): add collect_feedback + FeedbackResult — in-place EpisodeState mutator with stage progress"`

---

## Dependencies & Execution Order

- **Phase 1 (Setup)**: Start immediately — all 10 tests written red before any implementation
- **Phase 2 (Foundational)**: After T004 red verified — FeedbackResult dataclass blocks all user stories
- **Phase 3 (US1)**: After T006 — implement 5 mutations + placeholder stage_progress
- **Phase 4 (US2)**: After T008 US1 checkpoint — replace placeholder with snapshot logic
- **Phase 5 (US3)**: After T010 US2 checkpoint — verify category logic (already implemented in T007)
- **Phase 6 (Polish)**: After T011 all stories verified

## Notes

- `_TEST_GRAPH` in tests must use REGISTRY action_ids ("recon-syn-scan", "exploit-vsftpd-backdoor", "lateral-move-smb") so EpisodeState.__post_init__ validation does not raise on completed_actions entries
- FR-009 ordering: `before_actions` snapshot MUST be the very first line of `collect_feedback` — before `completed_actions.add(action_id)` — or stage_progress will always be False for the first call
- `stage_progress=False` placeholder in T007 is intentional — allows C-001 to C-004 (US1) and C-008 to C-010 (US3) to be verified before implementing the snapshot logic
- After T016 commit, merge `015-e4-feedback-collector` to main and continue with F16 (episode loop)
