# Tasks: Report Generator (F24)

**Input**: Design documents from `/specs/023-e6-report-generator/`  
**Branch**: `023-e6-report-generator`  
**Baseline**: 276 passed, 4 skipped, 6 failed | **Target**: ≥286 passed (+10)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

## Key facts for implementation

**ActionDefinition constructor** (from `src/aatf/action_library.py`):
```python
ActionDefinition(action_id=..., category="test", description="test desc",
                 default_parameters={}, suricata_category=...)
```

**Test helpers** (write once in test file header):
```python
from __future__ import annotations
from datetime import UTC, datetime
from aatf.action_library import ActionDefinition, ActionRegistry
from aatf.episode import StepRecord
from aatf.metrics import EpisodeRecord
from aatf.report import generate_report

FIXED_TS = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

def _step(action_id: str, detected: bool) -> StepRecord:
    return StepRecord(action_id=action_id, detected=detected, stage_progress=0, reward=0.0)

def _ep(attacker_class: str, seed: int, *steps: StepRecord, total_reward: float = 0.0) -> EpisodeRecord:
    return EpisodeRecord(attacker_class=attacker_class, seed=seed, steps=list(steps),
                         total_reward=total_reward, completed=False, episode_index=0)

def _defn(action_id: str, suricata_category: str) -> ActionDefinition:
    return ActionDefinition(action_id=action_id, category="test", description="test desc",
                            default_parameters={}, suricata_category=suricata_category)

def _reg(*defs: ActionDefinition) -> ActionRegistry:
    return ActionRegistry(list(defs))
```

**No red-phase stub**: Because Jinja2 raises `TemplateNotFound` if the template file is absent, pure red phase is not possible. Instead: write tests per story, then create/extend the template and implement report.py together, then verify green.

---

## Phase 1: Setup

**Purpose**: Install new pip dependency, create templates directory, confirm baseline

- [ ] T001 Add `jinja2>=3.1` to `requirements.in` under a `# Templating` comment section
- [ ] T002 Install jinja2 in venv: `source /home/yuti/Adaptive-Adversarial-Testing-Framework/.venv/bin/activate && pip install "jinja2>=3.1"`
- [ ] T003 Create directory `src/aatf/templates/` (touch a `.gitkeep` or leave empty — the template file will be created in Phase 3)
- [ ] T004 Record baseline: `source .venv/bin/activate && cd src && pytest --tb=no -q 2>&1 | tail -3` — confirm 276 passed, 4 skipped, 6 failed

---

## Phase 2: Foundational

**Purpose**: Verify all upstream imports resolve before writing any new code

⚠️ CRITICAL: No user story work can begin until this phase is complete

- [ ] T005 Verify all imports resolve: run `source .venv/bin/activate && python -c "from aatf.metrics import EpisodeRecord, detection_rate, robustness_score; from aatf.statistics import summarise_metric; from aatf.explainability import explain_evasions; from aatf.action_library import ActionRegistry; from jinja2 import Environment, FileSystemLoader; print('OK')"` — must print OK with no errors

**Checkpoint**: All upstream deps available — can now implement per story

---

## Phase 3: User Story 1 — Core Generation (Priority: P1) 🎯 MVP

**Goal**: `generate_report` function exists, returns a str, writes to file, is deterministic, handles empty records

**Independent Test**: `cd src && pytest ../tests/test_report.py::test_c001_importable ../tests/test_report.py::test_c002_returns_string_and_writes_file ../tests/test_report.py::test_c003_determinism ../tests/test_report.py::test_c004_empty_records -v`

### Tests for User Story 1

- [ ] T006 [US1] Write `tests/test_report.py` with helpers (FIXED_TS, _step, _ep, _defn, _reg — see Key facts above) and contracts C-001..C-004:

  **C-001** (`test_c001_importable`):
  ```python
  def test_c001_importable():
      assert callable(generate_report)
  ```

  **C-002** (`test_c002_returns_string_and_writes_file`):
  ```python
  def test_c002_returns_string_and_writes_file(tmp_path):
      reg = _reg(_defn("ssh_brute_force", "ET BRUTE_FORCE"), _defn("tcp_port_scan", "ET SCAN"))
      ep = _ep("LinUCB", 0, _step("ssh_brute_force", False), _step("tcp_port_scan", True))
      out = tmp_path / "report.md"
      result = generate_report([ep], reg, out, generated_at=FIXED_TS)
      assert isinstance(result, str)
      assert len(result) > 0
      assert out.read_text(encoding="utf-8") == result
  ```

  **C-003** (`test_c003_determinism`):
  ```python
  def test_c003_determinism(tmp_path):
      reg = _reg(_defn("ssh_brute_force", "ET BRUTE_FORCE"))
      ep = _ep("LinUCB", 0, _step("ssh_brute_force", False))
      r1 = generate_report([ep], reg, tmp_path / "r1.md", generated_at=FIXED_TS)
      r2 = generate_report([ep], reg, tmp_path / "r2.md", generated_at=FIXED_TS)
      assert r1 == r2
  ```

  **C-004** (`test_c004_empty_records`):
  ```python
  def test_c004_empty_records(tmp_path):
      reg = _reg()
      result = generate_report([], reg, tmp_path / "report.md", generated_at=FIXED_TS)
      assert len(result) > 0
      assert "0" in result
  ```

