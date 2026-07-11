# Quickstart: Automated Phase 1 Gate Evaluation (F26)

**Date**: 2026-07-11
**Module**: `src/aatf/gate.py`

## Standalone gate usage

```python
from aatf.gate import phase1_gate
from aatf.ground_truth import ValidationResult

# Build a minimal ValidationResult (BSP from F22 validate_blind_spots)
vr = ValidationResult(
    blind_spot_precision=0.85,
    true_positives=17,
    false_positives=3,
    total_reported=20,
    disabled_sid_count=10,
)

# Pass experiment records + validation result
gate_result = phase1_gate(records, vr)
print(gate_result.summary)
# → "Phase 1 PASSED (3/3 criteria met)"

for c in gate_result.criteria:
    status = "PASS" if c.passed else "FAIL"
    print(f"  {c.name}: {c.value:.4f} >= {c.threshold:.4f} [{status}]")
```

## Via make run (integrated in run_experiment.py)

```bash
make run
```

Expected stdout (with NullDefence — gate fails BSP):
```
Adaptive Adversarial Testing Framework
======================================
Attacker : RandomAttacker
Episodes : 100
Seed     : 42
--------------------------------------
Running 100 episodes...
--------------------------------------
Detection Rate   : 0.0000
Robustness Score : 0.0000
Report written   : outputs/run_001/report_20260711T120000.md
Manifest written : outputs/run_001/run_manifest_20260711T120000000000Z.json
--------------------------------------
  detection_rate        : 0.0000 (≥0.0000) [PASS]
  blind_spot_precision  : 0.0000 (≥0.8000) [FAIL]
  robustness_score      : 0.0000 (≥0.0000) [PASS]
Phase 1 FAILED (2/3 criteria met: blind_spot_precision below threshold)
```

## Checking gate in manifest

```python
import json
data = json.loads((output_dir / "run_manifest_*.json").read_text())
gate = data["phase1_gate"]
print(gate["passed"])    # False (BSP = 0.0 with NullDefence)
print(gate["summary"])   # "Phase 1 FAILED ..."
```

## Running tests

```bash
pytest tests/test_gate.py -v
```

Target: 10 new tests (C-001..C-010) all green, overall suite ≥322 passed.
