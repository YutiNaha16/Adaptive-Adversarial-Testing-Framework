# Tasks: Attacker Update Rule — LinUCB (F17)

**Input**: Design documents from `/specs/017-e4-attacker-update/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/linucb-contract.md ✅

**Tests**: TDD — all 10 tests written upfront (red), then implementation drives them green story-by-story.

**Baseline**: 198 passed, 4 skipped, 6 failed (pre-existing). **Target**: ≥208 passed, 4 skipped, 6 failed (+10 tests).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- All paths relative to repo root

---

## Phase 1: Setup

**Purpose**: Record baseline and create stub files.

- [X] T001 Record baseline: `source .venv/bin/activate && cd src && pytest ../tests/ --tb=no -q 2>&1 | tail -3` — confirm 198 passed, 4 skipped, 6 failed
- [X] T002 Create stub `src/aatf/linucb.py` with module docstring and `from __future__ import annotations` only
- [X] T003 Create stub `tests/test_linucb.py` with `from __future__ import annotations` only

---

## Phase 2: Foundational — Write All Tests Upfront (Red)

**Purpose**: Write all 10 tests before any implementation. Verify red: ImportError on `from aatf.linucb import LinUCBModel`.

**Independent test criteria**: `cd src && pytest ../tests/test_linucb.py --tb=short -q` collects 10 tests, all fail with ImportError or AttributeError.

- [X] T004 Write imports + shared setup in `tests/test_linucb.py`:
  ```python
  from __future__ import annotations

  import json
  import math

  import numpy as np

  from aatf.linucb import LinUCBModel
  ```

- [X] T005 Write C-001 in `tests/test_linucb.py` — A_inv correct after one update (d=1, analytic ground truth):
  ```python
  def test_c001_update_a_inv_analytic() -> None:
      model = LinUCBModel(d=1, alpha=1.0)
      ctx = np.array([1.0])
      model.update("a", ctx, reward=1.0)
      A_inv, _ = model._arms["a"]
      assert abs(A_inv[0, 0] - 0.5) < 1e-9
  ```

- [X] T006 Write C-002 in `tests/test_linucb.py` — b correct after one update (d=1):
  ```python
  def test_c002_update_b_analytic() -> None:
      model = LinUCBModel(d=1, alpha=1.0)
      ctx = np.array([1.0])
      model.update("a", ctx, reward=2.0)
      _, b = model._arms["a"]
      assert abs(b[0] - 2.0) < 1e-9
  ```

- [X] T007 Write C-003 in `tests/test_linucb.py` — lazy init creates eye(d) + zeros(d) on first reference:
  ```python
  def test_c003_update_lazy_init() -> None:
      model = LinUCBModel(d=2, alpha=1.0)
      assert "new_action" not in model._arms
      model.update("new_action", np.array([1.0, 0.0]), reward=0.0)
      assert "new_action" in model._arms
      _, b = model._arms["new_action"]
      assert np.allclose(b, np.zeros(2))
  ```

- [X] T008 Write C-004 in `tests/test_linucb.py` — A_inv and b correct after two sequential updates (d=2):
  ```python
  def test_c004_update_two_steps() -> None:
      model = LinUCBModel(d=2, alpha=1.0)
      model.update("a", np.array([1.0, 0.0]), reward=1.0)
      model.update("a", np.array([0.0, 1.0]), reward=0.5)
      A_inv, b = model._arms["a"]
      # Step 1: A_inv=[[0.5,0],[0,1]], b=[1,0]
      # Step 2: x=[0,1]; A_inv-=outer([0,1],[0,1])/2 → [[0.5,0],[0,0.5]], b=[1,0.5]
      assert np.allclose(A_inv, np.array([[0.5, 0.0], [0.0, 0.5]]), atol=1e-9)
      assert np.allclose(b, np.array([1.0, 0.5]), atol=1e-9)
  ```

- [X] T009 Write C-005 in `tests/test_linucb.py` — trained action beats untrained after 5 positive updates:
  ```python
  def test_c005_select_trained_over_untrained() -> None:
      model = LinUCBModel(d=1, alpha=1.0)
      ctx = np.array([1.0])
      for _ in range(5):
          model.update("b_action", ctx, reward=1.0)
      assert model.select_action(["a_action", "b_action"], ctx) == "b_action"
  ```

- [X] T010 Write C-006 in `tests/test_linucb.py` — alphabetical tie-break when all arms unseen:
  ```python
  def test_c006_select_alphabetical_tie_break() -> None:
      model = LinUCBModel(d=2, alpha=1.0)
      ctx = np.array([1.0, 1.0])
      winner = model.select_action(["z_action", "a_action", "m_action"], ctx)
      assert winner == "a_action"
  ```

- [X] T011 Write C-007 in `tests/test_linucb.py` — alpha=0 gives pure greedy (no exploration bonus):
  ```python
  def test_c007_select_alpha_zero_pure_greedy() -> None:
      model = LinUCBModel(d=1, alpha=0.0)
      ctx = np.array([1.0])
      model.update("good", ctx, reward=1.0)
      # "good": theta=[[0.5]]@[1]=[0.5], score=0.5+0=0.5
      # "other": theta=[[1]]@[0]=[0], score=0
      assert model.select_action(["good", "other"], ctx) == "good"
  ```

- [X] T012 Write C-008 in `tests/test_linucb.py` — to_dict() output passes json.dumps without error:
  ```python
  def test_c008_to_dict_json_serialisable() -> None:
      model = LinUCBModel(d=2, alpha=1.5)
      model.update("scan", np.array([1.0, 0.0]), reward=0.8)
      d = model.to_dict()
      serialised = json.dumps(d)  # must not raise
      assert '"scan"' in serialised
      assert d["alpha"] == 1.5
      assert d["d"] == 2
  ```

- [X] T013 Write C-009 in `tests/test_linucb.py` — from_dict() round-trip produces identical select_action():
  ```python
  def test_c009_round_trip_identical_scores() -> None:
      model = LinUCBModel(d=2, alpha=1.0)
      ctx = np.array([1.0, 0.5])
      model.update("tcp_port_scan", ctx, reward=1.0)
      model.update("udp_sweep", ctx, reward=-1.0)
      restored = LinUCBModel.from_dict(model.to_dict())
      available = ["tcp_port_scan", "udp_sweep"]
      assert model.select_action(available, ctx) == restored.select_action(available, ctx)
  ```

- [X] T014 Write C-010 in `tests/test_linucb.py` — from_dict() of fresh model behaves like new LinUCBModel:
  ```python
  def test_c010_round_trip_fresh_model() -> None:
      original = LinUCBModel(d=2, alpha=1.0)
      restored = LinUCBModel.from_dict(original.to_dict())
      ctx = np.array([1.0, 0.0])
      assert original.select_action(["a", "b"], ctx) == "a"
      assert restored.select_action(["a", "b"], ctx) == "a"
  ```

- [X] T015 Verify red phase: `cd src && pytest ../tests/test_linucb.py --tb=short -q 2>&1 | tail -4` — expect ImportError, 10 tests fail

---

## Phase 3: US1 — Parameter Update After a Step

**Story goal**: `update()` applies the Sherman-Morrison rank-1 update exactly. Beliefs initialised lazily to (eye(d), zeros(d)).

**Independent test criteria**: `cd src && pytest ../tests/test_linucb.py::test_c001_update_a_inv_analytic ../tests/test_linucb.py::test_c002_update_b_analytic ../tests/test_linucb.py::test_c003_update_lazy_init ../tests/test_linucb.py::test_c004_update_two_steps -v` → 4 PASS.

- [X] T016 [US1] Write `src/aatf/linucb.py` with full class skeleton, `__init__`, and `_get_or_init_arm`:
  ```python
  """LinUCB contextual-bandit attacker — per-action belief update and UCB selection."""

  from __future__ import annotations

  import math

  import numpy as np


  class LinUCBModel:
      def __init__(
          self,
          d: int,
          alpha: float = 1.0,
          *,
          _arms: dict[str, tuple[np.ndarray, np.ndarray]] | None = None,
      ) -> None:
          self.d = d
          self.alpha = alpha
          self._arms: dict[str, tuple[np.ndarray, np.ndarray]] = (
              _arms if _arms is not None else {}
          )

      def _get_or_init_arm(
          self, action_id: str
      ) -> tuple[np.ndarray, np.ndarray]:
          if action_id not in self._arms:
              self._arms[action_id] = (
                  np.eye(self.d, dtype=float),
                  np.zeros(self.d, dtype=float),
              )
          return self._arms[action_id]
  ```

- [X] T017 [US1] Add `update()` method to `LinUCBModel` in `src/aatf/linucb.py`:
  ```python
      def update(
          self, action_id: str, context: np.ndarray, reward: float
      ) -> None:
          A_inv, b = self._get_or_init_arm(action_id)
          x = A_inv @ context
          A_inv = A_inv - np.outer(x, x) / (1.0 + float(context @ x))
          b = b + reward * context
          self._arms[action_id] = (A_inv, b)
  ```

- [X] T018 [US1] Verify C-001 to C-004 green: `cd src && pytest ../tests/test_linucb.py::test_c001_update_a_inv_analytic ../tests/test_linucb.py::test_c002_update_b_analytic ../tests/test_linucb.py::test_c003_update_lazy_init ../tests/test_linucb.py::test_c004_update_two_steps -v` → 4 PASS

---

## Phase 4: US2 — Action Selection Under Uncertainty

**Story goal**: `select_action()` returns highest-UCB action; ties broken alphabetically; alpha=0 gives pure greedy.

**Independent test criteria**: `cd src && pytest ../tests/test_linucb.py::test_c005_select_trained_over_untrained ../tests/test_linucb.py::test_c006_select_alphabetical_tie_break ../tests/test_linucb.py::test_c007_select_alpha_zero_pure_greedy -v` → 3 PASS.

- [X] T019 [US2] Add `select_action()` method to `LinUCBModel` in `src/aatf/linucb.py`:
  ```python
      def select_action(
          self, available: list[str], context: np.ndarray
      ) -> str:
          best_id = sorted(available)[0]
          best_score = float("-inf")
          for action_id in sorted(available):
              A_inv, b = self._get_or_init_arm(action_id)
              theta = A_inv @ b
              score = float(theta @ context) + self.alpha * math.sqrt(
                  max(0.0, float(context @ A_inv @ context))
              )
              if score > best_score:
                  best_score = score
                  best_id = action_id
          return best_id
  ```

- [X] T020 [US2] Verify C-005 to C-007 green: `cd src && pytest ../tests/test_linucb.py::test_c005_select_trained_over_untrained ../tests/test_linucb.py::test_c006_select_alphabetical_tie_break ../tests/test_linucb.py::test_c007_select_alpha_zero_pure_greedy -v` → 3 PASS

---

## Phase 5: US3 — State Export and Restore

**Story goal**: `to_dict()` produces JSON-safe output; `from_dict()` reconstructs an identical model.

**Independent test criteria**: `cd src && pytest ../tests/test_linucb.py::test_c008_to_dict_json_serialisable ../tests/test_linucb.py::test_c009_round_trip_identical_scores ../tests/test_linucb.py::test_c010_round_trip_fresh_model -v` → 3 PASS.

- [X] T021 [US3] Add `to_dict()` and `from_dict()` to `LinUCBModel` in `src/aatf/linucb.py`:
  ```python
      def to_dict(self) -> dict:
          return {
              "d": self.d,
              "alpha": self.alpha,
              "arms": {
                  action_id: {
                      "A_inv": A_inv.tolist(),
                      "b": b.tolist(),
                  }
                  for action_id, (A_inv, b) in self._arms.items()
              },
          }

      @classmethod
      def from_dict(cls, data: dict) -> LinUCBModel:
          arms = {
              action_id: (
                  np.array(arm["A_inv"], dtype=float),
                  np.array(arm["b"], dtype=float),
              )
              for action_id, arm in data.get("arms", {}).items()
          }
          return cls(d=data["d"], alpha=data["alpha"], _arms=arms)
  ```

- [X] T022 [US3] Verify C-008 to C-010 green: `cd src && pytest ../tests/test_linucb.py::test_c008_to_dict_json_serialisable ../tests/test_linucb.py::test_c009_round_trip_identical_scores ../tests/test_linucb.py::test_c010_round_trip_fresh_model -v` → 3 PASS

---

## Phase 6: Polish & Validation

**Purpose**: Lint, format, full suite verification, commit, merge.

- [X] T023 Run `cd /path/to/repo && ruff check src/aatf/linucb.py tests/test_linucb.py` and fix any issues with `ruff check --fix src/aatf/linucb.py tests/test_linucb.py`
- [X] T024 Run `ruff format src/aatf/linucb.py tests/test_linucb.py`
- [X] T025 Run full suite: `cd src && pytest ../tests/ --tb=short -q 2>&1 | tail -5` — verify ≥208 passed, 4 skipped, 6 failed (same pre-existing failures)
- [X] T026 Stage and commit: `git add src/aatf/linucb.py tests/test_linucb.py && git commit -m "Add LinUCB attacker model: update, select_action, serialisation (F17)"`
- [X] T027 Merge to main: `git checkout main && git merge --no-ff 017-e4-attacker-update -m "Merge F17 LinUCB attacker (017-e4-attacker-update)"`

---

## Dependencies

```
Phase 1 (Setup) → Phase 2 (All tests — RED)
Phase 2 → Phase 3 (US1: __init__ + _get_or_init_arm + update → C-001..C-004 GREEN)
Phase 3 → Phase 4 (US2: select_action → C-005..C-007 GREEN)
Phase 4 → Phase 5 (US3: to_dict + from_dict → C-008..C-010 GREEN)
Phase 5 → Phase 6 (Polish + commit + merge)
```

T023 (`ruff check`) and T024 (`ruff format`) can run in parallel within Phase 6.

## Implementation Strategy

**MVP (Phase 3 complete)**: `__init__`, `_get_or_init_arm`, `update()` — the model can accept reward signals and update beliefs. Already useful for a learning-curve smoke test.

**Incremental delivery**:
1. Phase 3 → belief update correct (4 contracts green)
2. Phase 4 → selection correct, tie-breaking correct, alpha=0 greedy (3 more)
3. Phase 5 → state fully serialisable and restorable (3 more)
4. Phase 6 → merged to main; unblocks F20 (episode harness wiring)

**Total tasks**: 27 (T001–T027)
- Phase 1 Setup: 3 tasks
- Phase 2 Foundational (tests): 12 tasks (T004–T015)
- Phase 3 US1: 3 tasks
- Phase 4 US2: 2 tasks
- Phase 5 US3: 2 tasks
- Phase 6 Polish: 5 tasks