### Implementation for User Story 1

- [ ] T007 [US1] Create `src/aatf/templates/report.md.j2` with the full Jinja2 template skeleton (all sections — metadata, headline metrics with `{% if reward_mean is not none %}` guard, blind spots with `{% if explanations %}` guard, footer):

  ```jinja2
  # Blind-Spot Report

  ## Run Metadata

  - **Attacker**: {{ attacker_classes | join(", ") if attacker_classes else "N/A" }}
  - **Seeds**: {{ seeds | join(", ") if seeds else "N/A" }}
  - **Episodes**: {{ episode_count }}
  - **Generated**: {{ generated_at }}

  ## Headline Metrics

  | Metric | Value |
  |--------|-------|
  | Detection Rate | {{ "%.1f%%" | format(detection_rate * 100) }} |
  | Robustness Score (last {{ robustness_window }} ep.) | {{ "%.1f%%" | format(robustness_score * 100) }} |
  {% if reward_mean is not none %}
  | Mean Total Reward | {{ "%.4f" | format(reward_mean) }} ± {{ "%.4f" | format(reward_std) }} (95% CI: {{ "%.4f" | format(reward_ci_low) }}–{{ "%.4f" | format(reward_ci_high) }}) |
  {% else %}
  | Mean Total Reward | N/A |
  {% endif %}

  ## Blind Spots

  {% if explanations %}
  | Action | Category | Evasion Rate | Evaded | Total | Remediation |
  |--------|----------|--------------|--------|-------|-------------|
  {% for ex in explanations %}
  | {{ ex.action_id }} | {{ ex.suricata_category }} | {{ "%.1f%%" | format(ex.evasion_rate * 100) }} | {{ ex.evasion_count }} | {{ ex.total_count }} | {{ ex.remediation }} |
  {% endfor %}
  {% else %}
  _No blind spots detected — all actions were detected on every step._
  {% endif %}

  ---
  *Generated from logged episode records. No live defence systems were accessed.*
  ```

- [ ] T008 [US1] Create `src/aatf/report.py` with the complete `generate_report` function:

  ```python
  """Report generator — renders blind-spot Markdown report from episode logs."""
  from __future__ import annotations

  from datetime import UTC, datetime
  from pathlib import Path

  from jinja2 import Environment, FileSystemLoader

  from aatf.action_library import ActionRegistry
  from aatf.explainability import explain_evasions
  from aatf.metrics import EpisodeRecord, detection_rate, robustness_score
  from aatf.statistics import summarise_metric

  _TEMPLATE_DIR = Path(__file__).parent / "templates"


  def generate_report(
      records: list[EpisodeRecord],
      registry: ActionRegistry,
      output_path: str | Path,
      *,
      generated_at: datetime | None = None,
  ) -> str:
      out = Path(output_path)
      if not out.parent.exists():
          raise FileNotFoundError(f"Output directory does not exist: {out.parent}")

      if generated_at is None:
          generated_at = datetime.now(UTC)

      attacker_classes = sorted({r.attacker_class for r in records})
      seeds = sorted({r.seed for r in records})
      episode_count = len(records)
      window = min(10, len(records))
      dr = detection_rate(records)
      rs = robustness_score(records, window=window)
      reward_values = [r.total_reward for r in records]
      reward_summary = summarise_metric("total_reward", reward_values) if reward_values else None
      explanations = explain_evasions(records, registry)

      ctx = {
          "attacker_classes": attacker_classes,
          "seeds": seeds,
          "episode_count": episode_count,
          "generated_at": generated_at.isoformat(),
          "detection_rate": dr,
          "robustness_score": rs,
          "robustness_window": window,
          "reward_mean": reward_summary.mean if reward_summary else None,
          "reward_std": reward_summary.std if reward_summary else None,
          "reward_ci_low": reward_summary.ci_low if reward_summary else None,
          "reward_ci_high": reward_summary.ci_high if reward_summary else None,
          "explanations": explanations,
      }

      env = Environment(
          loader=FileSystemLoader(str(_TEMPLATE_DIR)),
          autoescape=False,
          keep_trailing_newline=True,
      )
      template = env.get_template("report.md.j2")
      rendered = template.render(**ctx)

      out.write_text(rendered, encoding="utf-8")
      return rendered
  ```

