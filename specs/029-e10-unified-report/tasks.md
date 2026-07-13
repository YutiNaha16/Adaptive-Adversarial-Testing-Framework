# Tasks: Unified Blind-Spot Report (F29)

**Input**: Design documents from `/specs/029-e10-unified-report/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**TDD**: Write all 5 test contracts first (red), then implement (green).
**Baseline**: 345 passed. **Target**: ≥350 passed (+5).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Confirm baseline before any changes.

- [X] T001 Record baseline — run `cd /home/yuti/Adaptive-Adversarial-Testing-Framework && source .venv/bin/activate && pytest` and confirm exactly 345 passed, 1 skipped, 0 failed before any changes

---

## Phase 2: Foundational Red (TDD — Write Tests Before Implementation)

**Purpose**: Create all 5 failing test contracts before touching source files.

**⚠️ CRITICAL**: T002 must be complete and red before any implementation begins.

- [X] T002 Create `tests/test_unified_report.py` with verbatim content below — 5 contracts C-001..C-005

  **Full file content** (write exactly as shown):

  ```python
  """Test contracts C-001..C-005: F29 unified ML blind-spot report."""
  from __future__ import annotations

  from pathlib import Path

  import pytest

  from aatf.action_library import REGISTRY
  from aatf.episode import EpisodeRecord, StepRecord
  from aatf.report import generate_report


  def _ep(steps: list[StepRecord], attacker_class: str = "DQNAttacker", seed: int = 42) -> EpisodeRecord:
      return EpisodeRecord(
          attacker_class=attacker_class,
          seed=seed,
          total_reward=sum(s.reward for s in steps),
          steps=steps,
      )


  # --- C-001 -------------------------------------------------------------------


  def test_c001_no_ml_section_when_all_anomaly_scores_zero(tmp_path: Path) -> None:
      step = StepRecord(action_id="tcp_port_scan", detected=False, stage_progress=0, reward=1.0)
      rendered = generate_report([_ep([step])], REGISTRY, tmp_path / "report.md")
      assert "ML Anomaly Defence Analysis" not in rendered


  # --- C-002 -------------------------------------------------------------------


  def test_c002_ml_section_appears_and_shows_cae(tmp_path: Path) -> None:
      step = StepRecord(
          action_id="tcp_port_scan", detected=False, stage_progress=0, reward=1.0, anomaly_score=0.5
      )
      rendered = generate_report([_ep([step])], REGISTRY, tmp_path / "report.md")
      assert "ML Anomaly Defence Analysis" in rendered
      # CAE = mean-of-episode-sums = 0.5 / 1 episode = 0.5000
      assert "0.5000" in rendered


  # --- C-003 -------------------------------------------------------------------


  def test_c003_evasive_table_ranks_ascending_by_undetected_anomaly(tmp_path: Path) -> None:
      # tcp_port_scan undetected anomaly 0.1 < udp_sweep undetected anomaly 0.4
      # → tcp_port_scan must appear first in the "Most Evasive Actions" table
      steps = [
          StepRecord(action_id="tcp_port_scan", detected=False, stage_progress=0, reward=1.0,
                     anomaly_score=0.1),
          StepRecord(action_id="udp_sweep", detected=False, stage_progress=0, reward=1.0,
                     anomaly_score=0.4),
      ]
      rendered = generate_report([_ep(steps)], REGISTRY, tmp_path / "report.md")
      assert "Most Evasive Actions" in rendered
      evasive_section = rendered.split("Most Evasive Actions")[1].split("Most Suspicious Actions")[0]
      assert evasive_section.index("tcp_port_scan") < evasive_section.index("udp_sweep")


  # --- C-004 -------------------------------------------------------------------


  def test_c004_suspicious_table_ranks_descending_by_overall_anomaly(tmp_path: Path) -> None:
      # tcp_port_scan overall anomaly 0.9 > udp_sweep overall anomaly 0.2
      # → tcp_port_scan must appear first in the "Most Suspicious Actions" table
      # Both detected=True so evasive table is empty; only suspicious table shows them.
      steps = [
          StepRecord(action_id="tcp_port_scan", detected=True, stage_progress=0, reward=-1.0,
                     anomaly_score=0.9),
          StepRecord(action_id="udp_sweep", detected=True, stage_progress=0, reward=-1.0,
                     anomaly_score=0.2),
      ]
      rendered = generate_report([_ep(steps)], REGISTRY, tmp_path / "report.md")
      assert "Most Suspicious Actions" in rendered
      suspicious_section = rendered.split("Most Suspicious Actions")[1].split("Retraining Recommendation")[0]
      assert suspicious_section.index("tcp_port_scan") < suspicious_section.index("udp_sweep")


  # --- C-005 -------------------------------------------------------------------


  def test_c005_retrain_categories_and_no_gap_message(tmp_path: Path) -> None:
      # Below threshold (0.25 < 0.3): tcp_port_scan's category "ET SCAN" must appear
      # in the Retraining Recommendation section.
      step_low = StepRecord(
          action_id="tcp_port_scan", detected=False, stage_progress=0, reward=1.0, anomaly_score=0.25
      )
      rendered_low = generate_report([_ep([step_low])], REGISTRY, tmp_path / "low.md")
      recommendation_section = rendered_low.split("Retraining Recommendation")[1]
      assert "ET SCAN" in recommendation_section

      # Above threshold (0.7 > 0.3): retrain_categories is empty → no-gap message shown.
      step_high = StepRecord(
          action_id="tcp_port_scan", detected=False, stage_progress=0, reward=1.0, anomaly_score=0.7
      )
      rendered_high = generate_report([_ep([step_high])], REGISTRY, tmp_path / "high.md")
      assert "No ML gap identified" in rendered_high
  ```

- [X] T003 Confirm red — run `pytest tests/test_unified_report.py -v` and verify all 5 contracts fail (ImportError on MLActionStats or test failures); record failure mode

---

## Phase 3: User Story 1 — ML Section Auto-Appears (Priority: P1)

**Goal**: ML section appears iff any anomaly_score > 0; absent otherwise.
**Independent Test**: C-001 (section absent) and C-002 (section present + CAE value) both green.

### Implementation for User Story 1

- [X] T004 [US1] Extend imports in `src/aatf/report.py`:
  - Add `import dataclasses` at the top (stdlib imports block)
  - Change existing metrics import from:
    `from aatf.metrics import EpisodeRecord, detection_rate, robustness_score`
    to:
    `from aatf.metrics import EpisodeRecord, cumulative_anomaly_exposure, detection_rate, robustness_score`

- [X] T005 [US1] Add module-level constant and dataclasses to `src/aatf/report.py` immediately after the imports block (before `_TEMPLATE_DIR`):

  ```python
  EVASION_THRESHOLD: float = 0.3


  @dataclasses.dataclass(frozen=True)
  class MLActionStats:
      action_id: str
      category: str
      mean_anomaly_all: float
      mean_anomaly_undetected: float
      total_steps: int
      undetected_steps: int


  @dataclasses.dataclass(frozen=True)
  class MLAnalysisSummary:
      cae: float
      episode_count: int
      evasive: list[MLActionStats]
      suspicious: list[MLActionStats]
      retrain_categories: list[str]
  ```

- [X] T006 [US1] Add private helpers to `src/aatf/report.py` immediately after `_TEMPLATE_DIR`:

  ```python
  def _has_ml_scores(records: list[EpisodeRecord]) -> bool:
      return any(s.anomaly_score > 0 for r in records for s in r.steps)


  def _compute_ml_summary(records: list[EpisodeRecord], registry: ActionRegistry) -> MLAnalysisSummary:
      from collections import defaultdict

      all_scores: dict[str, list[float]] = defaultdict(list)
      undetected_scores: dict[str, list[float]] = defaultdict(list)

      for r in records:
          for s in r.steps:
              all_scores[s.action_id].append(s.anomaly_score)
              if not s.detected:
                  undetected_scores[s.action_id].append(s.anomaly_score)

      stats: list[MLActionStats] = []
      for action_id, scores in all_scores.items():
          try:
              category = registry.get_action(action_id).suricata_category
          except KeyError:
              category = "UNKNOWN"
          u_scores = undetected_scores.get(action_id, [])
          stats.append(
              MLActionStats(
                  action_id=action_id,
                  category=category,
                  mean_anomaly_all=sum(scores) / len(scores),
                  mean_anomaly_undetected=sum(u_scores) / len(u_scores) if u_scores else 0.0,
                  total_steps=len(scores),
                  undetected_steps=len(u_scores),
              )
          )

      evasive = sorted(
          (a for a in stats if a.undetected_steps > 0),
          key=lambda a: a.mean_anomaly_undetected,
      )[:5]

      suspicious = sorted(stats, key=lambda a: a.mean_anomaly_all, reverse=True)[:5]

      retrain_categories = sorted(
          {
              a.category
              for a in stats
              if a.undetected_steps > 0 and a.mean_anomaly_undetected < EVASION_THRESHOLD
          }
      )

      return MLAnalysisSummary(
          cae=cumulative_anomaly_exposure(records),
          episode_count=len(records),
          evasive=evasive,
          suspicious=suspicious,
          retrain_categories=retrain_categories,
      )
  ```

- [X] T007 [US1] Inject `ml_summary` into ctx dict in `generate_report()` in `src/aatf/report.py` — add this line immediately after the `ctx = {...}` block closes and before `env = Environment(...)`:

  ```python
      ctx["ml_summary"] = _compute_ml_summary(records, registry) if _has_ml_scores(records) else None
  ```

- [X] T008 [US1] Insert ML section into `src/aatf/templates/report.md.j2` — between the closing `{% endif %}` of the Blind Spots block and the `---` footer line.

  The current template ends with:
  ```
  {% endif %}

  ---
  *Generated from logged episode records. No live defence systems were accessed.*
  ```

  Replace it with:
  ```
  {% endif %}

  {% if ml_summary %}
  ---

  ## ML Anomaly Defence Analysis

  > Based on {{ ml_summary.episode_count }} episodes. CAE = {{ "%.4f" | format(ml_summary.cae) }}
  > (lower = stealthier attacker).

  ### Most Evasive Actions (lowest mean anomaly score while undetected)

  {% if ml_summary.evasive %}
  | Action | Category | Mean Anomaly (undetected) | Undetected Steps |
  |--------|----------|--------------------------|-----------------|
  {% for s in ml_summary.evasive %}
  | {{ s.action_id }} | {{ s.category }} | {{ "%.3f" | format(s.mean_anomaly_undetected) }} | {{ s.undetected_steps }} |
  {% endfor %}
  {% else %}
  _No undetected actions — ML detector caught all steps._
  {% endif %}

  ### Most Suspicious Actions (highest mean anomaly score)

  {% if ml_summary.suspicious %}
  | Action | Category | Mean Anomaly (all steps) | Total Steps |
  |--------|----------|--------------------------|-------------|
  {% for s in ml_summary.suspicious %}
  | {{ s.action_id }} | {{ s.category }} | {{ "%.3f" | format(s.mean_anomaly_all) }} | {{ s.total_steps }} |
  {% endfor %}
  {% else %}
  _No actions recorded._
  {% endif %}

  ### Retraining Recommendation

  {% if ml_summary.retrain_categories %}
  The following action categories evaded the ML detector (mean anomaly score < 0.30 on undetected
  steps). Add representative normal-vs-attack traffic for these categories to the next training batch:

  {% for cat in ml_summary.retrain_categories %}
  - **{{ cat }}**
  {% endfor %}
  {% else %}
  No ML gap identified in this evaluation. The ML detector scored all evaded actions above the 0.30
  threshold. Re-evaluate after a longer training run or with the DQN attacker active.
  {% endif %}
  {% endif %}

  ---
  *Generated from logged episode records. No live defence systems were accessed.*
  ```

- [X] T009 [US1] Verify C-001 and C-002 green — run `pytest tests/test_unified_report.py::test_c001_no_ml_section_when_all_anomaly_scores_zero tests/test_unified_report.py::test_c002_ml_section_appears_and_shows_cae -v`

**Checkpoint**: ML section auto-appears correctly — C-001 and C-002 both PASS.

---

## Phase 4: User Story 2 — Evasion and Suspicion Tables (Priority: P2)

**Goal**: Evasive table ranks ascending by undetected anomaly; suspicious table ranks descending by overall anomaly.
**Independent Test**: C-003 and C-004 both green (already handled by _compute_ml_summary from T006).

- [X] T010 [US2] Verify C-003 and C-004 green — run `pytest tests/test_unified_report.py::test_c003_evasive_table_ranks_ascending_by_undetected_anomaly tests/test_unified_report.py::test_c004_suspicious_table_ranks_descending_by_overall_anomaly -v`; if either fails, debug _compute_ml_summary sort logic in `src/aatf/report.py`

**Checkpoint**: Table ranking verified — C-003 and C-004 both PASS.

---

## Phase 5: User Story 3 — Retraining Recommendation (Priority: P3)

**Goal**: Categories below EVASION_THRESHOLD (0.3) listed for retraining; otherwise no-gap message.
**Independent Test**: C-005 green (already handled by _compute_ml_summary retrain_categories logic from T006).

- [X] T011 [US3] Verify C-005 green — run `pytest tests/test_unified_report.py::test_c005_retrain_categories_and_no_gap_message -v`; if it fails, debug retrain_categories computation in `src/aatf/report.py`

**Checkpoint**: All 5 contracts green — `pytest tests/test_unified_report.py` shows 5 passed.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T012 Lint — run `ruff check src/aatf/report.py tests/test_unified_report.py`; fix any issues (unused imports, line length, etc.)

- [X] T013 Full suite — run `cd /home/yuti/Adaptive-Adversarial-Testing-Framework && pytest` and confirm ≥350 passed, 0 failed (target = 350+)

- [X] T014 Commit — stage and commit with message:
  `feat(F29): add ML Anomaly Defence Analysis section to blind-spot report`
  Files to stage:
  - `src/aatf/report.py`
  - `src/aatf/templates/report.md.j2`
  - `tests/test_unified_report.py`

- [X] T015 Push — `git push origin 029-e10-unified-report`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational Red (Phase 2)**: Depends on Phase 1 — creates tests before any implementation
- **US1 (Phase 3)**: Depends on Phase 2 (tests must be red first) — implements all core logic
- **US2 (Phase 4)**: Depends on Phase 3 (all implementation is in _compute_ml_summary)
- **US3 (Phase 5)**: Depends on Phase 4 — sequential verification
- **Polish (Phase 6)**: Depends on all 5 tests green

### Within Phase 3 (US1)

- T004, T005, T006 can all be done in one editing pass on `report.py` (same file, sequential)
- T007 is a single-line addition to `generate_report()` body
- T008 edits `report.md.j2` (different file from T004-T007, but logically depends on T006 being done first so ctx is clear)
- T009 verifies Phase 3 is complete

### Parallel Opportunities

- T004+T005+T006+T007 (all in report.py) and T008 (template) could be written together in one pass
- T012 (lint) can be checked after any implementation step
- T010 and T011 are pure verification steps — fast

---

## Implementation Strategy

### MVP (US1 Only)

1. Complete Phase 1 (baseline)
2. Complete Phase 2 (write tests, confirm red)
3. Complete T004–T009 (US1 implementation + verification)
4. Run full suite — if ≥348 pass, ship US1
5. US2 and US3 are verification-only (no extra code) — they pass for free once US1 is done

### Incremental Delivery

All 5 contracts are satisfied by a single coherent implementation in `report.py` + `report.md.j2`.
US2 and US3 phases are checkpoints, not separate implementations. The implementation is:
1. Write tests → red
2. Write all of report.py changes (T004–T007) + template (T008) → green
3. Confirm all 5 pass → done

---

## Notes

- `StepRecord.detected: bool` — `not s.detected` = undetected step
- `EVASION_THRESHOLD = 0.3` is a module-level constant; tests can monkeypatch it if needed
- Template insertion must preserve the existing `---` footer as the last line
- `registry.get_action(action_id)` raises `KeyError` if action not in registry — use try/except with "UNKNOWN" fallback
- All 345 existing tests must pass unchanged (backward-compatible: anomaly_score defaults to 0.0)
