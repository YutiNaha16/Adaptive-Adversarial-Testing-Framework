# Contracts: One-Command Reproducibility (F25)

**Phase**: 1 — Design
**Date**: 2026-07-11
**Feature**: 025-e7-repro-oneshot
**Total contracts**: 8 (C-001..C-008)

---

## Shared helpers

```python
import json
import sys
import importlib
from pathlib import Path
import pytest

# Test helper: write a minimal config.yaml to a tmp dir
def _write_config(tmp_path: Path, attacker_class: str = "RandomAttacker") -> Path:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"episodes: 3\n"
        f"seed: 42\n"
        f"output_dir: {tmp_path / 'out'}\n"
        f"ruleset_path: /tmp/rules\n"
        f"detection_threshold: 0.5\n"
        f"attacker_class: {attacker_class}\n"
    )
    return cfg

# Import run_experiment by inserting src/ into sys.path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))
import run_experiment
```

---

## US1 — End-to-End Execution

### C-001: Importability

```
GIVEN  src/run_experiment.py
WHEN   `import run_experiment` (with src/ on sys.path)
THEN   no ImportError; `run_experiment.main` is callable
```

### C-002: Output directory created

```
GIVEN  config.yaml with output_dir pointing to a non-existent directory
WHEN   run_experiment.main(config_path=cfg) is called
THEN   the output directory is created (Path.exists() == True)
```

### C-003: Report file written

```
GIVEN  config.yaml with valid fields, output_dir exists or is auto-created
WHEN   run_experiment.main(config_path=cfg) completes
THEN   at least one .md file exists in output_dir
```

### C-004: Manifest file written

```
GIVEN  config.yaml with valid fields
WHEN   run_experiment.main(config_path=cfg) completes
THEN   at least one file matching run_manifest_*.json exists in output_dir
```

### C-005: Manifest JSON contains required keys

```
GIVEN  a successful run
WHEN   the run_manifest_*.json file is parsed as JSON
THEN   manifest keys include: "seed", "config_snapshot", "timestamp", "git_commit"
       manifest["config_snapshot"]["attacker_class"] == "RandomAttacker"
```

---

## US2 — Determinism

### C-006: Two runs same seed → identical detection_rate

```
GIVEN  two calls to run_experiment.main(config_path=cfg) with same config (seed=42)
WHEN   both complete
THEN   the detection_rate values printed to stdout (or returned) are identical across both
       runs (float comparison with approx tolerance 0.0)
```

---

## US1 — Error Handling

### C-007: Missing config.yaml → SystemExit

```
GIVEN  a config_path pointing to a non-existent file
WHEN   run_experiment.main(config_path=non_existent) is called
THEN   SystemExit is raised with exit code != 0
       AND the error message mentions the missing config file
```

### C-008: Unknown attacker_class → SystemExit with message

```
GIVEN  config.yaml with attacker_class: "BogusAttacker"
WHEN   run_experiment.main(config_path=cfg) is called
THEN   SystemExit is raised with exit code != 0
       AND the error message mentions the unknown attacker class
```

---

## Contract-to-story mapping

| Contract | Story | FR | Description |
|---|---|---|---|
| C-001 | US1 | FR-001 | Importability |
| C-002 | US1 | FR-008 | Output dir created |
| C-003 | US1 | FR-005 | Report written |
| C-004 | US1 | FR-006 | Manifest written |
| C-005 | US1 | FR-006 | Manifest keys correct |
| C-006 | US2 | FR-011 | Determinism via fixed seed |
| C-007 | US1 | FR-012+FR-009 | Missing config → exit |
| C-008 | US1 | FR-009 | Unknown attacker → exit |