- [ ] T009 [US1] Verify C-001..C-004 green: `source /home/yuti/Adaptive-Adversarial-Testing-Framework/.venv/bin/activate && cd src && pytest ../tests/test_report.py::test_c001_importable ../tests/test_report.py::test_c002_returns_string_and_writes_file ../tests/test_report.py::test_c003_determinism ../tests/test_report.py::test_c004_empty_records -v`

**Checkpoint**: Core generation works — returns string, writes file, deterministic, empty-safe

---

## Phase 4: User Story 2 — Headline Metrics (Priority: P2)

**Goal**: Detection rate, robustness score, and reward CI appear correctly in the rendered report

**Independent Test**: `cd src && pytest ../tests/test_report.py::test_c005_detection_rate_in_report ../tests/test_report.py::test_c006_mean_reward_in_report -v`

### Tests for User Story 2

- [ ] T010 [US2] Append tests C-005..C-006 to `tests/test_report.py`:

  **C-005** (`test_c005_detection_rate_in_report`):
  ```python
  def test_c005_detection_rate_in_report(tmp_path):
      reg = _reg(_defn("tcp_port_scan", "ET SCAN"), _defn("ssh_brute_force", "ET BRUTE_FORCE"))
      ep = _ep("LinUCB", 0, _step("tcp_port_scan", True), _step("ssh_brute_force", False))
      result = generate_report([ep], reg, tmp_path / "report.md", generated_at=FIXED_TS)
      assert "50.0%" in result
  ```

  **C-006** (`test_c006_mean_reward_in_report`):
  ```python
  def test_c006_mean_reward_in_report(tmp_path):
      reg = _reg(_defn("ssh_brute_force", "ET BRUTE_FORCE"))
      ep1 = _ep("LinUCB", 0, _step("ssh_brute_force", False), total_reward=1.0)
      ep2 = _ep("LinUCB", 1, _step("ssh_brute_force", False), total_reward=-1.0)
      result = generate_report([ep1, ep2], reg, tmp_path / "report.md", generated_at=FIXED_TS)
      assert "0.0000" in result
  ```

- [ ] T011 [US2] Verify C-005..C-006 green: `cd src && pytest ../tests/test_report.py::test_c005_detection_rate_in_report ../tests/test_report.py::test_c006_mean_reward_in_report -v`

**Checkpoint**: Headline metrics rendered correctly

---

## Phase 5: User Story 3 — Blind-Spots Table (Priority: P3)

**Goal**: Evaded actions appear ranked by evasion rate descending; all-detected case shows the "no blind spots" message

**Independent Test**: `cd src && pytest ../tests/test_report.py::test_c007_blind_spots_ranked ../tests/test_report.py::test_c008_no_blind_spots_message -v`

### Tests for User Story 3

- [ ] T012 [US3] Append tests C-007..C-008 to `tests/test_report.py`:

  **C-007** (`test_c007_blind_spots_ranked`):
  ```python
  def test_c007_blind_spots_ranked(tmp_path):
      reg = _reg(_defn("action_a", "ET SCAN"), _defn("action_b", "ET SCAN"))
      # action_a: 3/4 evaded (0.75), action_b: 1/4 evaded (0.25)
      eps = [
          _ep("LinUCB", 0,
              _step("action_a", False), _step("action_a", False),
              _step("action_a", False), _step("action_a", True),
              _step("action_b", False), _step("action_b", True),
              _step("action_b", True), _step("action_b", True)),
      ]
      result = generate_report(eps, reg, tmp_path / "report.md", generated_at=FIXED_TS)
      assert result.index("action_a") < result.index("action_b")
  ```

  **C-008** (`test_c008_no_blind_spots_message`):
  ```python
  def test_c008_no_blind_spots_message(tmp_path):
      reg = _reg(_defn("tcp_port_scan", "ET SCAN"))
      ep = _ep("LinUCB", 0, _step("tcp_port_scan", True), _step("tcp_port_scan", True))
      result = generate_report([ep], reg, tmp_path / "report.md", generated_at=FIXED_TS)
      assert "No blind spots detected" in result
  ```

- [ ] T013 [US3] Verify C-007..C-008 green: `cd src && pytest ../tests/test_report.py::test_c007_blind_spots_ranked ../tests/test_report.py::test_c008_no_blind_spots_message -v`

**Checkpoint**: Blind-spots table ranked correctly; empty case handled

---

## Phase 6: User Story 4 — Run Metadata and Footer (Priority: P4)

