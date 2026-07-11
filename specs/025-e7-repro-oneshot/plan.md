# Implementation Plan: One-Command Reproducibility (F25)

**Branch**: `025-e7-repro-oneshot` | **Date**: 2026-07-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/025-e7-repro-oneshot/spec.md`

## Summary

Implement `src/run_experiment.py` — the real experiment entrypoint that replaces the
`__main__.py` stub. Update `Makefile` `run:` target, add `attacker_class` field to
`ExperimentConfig` + `config.yaml`, and add a README Quick Start section. 8 TDD contracts.
No new pip dependencies.

---

## Technical Context

**Language/Version**: Python 3.12 (pinned per F01)
**Primary Dependencies**: stdlib only — `json`, `datetime`, `pathlib`, `sys`, `argparse`;
existing project: `aatf.config`, `aatf.seeding`, `aatf.attacker`, `aatf.episode`,
`aatf.metrics`, `aatf.report`, `aatf.manifest`, `aatf.action_library`, `aatf.defence`,
`aatf.context_vector`
**Storage**: reads `config.yaml`; writes `output_dir/*.md` + `output_dir/run_manifest_*.json`
**Testing**: pytest; `pytest tests/test_run_experiment.py`
**Target Platform**: Linux (same host as all other `aatf` modules)
**Project Type**: Single Python package under `src/`
**Performance Goals**: completes 100 episodes in under 5 minutes (NullDefence path)
**Constraints**: Constitution Principles I (no external traffic), II (fixed seed determinism)
**Scale/Scope**: One call per `make run`; N episodes per run (config-driven)

---

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| I. Safety & Isolation | ✅ PASS | Default `NullDefence` + no-op executor — no network traffic emitted when lab not running; `ActionExecutor` already enforces `ExternalTargetError` for non-lab IPs |
| II. Reproducibility & Determinism | ✅ PASS | `seed_everything(config.seed)` called before all stochastic operations; same seed → same EpisodeResult sequence |
| III. Pluggable Defence Interface | ✅ PASS | Entrypoint uses `Defence` abstraction; `NullDefence` is the default |
| IV. Scientific Validity / TDD | ✅ PASS | 8 contracts written first; run_manifest emitted per run |
| V. Explainability | ✅ N/A | Consumed via `generate_report` (F24) which calls `explain_evasions` |
| VI. Observability | ✅ PASS | Manifest + report written per run; stdout summary; EpisodeRecord logs per episode |
| VII. Phased Delivery | ✅ PASS | F25 is the gate prerequisite; feeds F26 gate evaluation |

**Post-design re-check**: All principles hold.

---

## Project Structure

### Documentation

```text
specs/025-e7-repro-oneshot/
├── plan.md              ← this file
├── research.md          ← 12 decisions from API inspection
├── data-model.md        ← data flow diagram
├── quickstart.md        ← usage examples
├── contracts/
│   └── repro-oneshot-contract.md   ← 8 contracts C-001..C-008
└── tasks.md             (Phase 2 — /sp.tasks)
```

### Source Code

```text
src/
└── run_experiment.py    # ~90 LOC (NEW)
src/aatf/
└── config.py            # +1 field: attacker_class (MODIFIED)

config.yaml              # +1 key: attacker_class (MODIFIED)
Makefile                 # update run: target (MODIFIED)
README.md                # add Quick Start section (MODIFIED)

tests/
└── test_run_experiment.py   # ~180 LOC, 8 tests (NEW)
```

---

## Implementation Sketch

### src/aatf/config.py — add attacker_class field

```python
class ExperimentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    episodes: int = Field(gt=0)
    seed: int = Field(ge=0)
    output_dir: Path
    ruleset_path: Path
    detection_threshold: float = Field(ge=0.0, le=1.0)
    attacker_class: str = "RandomAttacker"   # NEW — default preserves existing config.yaml
```

### config.yaml — add attacker_class

```yaml
episodes: 100
seed: 42
output_dir: outputs/run_001
ruleset_path: /etc/suricata/rules
detection_threshold: 0.5
attacker_class: RandomAttacker
```

### src/run_experiment.py (~90 LOC)

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

    # Determine context dimension from a dummy initial state
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

    print(f"Adaptive Adversarial Testing Framework")
    print(f"{'='*38}")
    print(f"Attacker : {config.attacker_class}")
    print(f"Episodes : {config.episodes}")
    print(f"Seed     : {config.seed}")
    print(f"{'-'*38}")
    print(f"Running {config.episodes} episodes...")

    for i in range(config.episodes):
        state = EpisodeState()
        step_contexts: list = []

        def action_selector(available, ep_state, _step_contexts=step_contexts):
            ctx = build_context(ep_state)
            _step_contexts.append(ctx)
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

    print(f"{'-'*38}")
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

### Makefile run: target (updated)

```makefile
run:  ## Run the full experiment (requires: make setup; optionally: make lab-up)
	$(PY) src/run_experiment.py
```

### tests/test_run_experiment.py (~180 LOC)

```python
"""Tests for src/run_experiment.py — 8 contracts C-001..C-008."""
import json
import sys
from pathlib import Path
import pytest

# run_experiment.py lives in src/ (not a package); add src/ to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import run_experiment


def _write_config(tmp_path: Path, attacker_class: str = "RandomAttacker",
                  episodes: int = 2) -> Path:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"episodes: {episodes}\n"
        f"seed: 42\n"
        f"output_dir: {tmp_path / 'out'}\n"
        f"ruleset_path: /tmp/rules\n"
        f"detection_threshold: 0.5\n"
        f"attacker_class: {attacker_class}\n"
    )
    return cfg

# C-001: importability
# C-002: output_dir created
# C-003: report .md written
# C-004: run_manifest_*.json written
# C-005: manifest keys correct
# C-006: two runs same seed → same detection_rate
# C-007: missing config → SystemExit
# C-008: unknown attacker_class → SystemExit
```

---

## Baseline and target

| Metric | Value |
|---|---|
| Baseline (post-E6) | 304 passed, 4 skipped |
| New tests | 8 (C-001..C-008) |
| Target | ≥312 passed, 4 skipped |

---

## Story completion order

| Story | Contracts | Notes |
|---|---|---|
| US1 (P1) | C-001..C-005, C-007..C-008 | Core run + errors |
| US2 (P2) | C-006 | Determinism |
| US3 (P3) | README | Documentation (no test contract) |

---

## Complexity Tracking

No constitution violations. Table is empty.
