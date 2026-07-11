# Tasks: Ground-Truth Validation Harness (F22)

**Input**: Design documents from `/specs/024-e6-ground-truth-validation/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ground-truth-contract.md ✅

**TDD approach**: Write all 12 tests first (red phase → ImportError), then implement (green).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Record baseline and verify upstream imports are available.

- [ ] T001 Record test baseline: `cd src && pytest --tb=no -q 2>&1 | tail -3` — confirm 286 passed, 4 skipped, 6 failed
- [ ] T002 Verify upstream import available: `python -c "from aatf.explainability import ActionExplanation; print(ActionExplanation.__dataclass_fields__.keys())"` from within venv — confirm all 8 fields present (action_id, suricata_category, description, evasion_count, total_count, evasion_rate, remediation, false_positive_risk)

**Checkpoint**: Baseline recorded; ActionExplanation confirmed importable with all 8 fields.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Write all 12 tests upfront — these must fail (ImportError) before implementation.

**⚠️ CRITICAL**: All tests must be written and confirmed RED before any implementation begins.

- [ ] T003 Create `tests/test_ground_truth.py` with the `_expl` helper and all 12 contract tests (C-001..C-012) as described below:

  **File header and helper**:
  ```python
  """Tests for aatf.ground_truth — 12 contracts C-001..C-012."""
  from __future__ import annotations

  import pytest
  from dataclasses import FrozenInstanceError

  from aatf.explainability import ActionExplanation
  from aatf.ground_truth import (
      SURICATA_SID_CATEGORIES,
      ValidationResult,
      validate_blind_spots,
  )


  def _expl(action_id: str, suricata_category: str) -> ActionExplanation:
      return ActionExplanation(
          action_id=action_id,
          suricata_category=suricata_category,
          description="test",
          evasion_count=1,
          total_count=1,
          evasion_rate=1.0,
          remediation="fix it",
          false_positive_risk="low",
      )
  ```

  **C-001 — importability**:
  ```python
  def test_c001_importability():
      from aatf.ground_truth import validate_blind_spots, ValidationResult, SURICATA_SID_CATEGORIES  # noqa: F401
  ```

  **C-002 — ValidationResult field types**:
  ```python
  def test_c002_validation_result_field_types():
      r = ValidationResult(
          blind_spot_precision=0.5,
          true_positives=1,
          false_positives=1,
          total_reported=2,
          disabled_sid_count=1,
      )
      assert isinstance(r.blind_spot_precision, float)
      assert isinstance(r.true_positives, int)
      assert isinstance(r.false_positives, int)
      assert isinstance(r.total_reported, int)
      assert isinstance(r.disabled_sid_count, int)
  ```

  **C-003 — ValidationResult immutable**:
  ```python
  def test_c003_validation_result_immutable():
      r = ValidationResult(
          blind_spot_precision=0.5,
          true_positives=1,
          false_positives=1,
          total_reported=2,
          disabled_sid_count=1,
      )
      with pytest.raises((FrozenInstanceError, AttributeError)):
          r.blind_spot_precision = 0.9
  ```

  **C-004 — meets_gate True when >= 0.8**:
  ```python
  def test_c004_meets_gate_true_above_threshold():
      r = ValidationResult(
          blind_spot_precision=0.85,
          true_positives=17,
          false_positives=3,
          total_reported=20,
          disabled_sid_count=5,
      )
      assert r.meets_gate is True
  ```

  **C-005 — meets_gate False when < 0.8**:
  ```python
  def test_c005_meets_gate_false_below_threshold():
      r = ValidationResult(
          blind_spot_precision=0.75,
          true_positives=3,
          false_positives=1,
          total_reported=4,
          disabled_sid_count=2,
      )
      assert r.meets_gate is False
  ```

  **C-006 — meets_gate True at boundary 0.8 exactly**:
  ```python
  def test_c006_meets_gate_boundary_inclusive():
      r = ValidationResult(
          blind_spot_precision=0.8,
          true_positives=4,
          false_positives=1,
          total_reported=5,
          disabled_sid_count=2,
      )
      assert r.meets_gate is True
  ```

  **C-007 — both explanations confirmed**:
  ```python
  def test_c007_both_confirmed_precision_one():
      result = validate_blind_spots(
          [_expl("a", "ET SCAN"), _expl("b", "ET BRUTE_FORCE")],
          {"2001219", "2002087"},
      )
      assert result.true_positives == 2
      assert result.false_positives == 0
      assert result.blind_spot_precision == pytest.approx(1.0)
      assert result.total_reported == 2
      assert result.disabled_sid_count == 2
  ```

  **C-008 — one confirmed one not**:
  ```python
  def test_c008_one_confirmed_one_not():
      result = validate_blind_spots(
          [_expl("a", "ET SCAN"), _expl("b", "ET EXPLOIT")],
          {"2001219"},
      )
      assert result.true_positives == 1
      assert result.false_positives == 1
      assert result.blind_spot_precision == pytest.approx(0.5)
  ```

  **C-009 — empty explanations**:
  ```python
  def test_c009_empty_explanations():
      result = validate_blind_spots([], {"2001219"})
      assert result.blind_spot_precision == 0.0
      assert result.true_positives == 0
      assert result.false_positives == 0
      assert result.total_reported == 0
      assert result.disabled_sid_count == 1
  ```

  **C-010 — empty disabled_sids**:
  ```python
  def test_c010_empty_disabled_sids():
      result = validate_blind_spots([_expl("a", "ET SCAN")], set())
      assert result.blind_spot_precision == 0.0
      assert result.true_positives == 0
      assert result.false_positives == 1
      assert result.disabled_sid_count == 0
  ```

  **C-011 — unknown SID ignored**:
  ```python
  def test_c011_unknown_sid_ignored():
      result = validate_blind_spots([_expl("a", "ET SCAN")], {"9999999"})
      assert result.true_positives == 0
      assert result.false_positives == 1
      assert result.blind_spot_precision == 0.0
  ```

  **C-012 — SURICATA_SID_CATEGORIES covers all 8 Phase 1 categories**:
  ```python
  def test_c012_sid_categories_covers_all_phase1():
      required = {
          "ET SCAN", "ET BRUTE_FORCE", "ET EXPLOIT", "ET DNS",
          "ET POLICY", "ET TROJAN", "ET WEB_CLIENT", "ET WEB_SERVER",
      }
      assert required <= set(SURICATA_SID_CATEGORIES.values())
  ```

- [ ] T004 Run tests to confirm RED state: `cd src && pytest ../tests/test_ground_truth.py -v 2>&1 | tail -20` — expect ImportError/ModuleNotFoundError for `aatf.ground_truth` across all 12 tests; confirm 0 passed

**Checkpoint**: 12 tests written, all failing with ImportError. Ready to implement.

---

## Phase 3: User Story 1 — Core Validation (Priority: P1) 🎯 MVP

**Goal**: `validate_blind_spots` function + `ValidationResult` dataclass; covers C-001..C-003, C-007..C-011.

**Independent Test**: `cd src && pytest ../tests/test_ground_truth.py -k "c001 or c002 or c003 or c007 or c008 or c009 or c010 or c011" -v` — all 8 must pass.

- [ ] T005 [US1] Create `src/aatf/ground_truth.py` (~55 LOC) with exact content:

  ```python
  """Ground-truth validation harness — computes Blind-Spot Precision against disabled SIDs."""
  from __future__ import annotations

  from dataclasses import dataclass

  from aatf.explainability import ActionExplanation

  SURICATA_SID_CATEGORIES: dict[str, str] = {
      "2001219": "ET SCAN",
      "2008581": "ET SCAN",
      "2002087": "ET BRUTE_FORCE",
      "2019284": "ET BRUTE_FORCE",
      "2012648": "ET EXPLOIT",
      "2016778": "ET DNS",
      "2013028": "ET POLICY",
      "2014726": "ET TROJAN",
      "2010935": "ET WEB_CLIENT",
      "2009714": "ET WEB_SERVER",
  }


  @dataclass(frozen=True)
  class ValidationResult:
      blind_spot_precision: float
      true_positives: int
      false_positives: int
      total_reported: int
      disabled_sid_count: int

      @property
      def meets_gate(self) -> bool:
          return self.blind_spot_precision >= 0.8


  def validate_blind_spots(
      explanations: list[ActionExplanation],
      disabled_sids: set[str],
  ) -> ValidationResult:
      disabled_categories = {
          SURICATA_SID_CATEGORIES[s] for s in disabled_sids if s in SURICATA_SID_CATEGORIES
      }
      tp = sum(1 for e in explanations if e.suricata_category in disabled_categories)
      total = len(explanations)
      fp = total - tp
      precision = tp / total if total > 0 else 0.0
      return ValidationResult(
          blind_spot_precision=precision,
          true_positives=tp,
          false_positives=fp,
          total_reported=total,
          disabled_sid_count=len(disabled_sids),
      )
  ```

- [ ] T006 [US1] Run US1 contracts green: `cd src && pytest ../tests/test_ground_truth.py -k "c001 or c002 or c003 or c007 or c008 or c009 or c010 or c011" -v` — confirm 8 passed, 0 failed

**Checkpoint**: US1 complete — core validation works, ValidationResult is correct shape.

---

## Phase 4: User Story 2 — SID-to-Category Lookup (Priority: P2)

**Goal**: `SURICATA_SID_CATEGORIES` covers all 8 Phase 1 categories; covers C-012.

**Independent Test**: `cd src && pytest ../tests/test_ground_truth.py -k "c012" -v` — 1 passed.

- [ ] T007 [US2] Run C-012 green (already implemented in T005 — SID map is in ground_truth.py): `cd src && pytest ../tests/test_ground_truth.py::test_c012_sid_categories_covers_all_phase1 -v` — confirm 1 passed

**Checkpoint**: US2 complete — all 8 Phase 1 categories covered by SURICATA_SID_CATEGORIES.

---

## Phase 5: User Story 3 — Gate Assessment (Priority: P3)

**Goal**: `meets_gate` property returns correct bool for precision vs 0.8; covers C-004..C-006.

**Independent Test**: `cd src && pytest ../tests/test_ground_truth.py -k "c004 or c005 or c006" -v` — 3 passed.

- [ ] T008 [US3] Run C-004..C-006 green (already in ground_truth.py — meets_gate property hardcoded at 0.8): `cd src && pytest ../tests/test_ground_truth.py -k "c004 or c005 or c006" -v` — confirm 3 passed

**Checkpoint**: US3 complete — meets_gate boundary logic verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Lint, full suite run, commit, merge to main.

- [ ] T009 Run ruff on new files: `cd src && ruff check ../tests/test_ground_truth.py aatf/ground_truth.py --fix` — confirm 0 errors
- [ ] T010 Run full test suite: `cd src && pytest --tb=short -q 2>&1 | tail -5` — confirm ≥298 passed, 4 skipped, 6 failed (net +12 from baseline 286)
- [ ] T011 Stage and commit all new files to branch `024-e6-ground-truth-validation`:
  ```bash
  git add src/aatf/ground_truth.py tests/test_ground_truth.py specs/024-e6-ground-truth-validation/tasks.md
  git commit -m "feat(F22): add aatf.ground_truth — ValidationResult + validate_blind_spots (12 contracts green)"
  ```
- [ ] T012 Merge to main:
  ```bash
  git checkout main && git merge --no-ff 024-e6-ground-truth-validation -m "merge: F22 ground-truth validation (E6 complete)"
  ```
- [ ] T013 Verify suite on main: `cd src && pytest --tb=no -q 2>&1 | tail -3` — confirm ≥298 passed

**Checkpoint**: F22 complete. E6 (F20, F21, F23, F24, F22) all merged to main.

---

## Dependencies

```
T001 → T002 → T003 → T004   (setup + red phase, sequential)
T004 → T005 → T006           (US1: implement then verify)
T005 → T007                  (US2: verifying SID map already in T005)
T005 → T008                  (US3: verifying meets_gate already in T005)
T006 + T007 + T008 → T009 → T010 → T011 → T012 → T013
```

US2 and US3 checkpoints (T007, T008) can run in parallel after T006.

---

## Implementation Strategy

| Phase | Scope | Tests | Value |
|---|---|---|---|
| MVP | T001–T006 | C-001..C-003, C-007..C-011 | Core validate_blind_spots works |
| +US2 | T007 | C-012 | SID map coverage verified |
| +US3 | T008 | C-004..C-006 | Gate property verified |
| Full | T009–T013 | All 12 green | E6 merged to main |

---

## Summary

| Metric | Value |
|---|---|
| Total tasks | 13 (T001–T013) |
| US1 tasks | T005–T006 (2 tasks, 8 contracts) |
| US2 tasks | T007 (1 task, 1 contract) |
| US3 tasks | T008 (1 task, 3 contracts) |
| Setup/foundational | T001–T004 (4 tasks) |
| Polish | T009–T013 (5 tasks) |
| Parallelizable | T007 ∥ T008 (after T006) |
| Baseline | 286 passed |
| Target | ≥298 passed (+12) |
| New files | 2 (ground_truth.py, test_ground_truth.py) |
| Modified files | 0 |
| New pip deps | 0 |
