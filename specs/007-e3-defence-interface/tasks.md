# Tasks: Pluggable Defence Interface (F10)

**Input**: Design documents from `specs/007-e3-defence-interface/`
**Branch**: `007-e3-defence-interface`
**TDD**: Tests written first, must FAIL before implementation

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1/US2/US3 maps to user stories in spec.md
- Tests are written FIRST and must FAIL before implementation tasks

---

## Phase 1: Setup

**Purpose**: Establish baseline before any changes.

- [X] T001 Record `make test` baseline count in a comment in tasks.md — run `cd src && pytest --tb=no -q 2>&1 | tail -1` and note the number of passing tests
  <!-- BASELINE: 78 passed, 1 skipped -->

**Checkpoint**: Baseline recorded. All subsequent phases must not regress this count.

---

## Phase 2: Foundational — DetectionResult Validator

**Purpose**: Tighten `DetectionResult` to enforce `rule_ids == []` when `alerted = False`.
This is a prerequisite for all user stories — the interface contract depends on it.

**⚠️ CRITICAL**: Must complete before Phase 3.

- [X] T002 Add `@model_validator(mode='after')` to `DetectionResult` in `src/aatf/contracts.py` — import `model_validator` from pydantic; add method `_rule_ids_require_alert` that raises `ValueError("rule_ids must be empty when alerted is False")` if `self.rule_ids and not self.alerted`

- [X] T003 [P] Write test for C-004 in `tests/test_contracts.py` — add `test_detection_result_rule_ids_require_alert`: assert `pytest.raises(ValidationError)` when constructing `DetectionResult(alerted=False, rule_ids=["2001219"], anomaly_score=0.0, coverage="covered")`; also assert valid case `DetectionResult(alerted=True, rule_ids=["2001219"], anomaly_score=0.5, coverage="covered")` succeeds

- [X] T004 Run `cd src && pytest tests/test_contracts.py -v` — verify the new C-004 test passes and all prior contract tests still pass

**Checkpoint**: `DetectionResult` validator active. `make test` baseline + 1 new test.

---

## Phase 3: User Story 1 — Define and Invoke Defence Uniformly (Priority: P1) 🎯 MVP

**Goal**: `Defence` ABC, `DefenceError`, and `NullDefence` exist and satisfy C-001/002/003/006/007/008.

**Independent Test**: `from aatf.defence import NullDefence; NullDefence().observe(action)` returns a valid `DetectionResult` with no imports of concrete detectors.

### Tests for US1 (write first — must FAIL before T006)

- [X] T005 [US1] Write 6 failing tests in `tests/test_defence.py` — create the file with these tests (all will fail with `ModuleNotFoundError` until T006):
  - `test_null_defence_returns_detection_result` (C-001): call `NullDefence().observe(action)`, assert `isinstance(result, DetectionResult)`
  - `test_null_defence_not_detected` (C-002): assert `result.alerted is False`, `result.rule_ids == []`, `result.anomaly_score == 0.0`, `result.coverage == "unknown"`
  - `test_failing_defence_raises_defence_error` (C-003): define inline `FailingDefence(Defence)` that raises `DefenceError("test")` in `observe()`; assert `pytest.raises(DefenceError)`
  - `test_detection_result_is_immutable` (C-006): assert `pytest.raises((ValidationError, TypeError))` when assigning `result.alerted = True` after construction
  - `test_defence_cannot_be_instantiated` (C-007): assert `pytest.raises(TypeError)` when calling `Defence()`
  - `test_unimplemented_observe_raises_type_error` (C-008): define `class EmptyDefence(Defence): pass`; assert `pytest.raises(TypeError)` when calling `EmptyDefence()`
  - Include a module-level fixture `action` returning a valid `Action` with `action_id="t-001"`, `category="scan"`, `parameters={"port": 22}`, `timestamp=datetime.now(timezone.utc)`

### Implementation for US1

- [X] T006 [US1] Create `src/aatf/defence.py` with three components:
  1. `class DefenceError(Exception)` — `__init__(self, message: str, cause: Exception | None = None)`: calls `super().__init__(message)`, stores `self.cause = cause`
  2. `class Defence(ABC)` — imports `from abc import ABC, abstractmethod`; single `@abstractmethod` method `observe(self, action: Action) -> DetectionResult: ...`
  3. `class NullDefence(Defence)` — implements `observe` returning `DetectionResult(alerted=False, rule_ids=[], anomaly_score=0.0, coverage="unknown")`
  File header: `from __future__ import annotations` and imports from `abc`, `aatf.contracts`

- [X] T007 [US1] Add exports to `src/aatf/__init__.py` (re-export removed — live-layer boundary guard requires direct import from aatf.defence) — import and expose `Defence`, `DefenceError`, `NullDefence` from `aatf.defence`

- [X] T008 [US1] Run `cd src && pytest tests/test_defence.py -v` — verify all 6 US1 tests pass; then run full `pytest` to confirm no regressions

**Checkpoint**: US1 complete. `Defence`, `DefenceError`, `NullDefence` defined and tested.

---

## Phase 4: User Story 2 — Swap Detectors Without Touching Consumers (Priority: P2)

**Goal**: Prove pluggability via AST import check (C-005), repeated-call safety (C-009), and multi-category acceptance (C-010).

**Independent Test**: Two distinct stubs both satisfy the interface; consumer function works with either; `defence.py` has zero concrete-detector imports.

### Tests for US2 (write first — C-005/009/010)

