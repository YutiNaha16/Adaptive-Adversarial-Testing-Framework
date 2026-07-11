# Tasks: Automated Phase 1 Gate Evaluation (F26)

**Input**: Design documents from `/specs/026-e7-phase1-gate/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, quickstart.md ✅, checklists/requirements.md ✅

**TDD approach**: Write all 10 tests first (red = ImportError/ModuleNotFoundError), then implement.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Record baseline and verify prerequisites.

- [ ] T001 Record test baseline: `pytest --tb=no -q 2>&1 | tail -3` — confirm 312 passed, 4 skipped

**Checkpoint**: Baseline confirmed.

---

## Phase 2: Foundational (Red Phase)

**Purpose**: Write all 10 contract tests — must fail before implementation.

**⚠️ CRITICAL**: All 10 tests must be written and confirmed RED before any implementation begins.

- [ ] T002 Create `tests/test_gate.py` with helpers and all 10 contract tests:

  **File header, imports, and helpers**:
  ```python
  """Tests for aatf.gate — 10 contracts C-001..C-010."""
  from __future__ import annotations

  import sys
  from dataclasses import fields
  from pathlib import Path

  import pytest

  from aatf.gate import CriterionResult, GateResult, phase1_gate
  from aatf.ground_truth import ValidationResult
  from aatf.metrics import EpisodeRecord

  sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
  import run_experiment


  def _make_vr(bsp: float = 0.9) -> ValidationResult:
      return ValidationResult(
          blind_spot_precision=bsp,
          true_positives=9,
          false_positives=1,
          total_reported=10,
          disabled_sid_count=5,
      )


  def _make_records(n: int = 3) -> list[EpisodeRecord]:
      return [
          EpisodeRecord(
              attacker_class="RandomAttacker",
              seed=42,
              steps=[],
              total_reward=0.0,
              completed=True,
              episode_index=i,
          )
          for i in range(n)
      ]


  def _write_config(tmp_path: Path, episodes: int = 2) -> Path:
      tmp_path.mkdir(parents=True, exist_ok=True)
      cfg = tmp_path / "config.yaml"
      out = tmp_path / "out"
      cfg.write_text(
          f"episodes: {episodes}\n"
          f"seed: 42\n"
          f"output_dir: {out}\n"
          f"ruleset_path: /tmp/rules\n"
          f"detection_threshold: 0.5\n"
          f"attacker_class: RandomAttacker\n"
      )
      return cfg
  ```

  **C-001 — importability**:
  ```python
  def test_c001_importability():
      from aatf.gate import CriterionResult, GateResult, phase1_gate  # noqa: F401
      assert callable(phase1_gate)
  ```

  **C-002 — GateResult is frozen**:
  ```python
  def test_c002_gate_result_frozen():
      from dataclasses import FrozenInstanceError
      gr = GateResult(passed=True, criteria=(), summary="Phase 1 PASSED (0/0 criteria met)")
      with pytest.raises(FrozenInstanceError):
          gr.passed = False
  ```

  **C-003 — CriterionResult is frozen**:
  ```python
  def test_c003_criterion_result_frozen():
      from dataclasses import FrozenInstanceError
      cr = CriterionResult(name="test", passed=True, value=1.0, threshold=0.0)
      with pytest.raises(FrozenInstanceError):
          cr.passed = False
  ```

  **C-004 — all-pass scenario**:
  ```python
  def test_c004_all_pass(self=None):
      result = phase1_gate(_make_records(3), _make_vr(0.9))
      assert result.passed is True
      assert all(c.passed for c in result.criteria)
      assert len(result.criteria) == 3
  ```

  **C-005 — BSP below threshold**:
  ```python
  def test_c005_bsp_fails():
      result = phase1_gate(_make_records(3), _make_vr(0.5))
      assert result.passed is False
      bsp_criterion = next(c for c in result.criteria if c.name == "blind_spot_precision")
      assert bsp_criterion.passed is False
      assert bsp_criterion.value == pytest.approx(0.5)
  ```

  **C-006 — empty records fails gate**:
  ```python
  def test_c006_empty_records_fails():
      result = phase1_gate([], _make_vr(0.9))
      assert result.passed is False
  ```

  **C-007 — single episode passes DR and RS**:
  ```python
  def test_c007_single_episode_passes_dr_rs():
      result = phase1_gate(_make_records(1), _make_vr(0.9))
      dr_criterion = next(c for c in result.criteria if c.name == "detection_rate")
      rs_criterion = next(c for c in result.criteria if c.name == "robustness_score")
      assert dr_criterion.passed is True
      assert rs_criterion.passed is True
  ```

  **C-008 — summary contains PASSED or FAILED**:
  ```python
  def test_c008_summary_keywords():
      passed_result = phase1_gate(_make_records(3), _make_vr(0.9))
      assert "PASSED" in passed_result.summary

      failed_result = phase1_gate([], _make_vr(0.9))
      assert "FAILED" in failed_result.summary
  ```

  **C-009 — run_experiment stdout contains Phase 1**:
  ```python
  def test_c009_run_experiment_stdout_contains_gate(tmp_path, capsys):
      cfg = _write_config(tmp_path)
      run_experiment.main(config_path=cfg)
      out = capsys.readouterr().out
      assert "Phase 1" in out
  ```

  **C-010 — gate is deterministic**:
  ```python
  def test_c010_determinism():
      records = _make_records(5)
      vr = _make_vr(0.9)
      result1 = phase1_gate(records, vr)
      result2 = phase1_gate(records, vr)
      assert result1 == result2
  ```

- [ ] T003 Confirm RED state: `pytest tests/test_gate.py -v 2>&1 | tail -15` — expect ImportError for `aatf.gate`; confirm 0 passed, 10 errors

**Checkpoint**: 10 tests written, all failing. Ready to implement.

---

## Phase 3: User Story 1 — Gate Evaluation Function (Priority: P1)

**Goal**: `phase1_gate(records, validation_result) -> GateResult` evaluates 3 criteria and returns structured pass/fail; covers C-001..C-008, C-010.

**Independent Test**: `pytest tests/test_gate.py -k "c001 or c002 or c003 or c004 or c005 or c006 or c007 or c008 or c010" -v` — 9 passed.

- [ ] T004 [US1] Modify `src/aatf/manifest.py` — add `extra_metadata: dict | None = None` kwarg to `write_manifest()` and merge before writing:
  ```python
  def write_manifest(
      config: ExperimentConfig,
      seed: int,
      *,
      suricata_version: str = "unknown",
      ruleset_version: str = "unknown",
      extra_metadata: dict | None = None,
  ) -> Path:
      # ... existing body ...
      manifest = { ... existing keys ... }
      if extra_metadata:
          manifest.update(extra_metadata)
      # ... write to file ...
  ```

- [ ] T005 [US1] Create `src/aatf/gate.py` (~50 LOC) with exact content:

  ```python
  """Phase 1 gate evaluator — pure function, no I/O."""
  from __future__ import annotations

  from dataclasses import dataclass

  from aatf.ground_truth import ValidationResult
  from aatf.metrics import EpisodeRecord, detection_rate, robustness_score


  @dataclass(frozen=True)
  class CriterionResult:
      name: str
      passed: bool
      value: float
      threshold: float


  @dataclass(frozen=True)
  class GateResult:
      passed: bool
      criteria: tuple[CriterionResult, ...]
      summary: str


  def phase1_gate(
      records: list[EpisodeRecord],
      validation_result: ValidationResult,
  ) -> GateResult:
      n = len(records)
      dr_value = detection_rate(records)
      rs_value = robustness_score(records, window=min(10, n)) if n > 0 else 0.0

      criteria = (
          CriterionResult(
              name="detection_rate",
              threshold=0.0,
              value=dr_value,
              passed=n > 0,
          ),
          CriterionResult(
              name="blind_spot_precision",
              threshold=0.8,
              value=validation_result.blind_spot_precision,
              passed=validation_result.blind_spot_precision >= 0.8,
          ),
          CriterionResult(
              name="robustness_score",
              threshold=0.0,
              value=rs_value,
              passed=n > 0,
          ),
      )

      passed = all(c.passed for c in criteria)
      met = sum(c.passed for c in criteria)
      total = len(criteria)

      if passed:
          summary = f"Phase 1 PASSED ({met}/{total} criteria met)"
      else:
          failing = ", ".join(c.name for c in criteria if not c.passed)
          summary = f"Phase 1 FAILED ({met}/{total} criteria met: {failing} below threshold)"

      return GateResult(passed=passed, criteria=criteria, summary=summary)
  ```

- [ ] T006 [US1] Verify US1 contracts green: `pytest tests/test_gate.py -k "c001 or c002 or c003 or c004 or c005 or c006 or c007 or c008 or c010" -v 2>&1 | tail -15` — confirm 9 passed, 0 failed

**Checkpoint**: US1 complete — gate function works, all boundary cases handled.

---

## Phase 4: User Story 2 — Gate Result in Experiment Output (Priority: P2)

**Goal**: `run_experiment.main()` calls gate, prints gate block to stdout, includes in manifest; covers C-009.

**Independent Test**: `pytest tests/test_gate.py::test_c009_run_experiment_stdout_contains_gate -v` — 1 passed.

- [ ] T007 [US2] Modify `src/run_experiment.py` — add gate integration:

  **Add to imports (after existing imports)**:
  ```python
  from aatf.gate import phase1_gate
  from aatf.ground_truth import ValidationResult
  ```

  **After records loop, before computing dr/rs** (insert after `records = []` and the episode loop):
  ```python
  validation_result = ValidationResult(
      blind_spot_precision=0.0,
      true_positives=0,
      false_positives=0,
      total_reported=0,
      disabled_sid_count=0,
  )
  gate_result = phase1_gate(records, validation_result)
  ```

  **Replace the existing `manifest_path = write_manifest(config, config.seed)` call** with:
  ```python
  manifest_path = write_manifest(
      config,
      config.seed,
      extra_metadata={
          "phase1_gate": {
              "passed": gate_result.passed,
              "summary": gate_result.summary,
              "criteria": [
                  {
                      "name": c.name,
                      "passed": c.passed,
                      "value": c.value,
                      "threshold": c.threshold,
                  }
                  for c in gate_result.criteria
              ],
          }
      },
  )
  ```

  **After `print(f"Manifest written   : {manifest_path}")` line**, add gate block print:
  ```python
  print("-" * 38)
  for c in gate_result.criteria:
      status = "PASS" if c.passed else "FAIL"
      print(f"  {c.name:<22}: {c.value:.4f} (≥{c.threshold:.4f}) [{status}]")
  print(gate_result.summary)
  ```

- [ ] T008 [US2] Verify C-009 green: `pytest tests/test_gate.py::test_c009_run_experiment_stdout_contains_gate -v 2>&1 | tail -10` — confirm 1 passed

**Checkpoint**: US2 complete — gate result visible in stdout and manifest.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Lint, full suite, commit, merge to main, push.

- [ ] T009 Run ruff on new/modified files: `ruff check src/aatf/gate.py tests/test_gate.py src/run_experiment.py src/aatf/manifest.py --fix` — confirm 0 errors
- [ ] T010 Run full suite: `pytest --tb=short -q 2>&1 | tail -5` — confirm ≥322 passed, 4 skipped
- [ ] T011 Stage and commit: `git add src/aatf/gate.py tests/test_gate.py src/aatf/manifest.py src/run_experiment.py && git commit -m "feat(F26): Phase 1 gate evaluation — phase1_gate() + stdout + manifest (10 contracts green)"`
- [ ] T012 Merge to main: `git checkout main && git merge --no-ff 026-e7-phase1-gate -m "merge: F26 Phase 1 gate evaluation"`
- [ ] T013 Verify suite on main: `pytest --tb=no -q 2>&1 | tail -3` — confirm ≥322 passed
- [ ] T014 Push: `git push origin main`

**Checkpoint**: F26 complete and pushed. E7 complete.

---

## Dependencies

```
T001                                    (setup, baseline)
T001 → T002 → T003                     (red phase)
T003 → T004 → T005 → T006             (US1: manifest first, then gate, verify)
T006 → T007 → T008                     (US2: integration)
T008 → T009 → T010 → T011 → T012 → T013 → T014
```

T004 (manifest.py) and T005 (gate.py) touch different files — parallelizable if desired, but T004 must exist before T005 can be tested end-to-end (manifest called from run_experiment).

---

## Implementation Strategy

| Phase | Scope | Tests | Value |
|---|---|---|---|
| MVP | T001–T006 | C-001..C-008, C-010 | Gate function fully working |
| +US2 | T007–T008 | C-009 | Gate visible in experiment output |
| Full | T009–T014 | All 10 green | F26 merged + pushed |

---

## Summary

| Metric | Value |
|---|---|
| Total tasks | 14 (T001–T014) |
| US1 tasks | T004–T006 (3 tasks, 9 contracts) |
| US2 tasks | T007–T008 (2 tasks, 1 contract) |
| Setup/foundational | T001–T003 (3 tasks) |
| Polish | T009–T014 (6 tasks) |
| Baseline | 312 passed |
| Target | ≥322 passed (+10) |
| New files | 2 (gate.py, test_gate.py) |
| Modified files | 2 (manifest.py, run_experiment.py) |
| New pip deps | 0 |
