# Tasks: Evaluator & Metrics (F20)

**Input**: Design documents from `/specs/020-e6-evaluator-metrics/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/metrics-contract.md ✅

**Tests**: TDD — all 17 tests written upfront (red phase), then implementation drives them green story-by-story.

**Baseline**: 220 passed, 4 skipped, 6 failed (pre-existing). **Target**: ≥237 passed, 4 skipped, 6 failed (+17 tests).

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- All paths relative to repo root

---

## Phase 1: Setup

**Purpose**: Record baseline and create stub files.

- [ ] T001 Record baseline: `cd /home/yuti/Adaptive-Adversarial-Testing-Framework && source .venv/bin/activate && cd src && pytest ../tests/ --tb=no -q 2>&1 | tail -3` — confirm 220 passed, 4 skipped, 6 failed
- [ ] T002 Create stub `src/aatf/metrics.py` with module docstring and `from __future__ import annotations` only
- [ ] T003 Create stub `tests/test_metrics.py` with `from __future__ import annotations` only

---

## Phase 2: Foundational — Write All Tests Upfront (Red)

**Purpose**: Write all 17 tests before any implementation. Verify red: ImportError on `from aatf.metrics import EpisodeRecord`.

**Red criteria**: `cd src && pytest ../tests/test_metrics.py --tb=short -q` → ImportError, 17 tests fail.

- [ ] T004 Write imports and helpers in `tests/test_metrics.py`:
  ```python
  from __future__ import annotations

  import pytest

  from aatf.episode import StepRecord
  from aatf.metrics import (
      EpisodeRecord,
      adaptation_gain,
      convergence_episodes,
      detection_rate,
      robustness_score,
  )


  def _step(detected: bool, stage_progress: bool = False, reward: float = 0.0) -> StepRecord:
      return StepRecord(action_id="scan", detected=detected, stage_progress=stage_progress, reward=reward)


  def _ep(episode_index: int, steps: list[StepRecord], *, completed: bool = True) -> EpisodeRecord:
      return EpisodeRecord(
          attacker_class="TestAttacker",
          seed=0,
          steps=steps,
          total_reward=sum(s.reward for s in steps),
          completed=completed,
          episode_index=episode_index,
      )
  ```

- [ ] T005 Write C-001 in `tests/test_metrics.py` — EpisodeRecord construction with known fields:
  ```python
  def test_c001_episode_record_construction() -> None:
      steps = [_step(True), _step(False)]
      rec = _ep(episode_index=0, steps=steps)
      assert rec.attacker_class == "TestAttacker"
      assert rec.seed == 0
      assert rec.steps == steps
      assert rec.completed is True
      assert rec.episode_index == 0
  ```

- [ ] T006 Write C-002 in `tests/test_metrics.py` — EpisodeRecord with completed=False:
  ```python
  def test_c002_episode_record_incomplete() -> None:
      rec = _ep(episode_index=3, steps=[_step(True), _step(True)], completed=False)
      assert rec.completed is False
      assert rec.episode_index == 3
  ```

- [ ] T007 Write C-003 in `tests/test_metrics.py` — EpisodeRecord with empty steps:
  ```python
  def test_c003_episode_record_empty_steps() -> None:
      rec = _ep(episode_index=0, steps=[])
      assert rec.steps == []
      assert rec.total_reward == 0.0
  ```

- [ ] T008 Write C-004 in `tests/test_metrics.py` — detection_rate all detected → 1.0:
  ```python
  def test_c004_detection_rate_all_detected() -> None:
      records = [
          _ep(0, [_step(True), _step(True), _step(True)]),
          _ep(1, [_step(True), _step(True)]),
      ]
      assert detection_rate(records) == 1.0
  ```

- [ ] T009 Write C-005 in `tests/test_metrics.py` — detection_rate none detected → 0.0:
  ```python
  def test_c005_detection_rate_none_detected() -> None:
      records = [
          _ep(0, [_step(False), _step(False)]),
          _ep(1, [_step(False), _step(False), _step(False)]),
      ]
      assert detection_rate(records) == 0.0
  ```

- [ ] T010 Write C-006 in `tests/test_metrics.py` — detection_rate partial → 0.4:
  ```python
  def test_c006_detection_rate_partial() -> None:
      records = [
          _ep(0, [_step(True), _step(True), _step(False)]),
          _ep(1, [_step(False), _step(False)]),
      ]
      assert abs(detection_rate(records) - 0.4) < 1e-9
  ```

- [ ] T011 Write C-007 in `tests/test_metrics.py` — detection_rate empty list → 0.0:
  ```python
  def test_c007_detection_rate_empty() -> None:
      assert detection_rate([]) == 0.0
  ```

- [ ] T012 Write C-008 in `tests/test_metrics.py` — robustness_score uses last window episodes:
  ```python
  def test_c008_robustness_score_last_window() -> None:
      records = (
          [_ep(i, [_step(True)]) for i in range(3)] +
          [_ep(i + 3, [_step(False)]) for i in range(3)]
      )
      assert robustness_score(records, window=3) == 0.0
  ```

- [ ] T013 Write C-009 in `tests/test_metrics.py` — robustness_score window > len uses all records:
  ```python
  def test_c009_robustness_score_window_exceeds_len() -> None:
      records = [_ep(i, [_step(True)]) for i in range(3)]
      assert robustness_score(records, window=20) == 1.0
  ```

- [ ] T014 Write C-010 in `tests/test_metrics.py` — robustness_score empty records → 0.0:
  ```python
  def test_c010_robustness_score_empty() -> None:
      assert robustness_score([], window=5) == 0.0
  ```

- [ ] T015 Write C-011 in `tests/test_metrics.py` — adaptation_gain positive (baseline 0.8, learner 0.5):
  ```python
  def test_c011_adaptation_gain_positive() -> None:
      baseline = [
          _ep(0, [_step(True), _step(True), _step(True), _step(True), _step(False)]),
          _ep(1, [_step(True), _step(True), _step(True), _step(True), _step(False)]),
      ]
      learner = [
          _ep(0, [_step(True), _step(True), _step(False), _step(False), _step(False)]),
          _ep(1, [_step(True), _step(True), _step(True), _step(False), _step(False)]),
      ]
      assert abs(adaptation_gain(baseline, learner) - 30.0) < 1e-9
  ```

- [ ] T016 Write C-012 in `tests/test_metrics.py` — adaptation_gain zero (equal detection rates):
  ```python
  def test_c012_adaptation_gain_zero() -> None:
      records = [_ep(i, [_step(True), _step(False)]) for i in range(3)]
      assert adaptation_gain(records, records) == 0.0
  ```

- [ ] T017 Write C-013 in `tests/test_metrics.py` — adaptation_gain negative (learner worse):
  ```python
  def test_c013_adaptation_gain_negative() -> None:
      baseline = [
          _ep(0, [_step(True), _step(False), _step(False), _step(False), _step(False)]),
          _ep(1, [_step(True), _step(True), _step(False), _step(False), _step(False)]),
      ]
      learner = [
          _ep(0, [_step(True), _step(True), _step(True), _step(False), _step(False)]),
          _ep(1, [_step(True), _step(True), _step(True), _step(False), _step(False)]),
      ]
      assert abs(adaptation_gain(baseline, learner) - (-30.0)) < 1e-9
  ```

- [ ] T018 Write C-014 in `tests/test_metrics.py` — convergence at known episode (window=3, threshold=0.5):
  ```python
  def test_c014_convergence_at_known_episode() -> None:
      records = (
          [_ep(i, [_step(True)]) for i in range(2)] +
          [_ep(i + 2, [_step(False)]) for i in range(3)]
      )
      # i=3: records[1:4] = [T, F, F] → dr=1/3 < 0.5 → return records[3].episode_index = 3
      assert convergence_episodes(records, threshold=0.5, window=3) == 3
  ```

- [ ] T019 Write C-015 in `tests/test_metrics.py` — no convergence (all detected):
  ```python
  def test_c015_no_convergence() -> None:
      records = [_ep(i, [_step(True)]) for i in range(5)]
      assert convergence_episodes(records, threshold=0.5) is None
  ```

- [ ] T020 Write C-016 in `tests/test_metrics.py` — immediate convergence at episode 0:
  ```python
  def test_c016_immediate_convergence() -> None:
      records = [_ep(0, [_step(False)]), _ep(1, [_step(False)])]
      assert convergence_episodes(records, threshold=0.5, window=1) == 0
  ```

- [ ] T021 Write C-017 in `tests/test_metrics.py` — empty records → None:
  ```python
  def test_c017_convergence_empty_records() -> None:
      assert convergence_episodes([]) is None
  ```

- [ ] T022 Verify red phase: `cd src && pytest ../tests/test_metrics.py --tb=short -q 2>&1 | tail -4` — expect ImportError, 17 tests fail

---

## Phase 3: US1 — EpisodeRecord Contract (P1)

**Story goal**: `EpisodeRecord` dataclass defined and importable from `aatf.metrics`; all three field-access scenarios (full construction, completed=False, empty steps) green.

**Independent test criteria**: `cd src && pytest ../tests/test_metrics.py::test_c001_episode_record_construction ../tests/test_metrics.py::test_c002_episode_record_incomplete ../tests/test_metrics.py::test_c003_episode_record_empty_steps -v` → 3 PASS.

- [ ] T023 [US1] Write `src/aatf/metrics.py` — module header + `EpisodeRecord` dataclass:
  ```python
  """Offline evaluator — Phase 1 headline metrics."""
  from __future__ import annotations

  from dataclasses import dataclass

  from aatf.episode import StepRecord


  @dataclass(frozen=True)
  class EpisodeRecord:
      attacker_class: str
      seed: int
      steps: list[StepRecord]
      total_reward: float
      completed: bool
      episode_index: int
  ```

- [ ] T024 [US1] Verify C-001..C-003 green: `cd src && pytest ../tests/test_metrics.py::test_c001_episode_record_construction ../tests/test_metrics.py::test_c002_episode_record_incomplete ../tests/test_metrics.py::test_c003_episode_record_empty_steps -v` → 3 PASS

---

## Phase 4: US2 — detection_rate (P2)

**Story goal**: `detection_rate` correctly computes step-weighted fraction; handles all detected, none detected, partial, and empty input.

**Independent test criteria**: `cd src && pytest ../tests/test_metrics.py::test_c004_detection_rate_all_detected ../tests/test_metrics.py::test_c005_detection_rate_none_detected ../tests/test_metrics.py::test_c006_detection_rate_partial ../tests/test_metrics.py::test_c007_detection_rate_empty -v` → 4 PASS.

- [ ] T025 [US2] Add `detection_rate` to `src/aatf/metrics.py`:
  ```python
  def detection_rate(records: list[EpisodeRecord]) -> float:
      total = sum(len(r.steps) for r in records)
      if total == 0:
          return 0.0
      detected = sum(1 for r in records for s in r.steps if s.detected)
      return detected / total
  ```

- [ ] T026 [US2] Verify C-004..C-007 green: `cd src && pytest ../tests/test_metrics.py::test_c004_detection_rate_all_detected ../tests/test_metrics.py::test_c005_detection_rate_none_detected ../tests/test_metrics.py::test_c006_detection_rate_partial ../tests/test_metrics.py::test_c007_detection_rate_empty -v` → 4 PASS

---

## Phase 5: US3 — robustness_score & adaptation_gain (P3)

**Story goal**: `robustness_score` slices last-window episodes and delegates to `detection_rate`; `adaptation_gain` computes (baseline − learner) × 100; all edge cases (window > len, empty, equal, negative) green.

**Independent test criteria**: `cd src && pytest ../tests/test_metrics.py::test_c008_robustness_score_last_window ../tests/test_metrics.py::test_c009_robustness_score_window_exceeds_len ../tests/test_metrics.py::test_c010_robustness_score_empty ../tests/test_metrics.py::test_c011_adaptation_gain_positive ../tests/test_metrics.py::test_c012_adaptation_gain_zero ../tests/test_metrics.py::test_c013_adaptation_gain_negative -v` → 6 PASS.

- [ ] T027 [US3] Add `robustness_score` and `adaptation_gain` to `src/aatf/metrics.py`:
  ```python
  def robustness_score(records: list[EpisodeRecord], window: int) -> float:
      if window <= 0:
          return 0.0
      return detection_rate(records[-window:])


  def adaptation_gain(
      baseline_records: list[EpisodeRecord],
      learner_records: list[EpisodeRecord],
  ) -> float:
      return (detection_rate(baseline_records) - detection_rate(learner_records)) * 100.0
  ```

- [ ] T028 [US3] Verify C-008..C-013 green: `cd src && pytest ../tests/test_metrics.py::test_c008_robustness_score_last_window ../tests/test_metrics.py::test_c009_robustness_score_window_exceeds_len ../tests/test_metrics.py::test_c010_robustness_score_empty ../tests/test_metrics.py::test_c011_adaptation_gain_positive ../tests/test_metrics.py::test_c012_adaptation_gain_zero ../tests/test_metrics.py::test_c013_adaptation_gain_negative -v` → 6 PASS

---

## Phase 6: US4 — convergence_episodes (P4)

**Story goal**: `convergence_episodes` scans with a sliding trailing window, returns the stored `episode_index` of the first crossing below `threshold`, or `None` if never.

**Independent test criteria**: `cd src && pytest ../tests/test_metrics.py::test_c014_convergence_at_known_episode ../tests/test_metrics.py::test_c015_no_convergence ../tests/test_metrics.py::test_c016_immediate_convergence ../tests/test_metrics.py::test_c017_convergence_empty_records -v` → 4 PASS.

- [ ] T029 [US4] Add `convergence_episodes` to `src/aatf/metrics.py`:
  ```python
  def convergence_episodes(
      records: list[EpisodeRecord],
      threshold: float = 0.5,
      *,
      window: int = 5,
  ) -> int | None:
      for i, record in enumerate(records):
          start = max(0, i - window + 1)
          if detection_rate(records[start : i + 1]) < threshold:
              return record.episode_index
      return None
  ```

- [ ] T030 [US4] Verify C-014..C-017 green: `cd src && pytest ../tests/test_metrics.py::test_c014_convergence_at_known_episode ../tests/test_metrics.py::test_c015_no_convergence ../tests/test_metrics.py::test_c016_immediate_convergence ../tests/test_metrics.py::test_c017_convergence_empty_records -v` → 4 PASS

---

## Phase 7: Polish & Validation

**Purpose**: Lint, format, full suite verification, commit, merge.

- [ ] T031 [P] Run `ruff check src/aatf/metrics.py tests/test_metrics.py` — fix any issues with `ruff check --fix src/aatf/metrics.py tests/test_metrics.py`
- [ ] T032 [P] Run `ruff format src/aatf/metrics.py tests/test_metrics.py`
- [ ] T033 Run full suite: `cd src && pytest ../tests/ --tb=short -q 2>&1 | tail -5` — verify ≥237 passed, 4 skipped, 6 failed (same pre-existing failures)
- [ ] T034 Stage and commit: `git add src/aatf/metrics.py tests/test_metrics.py specs/020-e6-evaluator-metrics/tasks.md && git commit -m "Add EpisodeRecord + 4 metric functions: detection_rate, robustness_score, adaptation_gain, convergence_episodes (F20)"`
- [ ] T035 Merge to main: `git checkout main && git merge --no-ff 020-e6-evaluator-metrics -m "Merge F20 Evaluator metrics (020-e6-evaluator-metrics)"`

---

## Dependencies

```
Phase 1 (Setup) → Phase 2 (All 17 tests — RED)
Phase 2 → Phase 3 (US1: EpisodeRecord → C-001..C-003 GREEN)
Phase 3 → Phase 4 (US2: detection_rate → C-004..C-007 GREEN)
Phase 4 → Phase 5 (US3: robustness_score + adaptation_gain → C-008..C-013 GREEN)
Phase 5 → Phase 6 (US4: convergence_episodes → C-014..C-017 GREEN)
Phase 6 → Phase 7 (Polish + commit + merge)
```

T031 (`ruff check`) and T032 (`ruff format`) can run in parallel within Phase 7.

Phases 4–6 each add one or two functions; no US is blocked by another US's implementation (tests already written and isolated per-story). US2 (`detection_rate`) must be complete before US3 and US4 because both delegate to it.

## Implementation Strategy

**MVP (Phase 3 complete)**: `EpisodeRecord` is importable and correctly stores episode data. Already useful for any caller that wants to build records for later analysis.

**Incremental delivery**:
1. Phase 3 → `EpisodeRecord` contract stable (3 contracts green)
2. Phase 4 → `detection_rate` correct (4 more contracts green; the foundational metric)
3. Phase 5 → `robustness_score` + `adaptation_gain` correct (6 more contracts green; RQ1 answerable)
4. Phase 6 → `convergence_episodes` correct (4 more contracts green; learning speed measurable)
5. Phase 7 → merged to main; unblocks F21 (multi-seed orchestration) and Phase 1 gate evaluation

**Total tasks**: 35 (T001–T035)
- Phase 1 Setup: 3 tasks
- Phase 2 Foundational (all 17 tests): 19 tasks (T004–T022)
- Phase 3 US1: 2 tasks
- Phase 4 US2: 2 tasks
- Phase 5 US3: 2 tasks
- Phase 6 US4: 2 tasks
- Phase 7 Polish: 5 tasks
