# Tasks: One-Command Reproducibility (F25)

**Input**: Design documents from `/specs/025-e7-repro-oneshot/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/repro-oneshot-contract.md ✅

**TDD approach**: Write all 8 tests first (red = ImportError/ModuleNotFoundError), then implement.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Record baseline and make prerequisite modifications to config.py + config.yaml.

- [ ] T001 Record test baseline: `pytest --tb=no -q 2>&1 | tail -3` — confirm 304 passed, 4 skipped
- [ ] T002 Add `attacker_class: str = "RandomAttacker"` field to `ExperimentConfig` in `src/aatf/config.py` — insert after `detection_threshold` field:
  ```python
  attacker_class: str = "RandomAttacker"
  ```
- [ ] T003 Add `attacker_class: RandomAttacker` to `config.yaml` (repo root) — append as final line
- [ ] T004 Verify existing tests still pass after config change: `pytest tests/test_config.py tests/test_manifest.py tests/test_seeding.py --tb=short -q 2>&1 | tail -5` — confirm no regressions

**Checkpoint**: Config has attacker_class field; baseline unchanged.

---

## Phase 2: Foundational (Red Phase)

**Purpose**: Write all 8 contract tests — must fail before implementation.

**⚠️ CRITICAL**: All 8 tests must be written and confirmed RED before any implementation begins.

- [ ] T005 Create `tests/test_run_experiment.py` with `_write_config` helper and all 8 contract tests:

  **File header, path setup, and helper**:
  ```python
  """Tests for src/run_experiment.py — 8 contracts C-001..C-008."""
  from __future__ import annotations

  import json
  import sys
  from pathlib import Path

  import pytest

  # run_experiment.py lives in src/ alongside the aatf package
  sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
  import run_experiment


  def _write_config(
      tmp_path: Path,
      attacker_class: str = "RandomAttacker",
      episodes: int = 2,
  ) -> Path:
      cfg = tmp_path / "config.yaml"
      out = tmp_path / "out"
      cfg.write_text(
          f"episodes: {episodes}\n"
          f"seed: 42\n"
          f"output_dir: {out}\n"
          f"ruleset_path: /tmp/rules\n"
          f"detection_threshold: 0.5\n"
          f"attacker_class: {attacker_class}\n"
      )
      return cfg
  ```

  **C-001 — importability**:
  ```python
  def test_c001_importability():
      import run_experiment as _re  # noqa: F401
      assert callable(_re.main)
  ```

  **C-002 — output_dir created**:
  ```python
  def test_c002_output_dir_created(tmp_path):
      cfg = _write_config(tmp_path)
      out = tmp_path / "out"
      assert not out.exists()
      run_experiment.main(config_path=cfg)
      assert out.exists()
  ```

  **C-003 — report .md written**:
  ```python
  def test_c003_report_md_written(tmp_path):
      cfg = _write_config(tmp_path)
      run_experiment.main(config_path=cfg)
      out = tmp_path / "out"
      md_files = list(out.glob("*.md"))
      assert len(md_files) >= 1
  ```

  **C-004 — run_manifest written**:
  ```python
  def test_c004_manifest_json_written(tmp_path):
      cfg = _write_config(tmp_path)
      run_experiment.main(config_path=cfg)
      out = tmp_path / "out"
      manifests = list(out.glob("run_manifest_*.json"))
      assert len(manifests) >= 1
  ```

  **C-005 — manifest contains required keys**:
  ```python
  def test_c005_manifest_keys(tmp_path):
      cfg = _write_config(tmp_path)
      run_experiment.main(config_path=cfg)
      out = tmp_path / "out"
      manifest_path = next(out.glob("run_manifest_*.json"))
      data = json.loads(manifest_path.read_text())
      assert "seed" in data
      assert "config_snapshot" in data
      assert "timestamp" in data
      assert "git_commit" in data
      assert data["config_snapshot"]["attacker_class"] == "RandomAttacker"
  ```

  **C-006 — determinism: two runs same seed → same detection_rate**:
  ```python
  def test_c006_determinism(tmp_path, capsys):
      cfg1 = _write_config(tmp_path / "run1", episodes=3)
      run_experiment.main(config_path=cfg1)
      out1 = capsys.readouterr().out

      cfg2 = _write_config(tmp_path / "run2", episodes=3)
      run_experiment.main(config_path=cfg2)
      out2 = capsys.readouterr().out

      # Extract Detection Rate line from both runs
      def _get_dr(output: str) -> str:
          for line in output.splitlines():
              if "Detection Rate" in line:
                  return line.strip()
          return ""

      assert _get_dr(out1) == _get_dr(out2)
      assert _get_dr(out1) != ""
  ```

  **C-007 — missing config → SystemExit**:
  ```python
  def test_c007_missing_config_exits(tmp_path):
      with pytest.raises(SystemExit) as exc_info:
          run_experiment.main(config_path=tmp_path / "nonexistent.yaml")
      assert exc_info.value.code != 0
  ```

  **C-008 — unknown attacker_class → SystemExit**:
  ```python
  def test_c008_unknown_attacker_class_exits(tmp_path):
      cfg = _write_config(tmp_path, attacker_class="BogusAttacker")
      with pytest.raises(SystemExit) as exc_info:
          run_experiment.main(config_path=cfg)
      assert exc_info.value.code != 0
  ```

- [ ] T006 Confirm RED state: `pytest tests/test_run_experiment.py -v 2>&1 | tail -15` — expect ModuleNotFoundError for `run_experiment`; confirm 0 passed, 8 errors

**Checkpoint**: 8 tests written, all failing. Ready to implement.

---

## Phase 3: User Story 1 — End-to-End Execution (Priority: P1) 🎯 MVP

**Goal**: `run_experiment.main()` runs N episodes, writes report + manifest, creates output_dir, handles errors; covers C-001..C-005, C-007..C-008.

**Independent Test**: `pytest tests/test_run_experiment.py -k "c001 or c002 or c003 or c004 or c005 or c007 or c008" -v` — 7 passed.

- [ ] T007 [US1] Create `src/run_experiment.py` (~90 LOC) with exact content:

  ```python
  """Experiment entrypoint — load config, run N episodes, generate report and manifest."""
  from __future__ import annotations

  import argparse
  import sys
  from datetime import UTC, datetime
  from pathlib import Path

  from aatf.action_library import REGISTRY
  from aatf.attacker import FixedScriptAttacker, LinUCBAttacker, RandomAttacker
  from aatf.config import load_config
  from aatf.context_vector import EpisodeState, build_context
  from aatf.defence import NullDefence
  from aatf.episode import run_episode
  from aatf.linucb import LinUCBModel
  from aatf.manifest import write_manifest
  from aatf.metrics import EpisodeRecord, detection_rate, robustness_score
  from aatf.report import generate_report
  from aatf.seeding import seed_everything

  _ATTACKER_REGISTRY = {
      "RandomAttacker": lambda seed, ctx_dim, n_actions: RandomAttacker(seed=seed),
      "FixedScriptAttacker": lambda seed, ctx_dim, n_actions: FixedScriptAttacker(),
      "LinUCBAttacker": lambda seed, ctx_dim, n_actions: LinUCBAttacker(
          LinUCBModel(n_actions=n_actions, context_dim=ctx_dim)
      ),
  }


  def _make_attacker(name: str, seed: int, ctx_dim: int, n_actions: int):
      if name not in _ATTACKER_REGISTRY:
          raise ValueError(
              f"Unknown attacker_class {name!r}. "
              f"Valid: {sorted(_ATTACKER_REGISTRY)}"
          )
      return _ATTACKER_REGISTRY[name](seed, ctx_dim, n_actions)


  def main(config_path: str | Path = "config.yaml") -> None:
      try:
          config = load_config(config_path)
      except FileNotFoundError as exc:
          print(f"ERROR: {exc}", file=sys.stderr)
          sys.exit(1)

      seed_everything(config.seed)
      output_dir = Path(config.output_dir)
      output_dir.mkdir(parents=True, exist_ok=True)

      initial_state = EpisodeState()
      ctx_dim = len(build_context(initial_state))
      n_actions = len(REGISTRY.actions)

      try:
          attacker = _make_attacker(config.attacker_class, config.seed, ctx_dim, n_actions)
      except ValueError as exc:
          print(f"ERROR: {exc}", file=sys.stderr)
          sys.exit(2)

      defence = NullDefence()
      records: list[EpisodeRecord] = []

      print("Adaptive Adversarial Testing Framework")
      print("=" * 38)
      print(f"Attacker : {config.attacker_class}")
      print(f"Episodes : {config.episodes}")
      print(f"Seed     : {config.seed}")
      print("-" * 38)
      print(f"Running {config.episodes} episodes...")

      for i in range(config.episodes):
          state = EpisodeState()
          step_contexts: list = []

          def action_selector(available, ep_state, _sc=step_contexts):
              ctx = build_context(ep_state)
              _sc.append(ctx)
              return attacker.choose_action(available, ctx)

          result = run_episode(state, action_selector, lambda _: None, defence)

          for step, ctx in zip(result.steps, step_contexts):
              attacker.observe(step.action_id, ctx, step.reward)

          records.append(EpisodeRecord(
              attacker_class=config.attacker_class,
              seed=config.seed,
              steps=result.steps,
              total_reward=result.total_reward,
              completed=result.completed,
              episode_index=i,
          ))

      dr = detection_rate(records)
      window = min(10, len(records))
      rs = robustness_score(records, window=window)

      ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
      report_path = output_dir / f"report_{ts}.md"
      generate_report(records, REGISTRY, report_path)
      manifest_path = write_manifest(config, config.seed)

      print("-" * 38)
      print(f"Detection Rate   : {dr:.4f}")
      print(f"Robustness Score : {rs:.4f}")
      print(f"Report written   : {report_path}")
      print(f"Manifest written : {manifest_path}")


  if __name__ == "__main__":
      parser = argparse.ArgumentParser(description="Run AATF experiment")
      parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
      args = parser.parse_args()
      main(config_path=args.config)
  ```

- [ ] T008 [US1] Verify US1 contracts green: `pytest tests/test_run_experiment.py -k "c001 or c002 or c003 or c004 or c005 or c007 or c008" -v 2>&1 | tail -15` — confirm 7 passed, 0 failed

**Checkpoint**: US1 complete — experiment runs, files written, errors handled.

---

## Phase 4: User Story 2 — Deterministic Reproducibility (Priority: P2)

**Goal**: Two runs with same seed produce identical detection_rate; covers C-006.

**Independent Test**: `pytest tests/test_run_experiment.py::test_c006_determinism -v` — 1 passed.

- [ ] T009 [US2] Verify C-006 green (determinism is handled by seed_everything already in T007): `pytest tests/test_run_experiment.py::test_c006_determinism -v 2>&1 | tail -10` — confirm 1 passed

**Checkpoint**: US2 complete — determinism verified.

---

## Phase 5: User Story 3 — Quick-Start Documentation (Priority: P3)

**Goal**: README Quick Start section documents `make run` and expected outputs.

**Independent Test**: README.md contains "Quick Start" section with `make run` command.

- [ ] T010 [US3] [P] Update `Makefile` `run:` target — change `$(PY) -m aatf` to `$(PY) src/run_experiment.py` and update the comment:
  ```makefile
  run:  ## Run the full experiment end-to-end (requires: make setup; optionally: make lab-up)
  	$(PY) src/run_experiment.py
  ```
- [ ] T011 [US3] [P] Add Quick Start section to `README.md` — insert after any existing intro, before other sections:
  ```markdown
  ## Quick Start

  ```bash
  # 1. Set up the Python environment (once)
  make setup

  # 2. (Optional) Start the Docker lab for live traffic capture
  make lab-up

  # 3. Run the full experiment
  make run
  ```

  **Expected outputs** in `outputs/run_001/` after `make run`:
  - `report_<timestamp>.md` — Markdown blind-spot report with detection rate, robustness score, and blind-spot table
  - `run_manifest_<timestamp>.json` — Provenance record (seed, git commit, packages, config snapshot)

  **Key config** (`config.yaml`):
  - `seed: 42` — change for a different random run; same seed → identical results
  - `episodes: 100` — number of attack episodes to simulate
  - `attacker_class: RandomAttacker` — or `LinUCBAttacker`, `FixedScriptAttacker`
  ```

**Checkpoint**: US3 complete — README documents the one-command workflow.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Lint, full suite, commit, merge to main, push.

- [ ] T012 Run ruff on new/modified files: `ruff check src/run_experiment.py tests/test_run_experiment.py --fix` — confirm 0 errors
- [ ] T013 Run full suite: `pytest --tb=short -q 2>&1 | tail -5` — confirm ≥312 passed, 4 skipped
- [ ] T014 Stage and commit: `git add src/run_experiment.py tests/test_run_experiment.py src/aatf/config.py config.yaml Makefile README.md && git commit -m "feat(F25): one-command reproducibility — run_experiment.py + make run (8 contracts green)"`
- [ ] T015 Merge to main: `git checkout main && git merge --no-ff 025-e7-repro-oneshot -m "merge: F25 one-command reproducibility"`
- [ ] T016 Verify suite on main: `pytest --tb=no -q 2>&1 | tail -3` — confirm ≥312 passed
- [ ] T017 Push: `git push origin main`

**Checkpoint**: F25 complete and pushed.

---

## Dependencies

```
T001 → T002 → T003 → T004              (setup, sequential)
T004 → T005 → T006                     (red phase)
T006 → T007 → T008                     (US1: implement then verify)
T008 → T009                            (US2: verify determinism)
T008 → T010 ∥ T011                     (US3: Makefile + README in parallel)
T009 + T010 + T011 → T012 → T013 → T014 → T015 → T016 → T017
```

T010 and T011 are parallelizable (different files).

---

## Implementation Strategy

| Phase | Scope | Tests | Value |
|---|---|---|---|
| MVP | T001–T008 | C-001..C-005, C-007..C-008 | Full experiment pipeline works |
| +US2 | T009 | C-006 | Determinism verified |
| +US3 | T010–T011 | (README manual) | One-command documented |
| Full | T012–T017 | All 8 green | F25 merged + pushed |

---

## Summary

| Metric | Value |
|---|---|
| Total tasks | 17 (T001–T017) |
| US1 tasks | T007–T008 (2 tasks, 7 contracts) |
| US2 tasks | T009 (1 task, 1 contract) |
| US3 tasks | T010–T011 (2 tasks, no contract) |
| Setup/foundational | T001–T006 (6 tasks) |
| Polish | T012–T017 (6 tasks) |
| Parallelizable | T010 ∥ T011 (after T008) |
| Baseline | 304 passed |
| Target | ≥312 passed (+8) |
| New files | 2 (run_experiment.py, test_run_experiment.py) |
| Modified files | 4 (config.py, config.yaml, Makefile, README.md) |
| New pip deps | 0 |