**Goal**: Attacker class, seeds, episode count, and ISO timestamp appear in metadata; error raised on missing parent dir

**Independent Test**: `cd src && pytest ../tests/test_report.py::test_c009_metadata_fields ../tests/test_report.py::test_c010_missing_parent_raises -v`

### Tests for User Story 4

- [ ] T014 [US4] Append tests C-009..C-010 to `tests/test_report.py`:

  **C-009** (`test_c009_metadata_fields`):
  ```python
  def test_c009_metadata_fields(tmp_path):
      reg = _reg(_defn("tcp_port_scan", "ET SCAN"))
      ep1 = _ep("LinUCBAttacker", 42, _step("tcp_port_scan", True))
      ep2 = _ep("LinUCBAttacker", 99, _step("tcp_port_scan", True))
      result = generate_report([ep1, ep2], reg, tmp_path / "report.md", generated_at=FIXED_TS)
      assert "LinUCBAttacker" in result
      assert "42" in result
      assert "99" in result
      assert "2024-01-01" in result
  ```

  **C-010** (`test_c010_missing_parent_raises`):
  ```python
  import pytest
  def test_c010_missing_parent_raises():
      reg = _reg()
      with pytest.raises(FileNotFoundError):
          generate_report([], reg, "/nonexistent_dir_xyz/report.md", generated_at=FIXED_TS)
  ```

- [ ] T015 [US4] Verify C-009..C-010 green: `cd src && pytest ../tests/test_report.py::test_c009_metadata_fields ../tests/test_report.py::test_c010_missing_parent_raises -v`

**Checkpoint**: All 10 contracts green

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T016 Run ruff check on new files and fix any issues: `source /home/yuti/Adaptive-Adversarial-Testing-Framework/.venv/bin/activate && cd src && ruff check ../tests/test_report.py aatf/report.py --fix`
- [ ] T017 Run full test suite and confirm ≥286 passed, 4 skipped, 6 failed: `cd src && pytest --tb=short -q 2>&1 | tail -5`
- [ ] T018 Stage and commit all new files: `git add src/aatf/report.py src/aatf/templates/report.md.j2 tests/test_report.py requirements.in && git commit -m "Add F24 report generator: generate_report + Jinja2 template (10 contracts green)"`
- [ ] T019 Merge to main: `git checkout main && git merge 023-e6-report-generator --no-ff -m "Merge F24 023-e6-report-generator"`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on T001 + T002 (jinja2 installed)
- **Phase 3 (US1)**: Depends on Phase 2 — BLOCKS all other stories
- **Phase 4 (US2)**: Depends on Phase 3 (generate_report must exist)
- **Phase 5 (US3)**: Depends on Phase 3 (generate_report + template must exist)
- **Phase 6 (US4)**: Depends on Phase 3 (generate_report must exist)
- **Phase 7 (Polish)**: Depends on all story phases complete

### Within Each Story

- Write tests FIRST (T006, T010, T012, T014)
- Template and implementation created/extended next
- Verify green before moving to next story

### Parallel Opportunities

- T001 (requirements.in) and T003 (create templates dir) can run in parallel
- US2/US3/US4 test tasks (T010, T012, T014) can be written in parallel once Phase 3 is green

---

## Parallel Example: Phase 3 (US1)

```bash
# T007 and T008 can be written in parallel (different files):
Task: "Create src/aatf/templates/report.md.j2"
Task: "Create src/aatf/report.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005)
3. Complete Phase 3: US1 (T006–T009)
4. **STOP and VALIDATE**: `pytest ../tests/test_report.py -k "c00[1-4]"` — 4 tests green

### Incremental Delivery

1. Setup + Foundational → jinja2 available
2. US1 (T006–T009) → core generation works (4 tests green)
3. US2 (T010–T011) → metrics rendered correctly (6 tests green)
4. US3 (T012–T013) → blind-spots table works (8 tests green)
5. US4 (T014–T015) → metadata + error guard (10 tests green)
6. Polish (T016–T019) → ruff clean, merged to main

---

## Task Summary

| Phase | Tasks | Story | Contracts |
|---|---|---|---|
| Phase 1 Setup | T001–T004 | — | — |
| Phase 2 Foundational | T005 | — | — |
| Phase 3 US1 | T006–T009 | US1 | C-001..C-004 |
| Phase 4 US2 | T010–T011 | US2 | C-005..C-006 |
| Phase 5 US3 | T012–T013 | US3 | C-007..C-008 |
| Phase 6 US4 | T014–T015 | US4 | C-009..C-010 |
| Phase 7 Polish | T016–T019 | — | — |
| **Total** | **19 tasks** | | **10 contracts** |
