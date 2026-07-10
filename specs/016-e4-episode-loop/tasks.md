# Tasks: Episode Loop (F16)

**Input**: Design documents from `/specs/016-e4-episode-loop/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/episode-contract.md ✅

**Tests**: TDD — all 12 tests written upfront (red), then implementation drives them green story-by-story.

**Baseline**: 192 passed, 4 skipped. **Target**: ≥204 passed, 4 skipped (+12 tests).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- All paths relative to repo root

---

## Phase 1: Setup

**Purpose**: Record baseline and create the two new files as stubs.

- [ ] T001 Record baseline in terminal: `source .venv/bin/activate && cd src && pytest --tb=no -q 2>&1 | tail -3` — confirm 192 passed, 4 skipped
- [ ] T002 Create stub `src/aatf/episode.py` with module docstring and `from __future__ import annotations` only (no classes, no functions yet)
- [ ] T003 Create empty `tests/test_episode.py` with `from __future__ import annotations` only

---

## Phase 2: Foundational — Write All Tests Upfront (Red)

**Purpose**: Write all 12 tests before any implementation. Verify red: tests collected but all fail (ImportError or AttributeError acceptable).

**Independent test criteria**: `cd src && pytest ../tests/test_episode.py --tb=short -q` collects 12 tests and all fail.

- [ ] T004 Add shared fixtures/helpers to `tests/test_episode.py`:
  ```python
  from __future__ import annotations
  from aatf.action_library import REGISTRY
  from aatf.contracts import Action, DetectionResult
  from aatf.context_vector import EpisodeState
  from aatf.defence import Defence
  from aatf.episode import EpisodeResult, StepRecord, run_episode

  _ALL_IDS: frozenset[str] = frozenset(a.action_id for a in REGISTRY.list_actions())
  _SELECTOR = lambda available, state: available[0]
  _EXECUTE: lambda action_id: None  # type: ignore[assignment]

  class StubDefence(Defence):
      def __init__(self, alert: bool = False) -> None:
          self._alert = alert
      def observe(self, action: Action) -> DetectionResult:
          return DetectionResult(alerted=self._alert, rule_ids=[], anomaly_score=0.0, coverage="unknown")
  ```

- [ ] T005 Write C-001 in `tests/test_episode.py` — StepRecord.action_id is one of the 4 entry point ids after 1 step on fresh state with max_steps=1:
  ```python
  def test_c001_step_record_action_id() -> None:
      state = EpisodeState()
      result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=1)
      assert len(result.steps) == 1
      entry_points = {"dns_subdomain_enum", "icmp_ping_sweep", "tcp_port_scan", "udp_sweep"}
      assert result.steps[0].action_id in entry_points
  ```

- [ ] T006 Write C-002 in `tests/test_episode.py` — detected=False + reward=-0.1 when no alert and terminal action (ssh_version_probe, all others pre-completed):
  ```python
  def test_c002_no_alert_terminal_reward() -> None:
      state = EpisodeState(completed_actions=set(_ALL_IDS - {"ssh_version_probe"}))
      result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=1)
      step = result.steps[0]
      assert step.action_id == "ssh_version_probe"
      assert step.detected is False
      assert step.stage_progress is False
      assert step.reward == -0.1
  ```

- [ ] T007 Write C-003 in `tests/test_episode.py` — detected=True + reward=-1.0 when alert fires:
  ```python
  def test_c003_alert_detected_reward() -> None:
      state = EpisodeState(completed_actions=set(_ALL_IDS - {"ssh_version_probe"}))
      result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=True), max_steps=1)
      step = result.steps[0]
      assert step.detected is True
      assert step.reward == -1.0
  ```

- [ ] T008 Write C-004 in `tests/test_episode.py` — stage_progress=True + reward=+1.0 for entry-point action with successors (tcp_port_scan):
  ```python
  def test_c004_stage_progress_true_entry_point() -> None:
      state = EpisodeState()
      selector = lambda available, s: "tcp_port_scan"
      result = run_episode(state, selector, _EXECUTE, StubDefence(alert=False), max_steps=1)
      assert result.steps[0].stage_progress is True
      assert result.steps[0].reward == 1.0
  ```

- [ ] T009 Write C-005 in `tests/test_episode.py` — EpisodeState.step, completed_actions, alert_history mutated in-place:
  ```python
  def test_c005_episode_state_mutated() -> None:
      state = EpisodeState()
      assert state.step == 0
      run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=1)
      assert state.step == 1
      assert len(state.alert_history) == 1
      assert len(state.completed_actions) == 1
  ```

- [ ] T010 Write C-006 in `tests/test_episode.py` — completed=True + exactly 1 step when final action is terminal (ssh_version_probe):
  ```python
  def test_c006_completed_true_terminal_exhausted() -> None:
      state = EpisodeState(completed_actions=set(_ALL_IDS - {"ssh_version_probe"}))
      result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False))
      assert result.completed is True
      assert len(result.steps) == 1
  ```

- [ ] T011 Write C-007 in `tests/test_episode.py` — completed=True + 0 steps when all actions pre-completed:
  ```python
  def test_c007_completed_true_zero_steps_preloaded() -> None:
      state = EpisodeState(completed_actions=set(_ALL_IDS))
      result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False))
      assert result.completed is True
      assert result.steps == []
      assert result.total_reward == 0.0
  ```

- [ ] T012 Write C-008 in `tests/test_episode.py` — completed=False + exactly max_steps=3 steps when step limit reached:
  ```python
  def test_c008_completed_false_step_limit() -> None:
      state = EpisodeState()
      result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=3)
      assert result.completed is False
      assert len(result.steps) == 3
  ```

- [ ] T013 Write C-009 in `tests/test_episode.py` — FR-003: no-actions wins over step-limit when both conditions simultaneously true:
  ```python
  def test_c009_fr003_no_actions_wins_over_step_limit() -> None:
      # Both true: available=[] AND step(5) >= max_steps(5)
      state = EpisodeState(completed_actions=set(_ALL_IDS), step=5)
      result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=5)
      assert result.completed is True   # no-actions wins → True, not False
      assert result.steps == []
  ```

- [ ] T014 Write C-010 in `tests/test_episode.py` — max_steps=0 → 0 steps, completed=False:
  ```python
  def test_c010_max_steps_zero() -> None:
      state = EpisodeState()
      result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=0)
      assert result.completed is False
      assert result.steps == []
      assert result.total_reward == 0.0
  ```

- [ ] T015 Write C-011 in `tests/test_episode.py` — total_reward is arithmetic sum (abs tolerance < 1e-9):
  ```python
  def test_c011_total_reward_arithmetic_sum() -> None:
      # 3 entry-point actions in order; first alerts (-1.0), next two don't + progress (+1.0 each)
      state = EpisodeState()
      steps_order = ["tcp_port_scan", "dns_subdomain_enum", "icmp_ping_sweep"]
      idx = 0
      def seq_selector(available: list[str], s: EpisodeState) -> str:
          nonlocal idx
          choice = steps_order[idx]; idx += 1; return choice
      call_count = 0
      class FirstAlertDefence(Defence):
          def observe(self, action: Action) -> DetectionResult:
              nonlocal call_count
              call_count += 1
              alerted = call_count == 1
              return DetectionResult(alerted=alerted, rule_ids=[], anomaly_score=0.0, coverage="unknown")
      result = run_episode(state, seq_selector, _EXECUTE, FirstAlertDefence(), max_steps=3)
      assert len(result.steps) == 3
      # step1: detected=True → -1.0; step2: no alert + progress → +1.0; step3: no alert + progress → +1.0
      assert abs(result.total_reward - (-1.0 + 1.0 + 1.0)) < 1e-9
  ```

- [ ] T016 Write C-012 in `tests/test_episode.py` — state.step == len(result.steps) for any episode:
  ```python
  def test_c012_state_step_equals_steps_length() -> None:
      state = EpisodeState()
      result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=4)
      assert state.step == len(result.steps)
  ```

- [ ] T017 Verify red phase: `cd src && pytest ../tests/test_episode.py --tb=short -q 2>&1 | tail -6` — expect 12 tests collected, all failing (ImportError from `from aatf.episode import EpisodeResult, StepRecord, run_episode`)

---

## Phase 3: US1 — Single Step Execution

**Story goal**: The loop correctly orchestrates the full action → detect → feedback → reward sequence in one step. StepRecord captures all fields correctly.

**Independent test criteria**: `cd src && pytest ../tests/test_episode.py::test_c001_step_record_action_id ../tests/test_episode.py::test_c002_no_alert_terminal_reward ../tests/test_episode.py::test_c003_alert_detected_reward ../tests/test_episode.py::test_c004_stage_progress_true_entry_point ../tests/test_episode.py::test_c005_episode_state_mutated -v` → 5 PASS.

- [ ] T018 [US1] Add `StepRecord` and `EpisodeResult` frozen dataclasses to `src/aatf/episode.py`:
  ```python
  @dataclass(frozen=True)
  class StepRecord:
      action_id: str
      detected: bool
      stage_progress: bool
      reward: float

  @dataclass(frozen=True)
  class EpisodeResult:
      episode_state: EpisodeState
      steps: list[StepRecord]
      total_reward: float
      completed: bool
  ```

- [ ] T019 [US1] Add full `run_episode` function to `src/aatf/episode.py` with complete per-step logic:

  Imports block:
  ```python
  from __future__ import annotations
  from dataclasses import dataclass
  from datetime import datetime, timezone
  from typing import Callable
  from aatf.action_library import REGISTRY
  from aatf.attack_graph import ATTACK_GRAPH, AttackGraph
  from aatf.context_vector import EpisodeState, MAX_STEPS
  from aatf.contracts import Action
  from aatf.defence import Defence
  from aatf.feedback import collect_feedback
  from aatf.reward import compute_reward
  ```

  Function:
  ```python
  def run_episode(
      episode_state: EpisodeState,
      action_selector: Callable[[list[str], EpisodeState], str],
      execute_fn: Callable[[str], None],
      defence: Defence,
      *,
      attack_graph: AttackGraph = ATTACK_GRAPH,
      max_steps: int = MAX_STEPS,
  ) -> EpisodeResult:
      steps: list[StepRecord] = []
      total_reward = 0.0
      while True:
          reachable = attack_graph.available_actions(episode_state.completed_actions)
          available = [a for a in reachable if a not in episode_state.completed_actions]
          if not available:
              return EpisodeResult(episode_state=episode_state, steps=steps,
                                   total_reward=total_reward, completed=True)
          if episode_state.step >= max_steps:
              return EpisodeResult(episode_state=episode_state, steps=steps,
                                   total_reward=total_reward, completed=False)
          action_id = action_selector(available, episode_state)
          execute_fn(action_id)
          action_def = REGISTRY.get_action(action_id)
          action = Action(action_id=action_id, category=action_def.category,
                          parameters=action_def.default_parameters,
                          timestamp=datetime.now(timezone.utc))
          detection = defence.observe(action)
          alert_fired = detection.alerted
          category = action_def.suricata_category if alert_fired else None
          result = collect_feedback(episode_state, action_id, alert_fired,
                                    attack_graph=attack_graph, category=category)
          reward = compute_reward(result.detected, result.stage_progress)
          steps.append(StepRecord(action_id=action_id, detected=result.detected,
                                  stage_progress=result.stage_progress, reward=reward))
          total_reward += reward
  ```

- [ ] T020 [US1] Verify C-001 to C-005 green: `cd src && pytest ../tests/test_episode.py::test_c001_step_record_action_id ../tests/test_episode.py::test_c002_no_alert_terminal_reward ../tests/test_episode.py::test_c003_alert_detected_reward ../tests/test_episode.py::test_c004_stage_progress_true_entry_point ../tests/test_episode.py::test_c005_episode_state_mutated -v` → 5 PASS

---

## Phase 4: US2 — Episode Termination: Actions Exhausted

**Story goal**: Episode terminates with `completed=True` when no uncompleted reachable actions remain — immediately (0 steps) or after the last terminal action (1+ steps).

**Independent test criteria**: `cd src && pytest ../tests/test_episode.py::test_c006_completed_true_terminal_exhausted ../tests/test_episode.py::test_c007_completed_true_zero_steps_preloaded -v` → 2 PASS.

- [ ] T021 [US2] Verify C-006 and C-007 green (no additional code needed — termination logic already in run_episode from T019): `cd src && pytest ../tests/test_episode.py::test_c006_completed_true_terminal_exhausted ../tests/test_episode.py::test_c007_completed_true_zero_steps_preloaded -v` → 2 PASS

---

## Phase 5: US3 — Episode Termination: Step Limit Reached

**Story goal**: Episode terminates with `completed=False` when `episode_state.step >= max_steps`. FR-003: no-actions check takes priority when both conditions are simultaneously true.

**Independent test criteria**: `cd src && pytest ../tests/test_episode.py::test_c008_completed_false_step_limit ../tests/test_episode.py::test_c009_fr003_no_actions_wins_over_step_limit ../tests/test_episode.py::test_c010_max_steps_zero -v` → 3 PASS.

- [ ] T022 [US3] Verify C-008, C-009, C-010 green (no additional code needed — step-limit check and FR-003 ordering already in run_episode from T019): `cd src && pytest ../tests/test_episode.py::test_c008_completed_false_step_limit ../tests/test_episode.py::test_c009_fr003_no_actions_wins_over_step_limit ../tests/test_episode.py::test_c010_max_steps_zero -v` → 3 PASS

---

## Phase 6: US4 — Cumulative Episode Result

**Story goal**: `EpisodeResult.total_reward` is the arithmetic sum of all step rewards to floating-point precision. `episode_state.step == len(result.steps)` after any episode.

**Independent test criteria**: `cd src && pytest ../tests/test_episode.py::test_c011_total_reward_arithmetic_sum ../tests/test_episode.py::test_c012_state_step_equals_steps_length -v` → 2 PASS.

- [ ] T023 [US4] Verify C-011 and C-012 green (no additional code needed — reward accumulation and state.step mutation already in run_episode from T019): `cd src && pytest ../tests/test_episode.py::test_c011_total_reward_arithmetic_sum ../tests/test_episode.py::test_c012_state_step_equals_steps_length -v` → 2 PASS

---

## Phase 7: Polish & Validation

**Purpose**: Lint, format, full suite verification, commit, merge.

- [ ] T024 Run `ruff check src/aatf/episode.py tests/test_episode.py` and fix any issues with `ruff check --fix src/aatf/episode.py tests/test_episode.py`
- [ ] T025 Run `ruff format src/aatf/episode.py tests/test_episode.py` to normalise formatting
- [ ] T026 Run full test suite: `cd src && pytest --tb=short -q 2>&1 | tail -5` — verify ≥204 passed, 4 skipped, 0 failed
- [ ] T027 Stage and commit: `git add src/aatf/episode.py tests/test_episode.py && git commit -m "Add episode loop: run_episode, StepRecord, EpisodeResult (F16)"`
- [ ] T028 Merge to main: `git checkout main && git merge --no-ff 016-e4-episode-loop -m "Merge F16 episode loop"`

---

## Dependencies

```
Phase 1 (Setup) → Phase 2 (All tests written — RED)
Phase 2 → Phase 3 (US1 implementation — GREEN C-001..C-005)
Phase 3 → Phase 4 (US2 verification — GREEN C-006..C-007)
Phase 4 → Phase 5 (US3 verification — GREEN C-008..C-010)
Phase 5 → Phase 6 (US4 verification — GREEN C-011..C-012)
Phase 6 → Phase 7 (Polish + commit)
```

Within Phase 2, T005–T016 (individual test writes) can run in parallel since they all write to the same file — execute sequentially in T005 → T016 order.

Within Phase 7, T024 and T025 can run in parallel (different tools, same files); T026 must follow both.

## Parallel Execution Opportunities

- T024 (`ruff check`) and T025 (`ruff format`) can run in parallel
- T005–T016 are listed sequentially but can be written as a batch to `tests/test_episode.py` in one edit

## Implementation Strategy

**MVP (Phase 3 complete)**: `run_episode` works for the single-step case. From that point, a caller can already wire together a one-step smoke test against the real lab.

**Incremental delivery**:
1. Phase 3 → `run_episode` orchestrates one step correctly (5 contracts green)
2. Phase 4 → exhaustion termination verified (2 more contracts)
3. Phase 5 → step-limit + FR-003 priority verified (3 more contracts)
4. Phase 6 → cumulative result verified (2 more contracts)
5. Phase 7 → merged to main; unblocks F17 (attacker update), F19 (episode logger), F20 (harness)

**Total tasks**: 28 (T001–T028)
- Phase 1 Setup: 3 tasks
- Phase 2 Foundational (tests): 14 tasks (T004–T017)
- Phase 3 US1: 3 tasks
- Phase 4 US2: 1 task
- Phase 5 US3: 1 task
- Phase 6 US4: 1 task
- Phase 7 Polish: 5 tasks