- [X] T009 [US2] Add 3 tests to `tests/test_defence.py`:
  - `test_defence_module_has_no_concrete_imports` (C-005): use `import ast, pathlib`; parse `src/aatf/defence.py` AST; collect all imported names from `Import` and `ImportFrom` nodes; assert none of `["suricata", "eve", "auditd", "sklearn", "torch", "tensorflow"]` appear in any imported module name (case-insensitive)
  - `test_null_defence_repeated_calls_equal` (C-009): call `NullDefence().observe(action)` three times; assert all three results are equal
  - `test_null_defence_accepts_any_action_category` (C-010): call `NullDefence().observe()` with Actions of categories `"scan"`, `"exfil"`, `"brute"`; assert each returns a valid `DetectionResult`

### Implementation for US2

- [X] T010 [US2] Run `cd src && pytest tests/test_defence.py::test_defence_module_has_no_concrete_imports tests/test_defence.py::test_null_defence_repeated_calls_equal tests/test_defence.py::test_null_defence_accepts_any_action_category -v` — all 3 must pass (C-009/010 pass from existing NullDefence; C-005 passes if defence.py is clean); fix any issues

**Checkpoint**: US2 complete. Pluggability and AST cleanliness verified.

---

## Phase 5: User Story 3 — Stub the Detector in Unit Tests (Priority: P3)

**Goal**: `check_defence_contract()` helper shipped with interface tests; any future Defence test can call it to verify conformance (C-011).

**Independent Test**: Import `check_defence_contract` from `tests.test_defence` in an external test; call it with `NullDefence()` — passes silently.

### Tests for US3 (write first — C-011)

- [X] T011 [US3] Add test `test_check_defence_contract_helper_passes_for_null` (C-011) to `tests/test_defence.py` — the test body calls `check_defence_contract(NullDefence(), action)` and asserts it returns `None` (no assertions raised); this test will fail until T012 adds the helper function

### Implementation for US3

- [X] T012 [US3] Add `check_defence_contract(defence: Defence, action: Action) -> None` function to `tests/test_defence.py` — body:
  ```python
  result = defence.observe(action)
  assert isinstance(result, DetectionResult)
  assert isinstance(result.alerted, bool)
  assert isinstance(result.rule_ids, list)
  assert 0.0 <= result.anomaly_score <= 1.0
  assert result.coverage in ("covered", "uncovered", "unknown")
  if not result.alerted:
      assert result.rule_ids == []
  ```
  Place the function BEFORE the test classes so it is importable as a module-level callable.

- [X] T013 [US3] Run `cd src && pytest tests/test_defence.py -v` — verify all 11 contract tests pass (6 from US1 + 3 from US2 + 1 from US3 + 1 C-004 in test_contracts.py)

**Checkpoint**: All 3 user stories complete. All 11 contracts pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T014 Run `cd src && ruff check . && ruff format --check .` — fix any linting or formatting violations in `defence.py`, `contracts.py`, `__init__.py`, `test_defence.py`, `test_contracts.py`

- [X] T015 Run final `cd src && pytest --tb=short -q` — confirm test count increased by ≥12 vs baseline (1 C-004 contract + 11 defence tests); confirm 0 failures, 0 errors

- [ ] T016 Commit all changes — staged files: `src/aatf/defence.py`, `src/aatf/contracts.py`, `src/aatf/__init__.py`, `tests/test_defence.py`, `tests/test_contracts.py`, `specs/007-e3-defence-interface/tasks.md`; message: `feat(F10): pluggable Defence interface — ABC, DefenceError, NullDefence, 11 contract tests`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1)**: Depends on Phase 2 — write tests first (T005), then implement (T006→T007→T008)
- **Phase 4 (US2)**: Depends on Phase 3 completion — NullDefence must exist for C-009/010 tests
- **Phase 5 (US3)**: Depends on Phase 4 completion — conformance helper tests NullDefence
- **Phase 6 (Polish)**: Depends on all phases complete

### User Story Dependencies

- **US1 (P1)**: Foundational complete → write T005 tests → T006 defence.py → T007 exports → T008 verify
- **US2 (P2)**: US1 complete → write T009 tests → T010 verify
- **US3 (P3)**: US2 complete → write T011 test → T012 helper → T013 verify

### Parallel Opportunities

- T003 (C-004 test) can be written in parallel with T002 (validator implementation) — different files
- Within US1: T005 tests can be written while reviewing T006 implementation sketch
- T009 (US2 tests) written immediately after T008 passes — no additional implementation needed

---

## Parallel Example: Phase 2

```
T002: Edit src/aatf/contracts.py    ─┐
T003: Edit tests/test_contracts.py  ─┴─► T004: run make test
```

---

## Implementation Strategy

### MVP (Phase 1 + 2 + 3 only)

1. Record baseline (T001)
2. Tighten DetectionResult (T002–T004)
3. Write 6 failing tests (T005)
4. Create defence.py (T006–T007)
5. **STOP**: run `make test` → if 6 new tests pass, US1 is done
6. Continue to US2/US3 for full compliance

### Incremental Delivery

- After T008: US1 done — `Defence`, `DefenceError`, `NullDefence` usable by F11/F12
- After T010: US2 done — pluggability guaranteed by AST check
- After T013: US3 done — conformance helper available for all future adapter tests
- After T016: committed and ready for `/sp.implement` on F11

---

## Notes

- TDD is mandatory — verify tests FAIL before each implementation task
- defence.py must never import anything outside of `abc` stdlib and `aatf.contracts`
- `check_defence_contract()` is placed at module level in test_defence.py so F11/F12 tests can import it
- The C-004 validator change to contracts.py is additive — existing passing test_contracts.py tests must all still pass
- `NullDefence` returns `coverage="unknown"` deliberately — it has no knowledge of rules, so "unknown" is the correct neutral state
