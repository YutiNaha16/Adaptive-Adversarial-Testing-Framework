# Tasks: Attacker Interface + Baselines (F18)

**Input**: Design documents from `/specs/018-e5-attacker-baselines/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/attacker-contract.md ✅

**Tests**: TDD — all 12 tests written upfront (red), then implementation drives them green story-by-story.

**Baseline**: 208 passed, 4 skipped, 6 failed (pre-existing). **Target**: ≥220 passed, 4 skipped, 6 failed (+12 tests).

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- All paths relative to repo root

---

## Phase 1: Setup

**Purpose**: Record baseline and create stub files.

- [ ] T001 Record baseline: `cd /home/yuti/Adaptive-Adversarial-Testing-Framework && source .venv/bin/activate && cd src && pytest ../tests/ --tb=no -q 2>&1 | tail -3` — confirm 208 passed, 4 skipped, 6 failed
- [ ] T002 Create stub `src/aatf/attacker.py` with module docstring and `from __future__ import annotations` only
- [ ] T003 Create stub `tests/test_attacker.py` with `from __future__ import annotations` only

---

## Phase 2: Foundational — Write All Tests Upfront (Red)

**Purpose**: Write all 12 tests before any implementation. Verify red: ImportError on `from aatf.attacker import Attacker`.

**Red criteria**: `cd src && pytest ../tests/test_attacker.py --tb=short -q` → ImportError, 12 tests fail.

- [ ] T004 Write imports in `tests/test_attacker.py`:
  ```python
  from __future__ import annotations

  import numpy as np
  import pytest

  from aatf.attacker import Attacker, FixedScriptAttacker, LinUCBAttacker, RandomAttacker
  from aatf.linucb import LinUCBModel
  ```

- [ ] T005 Write C-001 in `tests/test_attacker.py` — all three classes are instances of Attacker:
  ```python
  def test_c001_all_classes_are_attacker_instances() -> None:
      model = LinUCBModel(d=1)
      assert isinstance(RandomAttacker(), Attacker)
      assert isinstance(FixedScriptAttacker(), Attacker)
      assert isinstance(LinUCBAttacker(model), Attacker)
  ```

- [ ] T006 Write C-002 in `tests/test_attacker.py` — choose_action returns value from available:
  ```python
  def test_c002_choose_action_returns_from_available() -> None:
      available = ["tcp_port_scan", "icmp_ping_sweep", "dns_subdomain_enum"]
      ctx = np.zeros(1)
      model = LinUCBModel(d=1)
      for attacker in [RandomAttacker(), FixedScriptAttacker(), LinUCBAttacker(model)]:
          result = attacker.choose_action(available, ctx)
          assert result in available
  ```

- [ ] T007 Write C-003 in `tests/test_attacker.py` — observe completes without error on all:
  ```python
  def test_c003_observe_no_error_all_implementations() -> None:
      ctx = np.array([1.0])
      model = LinUCBModel(d=1)
      for attacker in [RandomAttacker(), FixedScriptAttacker(), LinUCBAttacker(model)]:
          attacker.observe("tcp_port_scan", ctx, reward=1.0)
  ```

- [ ] T008 Write C-004 in `tests/test_attacker.py` — RandomAttacker seeded determinism:
  ```python
  def test_c004_random_attacker_seeded_determinism() -> None:
      available = ["a", "b", "c"]
      ctx = np.zeros(1)
      seq1 = [RandomAttacker(seed=42).choose_action(available, ctx) for _ in range(5)]
      rng2 = RandomAttacker(seed=42)
      seq2 = [rng2.choose_action(available, ctx) for _ in range(5)]
      assert seq1 == seq2
  ```

- [ ] T009 Write C-005 in `tests/test_attacker.py` — RandomAttacker single-element available:
  ```python
  def test_c005_random_attacker_single_element() -> None:
      attacker = RandomAttacker(seed=0)
      for _ in range(10):
          assert attacker.choose_action(["only_action"], np.zeros(1)) == "only_action"
  ```

- [ ] T010 Write C-006 in `tests/test_attacker.py` — RandomAttacker raises ValueError on empty:
  ```python
  def test_c006_random_attacker_empty_available_raises() -> None:
      attacker = RandomAttacker()
      with pytest.raises(ValueError):
          attacker.choose_action([], np.zeros(1))
  ```

- [ ] T011 Write C-007 in `tests/test_attacker.py` — RandomAttacker observe is a no-op (RNG unaffected):
  ```python
  def test_c007_random_attacker_observe_noop() -> None:
      r1 = RandomAttacker(seed=7)
      r2 = RandomAttacker(seed=7)
      available = ["x", "y", "z"]
      ctx = np.zeros(1)
      r1.choose_action(available, ctx)
      r1.observe("x", ctx, reward=-1.0)  # must not advance RNG
      r1.choose_action(available, ctx)
      r2.choose_action(available, ctx)
      # 3rd choose_action on r1 must equal 3rd on r2 (same number of choose_action calls)
      assert r1.choose_action(available, ctx) == r2.choose_action(available, ctx)
  ```

- [ ] T012 Write C-008 in `tests/test_attacker.py` — FixedScriptAttacker explicit cycle:
  ```python
  def test_c008_fixed_script_attacker_explicit_cycle() -> None:
      attacker = FixedScriptAttacker(script=["x", "y"])
      ctx = np.zeros(1)
      results = [attacker.choose_action(["x", "y"], ctx) for _ in range(4)]
      assert results == ["x", "y", "x", "y"]
  ```

- [ ] T013 Write C-009 in `tests/test_attacker.py` — FixedScriptAttacker default alphabetical script:
  ```python
  def test_c009_fixed_script_attacker_default_alphabetical() -> None:
      attacker = FixedScriptAttacker()
      ctx = np.zeros(1)
      first = attacker.choose_action(["c_action", "a_action", "b_action"], ctx)
      assert first == "a_action"
      assert attacker.choose_action(["c_action", "a_action", "b_action"], ctx) == "b_action"
      assert attacker.choose_action(["c_action", "a_action", "b_action"], ctx) == "c_action"
      assert attacker.choose_action(["c_action", "a_action", "b_action"], ctx) == "a_action"
  ```

- [ ] T014 Write C-010 in `tests/test_attacker.py` — FixedScriptAttacker single-element repeats:
  ```python
  def test_c010_fixed_script_attacker_single_element() -> None:
      attacker = FixedScriptAttacker(script=["only"])
      ctx = np.zeros(1)
      for _ in range(5):
          assert attacker.choose_action(["only"], ctx) == "only"
  ```

- [ ] T015 Write C-011 in `tests/test_attacker.py` — LinUCBAttacker observe delegates to model.update:
  ```python
  def test_c011_linucb_attacker_observe_mutates_model() -> None:
      model = LinUCBModel(d=1, alpha=1.0)
      attacker = LinUCBAttacker(model)
      ctx = np.array([1.0])
      attacker.observe("scan", ctx, reward=1.0)
      assert "scan" in model._arms
      _, b = model._arms["scan"]
      assert abs(b[0] - 1.0) < 1e-9
  ```

- [ ] T016 Write C-012 in `tests/test_attacker.py` — LinUCBAttacker choose_action matches model.select_action:
  ```python
  def test_c012_linucb_attacker_choose_action_matches_model() -> None:
      model = LinUCBModel(d=1, alpha=1.0)
      attacker = LinUCBAttacker(model)
      ctx = np.array([1.0])
      available = ["a_action", "b_action"]
      assert attacker.choose_action(available, ctx) == model.select_action(available, ctx)
  ```

- [ ] T017 Verify red phase: `cd src && pytest ../tests/test_attacker.py --tb=short -q 2>&1 | tail -4` — expect ImportError, 12 tests fail

---

## Phase 3: US1 — Common Attacker Interface (P1)

**Story goal**: `Attacker` ABC defined; all three concrete classes satisfy `isinstance(obj, Attacker)`; `choose_action` and `observe` are callable on all three.

**Independent test criteria**: `cd src && pytest ../tests/test_attacker.py::test_c001_all_classes_are_attacker_instances ../tests/test_attacker.py::test_c002_choose_action_returns_from_available ../tests/test_attacker.py::test_c003_observe_no_error_all_implementations -v` → 3 PASS.

- [ ] T018 [US1] Write `src/aatf/attacker.py` with full module structure — Attacker ABC + all three implementations:
  ```python
  """Attacker policy interface and baseline implementations."""

  from __future__ import annotations

  import itertools
  import random
  from abc import ABC, abstractmethod
  from collections.abc import Iterator

  import numpy as np

  from aatf.linucb import LinUCBModel


  class Attacker(ABC):
      @abstractmethod
      def choose_action(self, available: list[str], context: np.ndarray) -> str: ...

      @abstractmethod
      def observe(self, action_id: str, context: np.ndarray, reward: float) -> None: ...


  class RandomAttacker(Attacker):
      def __init__(self, seed: int = 0) -> None:
          self._rng = random.Random(seed)

      def choose_action(self, available: list[str], context: np.ndarray) -> str:
          if not available:
              raise ValueError("available must be non-empty")
          return self._rng.choice(available)

      def observe(self, action_id: str, context: np.ndarray, reward: float) -> None:
          pass


  class FixedScriptAttacker(Attacker):
      def __init__(self, script: list[str] | None = None) -> None:
          self._script: list[str] | None = script
          self._cycle: Iterator[str] | None = None

      def choose_action(self, available: list[str], context: np.ndarray) -> str:
          if self._cycle is None:
              if self._script is None:
                  self._script = sorted(available)
              self._cycle = itertools.cycle(self._script)
          return next(self._cycle)

      def observe(self, action_id: str, context: np.ndarray, reward: float) -> None:
          pass


  class LinUCBAttacker(Attacker):
      def __init__(self, model: LinUCBModel) -> None:
          self._model = model

      def choose_action(self, available: list[str], context: np.ndarray) -> str:
          return self._model.select_action(available, context)

      def observe(self, action_id: str, context: np.ndarray, reward: float) -> None:
          self._model.update(action_id, context, reward)
  ```

- [ ] T019 [US1] Verify C-001 to C-003 green: `cd src && pytest ../tests/test_attacker.py::test_c001_all_classes_are_attacker_instances ../tests/test_attacker.py::test_c002_choose_action_returns_from_available ../tests/test_attacker.py::test_c003_observe_no_error_all_implementations -v` → 3 PASS

---

## Phase 4: US2 — Non-Learning Baselines (P2)

**Story goal**: `RandomAttacker` seeded determinism, single-element, ValueError on empty, observe no-op; `FixedScriptAttacker` explicit cycle, default alphabetical, single-element.

**Independent test criteria**: `cd src && pytest ../tests/test_attacker.py::test_c004_random_attacker_seeded_determinism ../tests/test_attacker.py::test_c005_random_attacker_single_element ../tests/test_attacker.py::test_c006_random_attacker_empty_available_raises ../tests/test_attacker.py::test_c007_random_attacker_observe_noop ../tests/test_attacker.py::test_c008_fixed_script_attacker_explicit_cycle ../tests/test_attacker.py::test_c009_fixed_script_attacker_default_alphabetical ../tests/test_attacker.py::test_c010_fixed_script_attacker_single_element -v` → 7 PASS.

- [ ] T020 [US2] Verify C-004 to C-010 green (no new code needed — all implemented in T018): `cd src && pytest ../tests/test_attacker.py::test_c004_random_attacker_seeded_determinism ../tests/test_attacker.py::test_c005_random_attacker_single_element ../tests/test_attacker.py::test_c006_random_attacker_empty_available_raises ../tests/test_attacker.py::test_c007_random_attacker_observe_noop ../tests/test_attacker.py::test_c008_fixed_script_attacker_explicit_cycle ../tests/test_attacker.py::test_c009_fixed_script_attacker_default_alphabetical ../tests/test_attacker.py::test_c010_fixed_script_attacker_single_element -v` → 7 PASS

---

## Phase 5: US3 — LinUCB Wrapped Behind Interface (P3)

**Story goal**: `LinUCBAttacker.observe` delegates to `model.update` (model state changes); `LinUCBAttacker.choose_action` delegates to `model.select_action` (returns same result as direct call).

**Independent test criteria**: `cd src && pytest ../tests/test_attacker.py::test_c011_linucb_attacker_observe_mutates_model ../tests/test_attacker.py::test_c012_linucb_attacker_choose_action_matches_model -v` → 2 PASS.

- [ ] T021 [US3] Verify C-011 to C-012 green (no new code needed — implemented in T018): `cd src && pytest ../tests/test_attacker.py::test_c011_linucb_attacker_observe_mutates_model ../tests/test_attacker.py::test_c012_linucb_attacker_choose_action_matches_model -v` → 2 PASS

---

## Phase 6: Polish & Validation

**Purpose**: Lint, format, full suite verification, commit, merge.

- [ ] T022 Run `ruff check src/aatf/attacker.py tests/test_attacker.py` — fix any issues with `ruff check --fix src/aatf/attacker.py tests/test_attacker.py`
- [ ] T023 [P] Run `ruff format src/aatf/attacker.py tests/test_attacker.py`
- [ ] T024 Run full suite: `cd src && pytest ../tests/ --tb=short -q 2>&1 | tail -5` — verify ≥220 passed, 4 skipped, 6 failed (same pre-existing failures)
- [ ] T025 Stage and commit: `git add src/aatf/attacker.py tests/test_attacker.py specs/018-e5-attacker-baselines/tasks.md && git commit -m "Add Attacker ABC + RandomAttacker, FixedScriptAttacker, LinUCBAttacker (F18)"`
- [ ] T026 Merge to main: `git checkout main && git merge --no-ff 018-e5-attacker-baselines -m "Merge F18 Attacker interface + baselines (018-e5-attacker-baselines)"`

---

## Dependencies

```
Phase 1 (Setup) → Phase 2 (All 12 tests — RED)
Phase 2 → Phase 3 (US1: Attacker ABC + all 3 impls → C-001..C-003 GREEN)
Phase 3 → Phase 4 (US2: RandomAttacker + FixedScriptAttacker → C-004..C-010 GREEN)
Phase 4 → Phase 5 (US3: LinUCBAttacker → C-011..C-012 GREEN)
Phase 5 → Phase 6 (Polish + commit + merge)
```

T022 (`ruff check`) and T023 (`ruff format`) can run in parallel within Phase 6.

Phases 4 and 5 require no new implementation code (all written in T018) — they are pure verification checkpoints.

## Implementation Strategy

**MVP (Phase 3 complete)**: `Attacker` ABC and all three concrete classes are instantiable and satisfy the interface. Already useful for episode loop wiring (F20+).

**Incremental delivery**:
1. Phase 3 → interface correct, all three classes drop-in compatible (3 contracts green)
2. Phase 4 → RandomAttacker seeded + FixedScriptAttacker cycle correct (7 more contracts green)
3. Phase 5 → LinUCBAttacker delegation verified (2 more contracts green)
4. Phase 6 → merged to main; unblocks F19 (Q-learning) and F20 (episode harness)

**Note**: Because the entire implementation is written in one task (T018), phases 4 and 5 are verification-only. This is safe — the implementation is short (~50 lines) and fully specified in plan.md with no ambiguity.

**Total tasks**: 26 (T001–T026)
- Phase 1 Setup: 3 tasks
- Phase 2 Foundational (tests): 14 tasks (T004–T017)
- Phase 3 US1: 2 tasks
- Phase 4 US2: 1 task (verification only)
- Phase 5 US3: 1 task (verification only)
- Phase 6 Polish: 5 tasks
