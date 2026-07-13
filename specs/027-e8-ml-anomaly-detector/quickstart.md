# Quickstart: ML Anomaly Defence (F27)

## Integration Scenarios

### Scenario 1: Basic usage — observe an action

```python
from aatf.ml_defence import MLAnomalyDefence
from aatf.contracts import Action
from datetime import datetime, timezone

defence = MLAnomalyDefence(threshold=0.6, seed=42)

action = Action(
    action_id="port_scan",
    category="scan",
    parameters={"port_range_start": 1, "port_range_end": 1024, "timing_ms": 10},
    timestamp=datetime.now(timezone.utc),
)
result = defence.observe(action)
print(result.anomaly_score)  # float in [0,1]; higher = more anomalous
print(result.alerted)        # True if anomaly_score >= 0.6
print(result.coverage)       # "covered" — always
```

---

### Scenario 2: Drop-in swap in run_episode

```python
from aatf.episode import run_episode
from aatf.ml_defence import MLAnomalyDefence
from aatf.context_vector import build_context_vector
from aatf.action_library import REGISTRY

ml_defence = MLAnomalyDefence(seed=42)
state = build_context_vector()  # initial context

record = run_episode(
    state=state,
    selector=some_attacker,    # any AttackerSelector
    execute_fn=lambda _: None, # no-op in unit test
    defence=ml_defence,        # <-- drop-in swap
)
# record.steps[i].detected reflects MLAnomalyDefence alerts
```

No changes to `run_episode`, `metrics`, or `report` needed.

---

### Scenario 3: ROC-AUC evaluation

```python
from aatf.ml_defence import (
    ActionFeatureEncoder,
    IsolationForestDetector,
    collect_normal_baseline,
    evaluate_roc_auc,
    FEATURE_DIM,
)
from aatf.action_library import REGISTRY
from aatf.contracts import Action
from datetime import datetime, timezone

# Build normal baseline
X_normal = collect_normal_baseline(n_samples=500, seed=42)

# Train detector
detector = IsolationForestDetector(contamination=0.1, seed=42)
detector.fit(X_normal)

# Build attack vectors from registry
encoder = ActionFeatureEncoder()
X_attack = []
for action_id, action_def in REGISTRY.actions.items():
    action = Action(
        action_id=action_id,
        category=action_def.category,
        parameters=action_def.default_parameters,
        timestamp=datetime.now(timezone.utc),
    )
    X_attack.append(encoder.encode(action))

import numpy as np
X_attack_arr = np.array(X_attack)

auc = evaluate_roc_auc(detector, X_normal[:50], X_attack_arr)
print(f"ROC-AUC: {auc:.4f}")  # must be > 0.5
```

---

### Scenario 4: Custom threshold

```python
# Low threshold: alert on anything slightly unusual
defence = MLAnomalyDefence(threshold=0.4, seed=42)
result = defence.observe(benign_looking_action)
# result.alerted may be True even for mild actions

# High threshold: only alert on clearly anomalous traffic
defence = MLAnomalyDefence(threshold=0.8, seed=42)
result = defence.observe(obvious_attack_action)
# result.alerted = True only when detector is very confident
```

---

## File Locations

| File | Purpose |
|------|---------|
| `src/aatf/ml_defence.py` | All ML defence code (~120 LOC) |
| `tests/test_ml_defence.py` | 10 contract tests (C-001..C-010) |
| `requirements.in` | Add `scikit-learn>=1.4` |

## Test Command

```bash
source .venv/bin/activate
pytest tests/test_ml_defence.py -v
```

## Expected Output (after green phase)

```
tests/test_ml_defence.py::test_c001_imports PASSED
tests/test_ml_defence.py::test_c002_encode_shape PASSED
tests/test_ml_defence.py::test_c003_encode_dtype_range PASSED
tests/test_ml_defence.py::test_c004_baseline_shape PASSED
tests/test_ml_defence.py::test_c005_baseline_deterministic PASSED
tests/test_ml_defence.py::test_c006_score_before_fit_raises PASSED
tests/test_ml_defence.py::test_c007_score_after_fit_range PASSED
tests/test_ml_defence.py::test_c008_observe_returns_detection_result PASSED
tests/test_ml_defence.py::test_c009_attack_scores_higher PASSED
tests/test_ml_defence.py::test_c010_roc_auc_gt_0_5 PASSED
10 passed
```
