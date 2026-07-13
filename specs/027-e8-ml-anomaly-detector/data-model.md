# Data Model: ML Anomaly Defence (F27)

## Entities

### 1. ActionFeatureEncoder

**Kind**: Stateless class (no instance state)

**Constants**:
```python
CATEGORY_MAP: dict[str, int] = {
    "scan": 0, "brute": 1, "ssh": 2, "web": 3, "dns": 4, "exfil": 5
}
FEATURE_DIM: int = 7
```

**Interface**:
```python
def encode(self, action: Action) -> np.ndarray  # shape=(FEATURE_DIM,), dtype=float64
```

**Feature layout**:
| Index | Name              | Source                                  | Normalization             |
|-------|-------------------|-----------------------------------------|---------------------------|
| 0     | category_norm     | CATEGORY_MAP[action.category]           | / 5.0 → [0.0, 1.0]       |
| 1     | action_id_hash    | abs(hash(action.action_id)) % 1000      | / 1000.0 → [0.0, 1.0)    |
| 2     | port_range_start  | params.get("port_range_start", 0.0)     | / 65535 → [0.0, 1.0]     |
| 3     | port_range_end    | params.get("port_range_end", 0.0)       | / 65535 → [0.0, 1.0]     |
| 4     | attempts          | params.get("attempts", 0.0)             | / 100 capped at 1.0       |
| 5     | timing_ms         | params.get("timing_ms", 0.0)            | / 10000 capped at 1.0     |
| 6     | wordlist_size     | params.get("wordlist_size", 0.0)        | / 100 capped at 1.0       |

**Parameter parsing**: `action.parameters` is `dict[str, str | int | float]`. Numeric values are extracted directly; string values for port_range are split by "-" and first/last integers extracted (e.g., "1-1024" → 1, 1024).

**Invariants**:
- Output always has exactly `FEATURE_DIM` elements
- All output values in [0.0, 1.0]
- Same input → same output (deterministic, no randomness)
- Missing/absent parameters → 0.0

---

### 2. IsolationForestDetector

**Kind**: Stateful class — unfitted / fitted states

**State**:
```python
_clf: IsolationForest | None  # None until fit() called
_fitted: bool                  # False until fit() called
contamination: float           # constructor param, default 0.1
seed: int                      # constructor param, default 42
```

**Interface**:
```python
def fit(self, X: np.ndarray) -> None    # X shape: (n_samples, FEATURE_DIM)
def score(self, x: np.ndarray) -> float # x shape: (FEATURE_DIM,); returns [0, 1]
```

**State transitions**:
```
[unfitted] --fit(X)--> [fitted]
[unfitted] --score(x)--> RuntimeError("IsolationForestDetector not fitted")
[fitted]   --score(x)--> float in [0, 1]
```

**Score formula**:
```python
raw = self._clf.score_samples(x.reshape(1, -1))[0]
return float(1.0 / (1.0 + math.exp(raw)))  # sigmoid(-(-raw)) = sigmoid(raw) ← NOTE: raw is already negative
# Correction: sigmoid of negated raw → sigmoid(-raw):
#   raw is negative for inliers, more negative for more anomalous outliers
#   -raw is positive for anomalies → sigmoid(-raw) > 0.5 for anomalies
return float(1.0 / (1.0 + math.exp(-(-raw))))  # = sigmoid(raw) ← wait, let me think again
```

**Score formula (clarified)**:
- IsolationForest `score_samples` returns negative values
- Normal/inlier: score closer to 0 (e.g., -0.1)
- Anomaly/outlier: score more negative (e.g., -0.5)
- We want: anomaly → high output value → negate raw → positive for anomalies
- `z = -raw_score` (positive for anomalies, negative for normals)
- `sigmoid(z) = 1 / (1 + exp(-z))` → high for anomalies

```python
z = -raw  # negate: anomaly → positive, inlier → negative
return float(1.0 / (1.0 + math.exp(-z)))  # standard sigmoid
```

---

### 3. MLAnomalyDefence

**Kind**: Stateful class — implements `Defence` ABC

**State**:
```python
_encoder: ActionFeatureEncoder       # stateless
_detector: IsolationForestDetector   # fitted at __init__
_threshold: float                    # alert threshold, default 0.6
```

**Constructor**:
```python
def __init__(
    self,
    threshold: float = 0.6,
    contamination: float = 0.1,
    seed: int = 42,
    n_baseline: int = 500,
) -> None:
    self._encoder = ActionFeatureEncoder()
    X_normal = collect_normal_baseline(n_baseline, seed)
    self._detector = IsolationForestDetector(contamination, seed)
    self._detector.fit(X_normal)
    self._threshold = threshold
```

**Interface**:
```python
def observe(self, action: Action) -> DetectionResult
```

**observe() logic**:
```python
x = self._encoder.encode(action)
score = self._detector.score(x)
return DetectionResult(
    alerted=score >= self._threshold,
    rule_ids=[],
    anomaly_score=score,
    coverage="covered",
)
```

**DetectionResult fields** (from contracts.py, unchanged):
- `alerted: bool`
- `rule_ids: list[str]`
- `anomaly_score: float  # Field(ge=0.0, le=1.0)`
- `coverage: Literal["covered", "uncovered", "partial"]`

---

### 4. NormalBaseline (function, not class)

```python
def collect_normal_baseline(n_samples: int = 500, seed: int = 42) -> np.ndarray:
    # shape: (n_samples, FEATURE_DIM), dtype: float64
```

**Distribution per feature slot**:
| Feature     | Normal distribution                              | Rationale                              |
|-------------|--------------------------------------------------|----------------------------------------|
| category    | uniform choice from {0.0, 0.2, 0.4, 0.6, 0.8, 1.0} | all categories can appear benign   |
| action_hash | uniform [0.0, 1.0)                               | all actions can appear benign          |
| port_start  | uniform [0.0, 100/65535] ≈ [0.0, 0.00153]      | single ports, no scanning              |
| port_end    | uniform [0.0, 100/65535] ≈ [0.0, 0.00153]      | narrow range                           |
| attempts    | uniform [0.0, 0.02]                              | 0–2 attempts (benign auth)             |
| timing_ms   | uniform [0.0, 0.01]                              | 0–100ms (slow, patient traffic)        |
| wordlist    | uniform [0.0, 0.03]                              | tiny wordlists or none                 |

**Invariants**:
- `n_samples > 0` required (raises `ValueError` if 0)
- Same `(n_samples, seed)` → identical output on any machine
- All values in [0.0, 1.0]

---

### 5. evaluate_roc_auc (function)

```python
def evaluate_roc_auc(
    detector: IsolationForestDetector,
    X_normal: np.ndarray,
    X_attack: np.ndarray,
) -> float:
    # Returns float in [0.0, 1.0]; must be > 0.5 for default config
```

**Logic**:
- Label: 0 = normal, 1 = attack
- Score each row in X_normal and X_attack via `detector.score()`
- `sklearn.metrics.roc_auc_score(y_true, y_score)`

**Invariants**:
- Detector must be fitted (delegates check to `IsolationForestDetector.score`)
- Returns float in [0.0, 1.0]
- Raises if X_normal or X_attack is empty

---

## Module Layout

```text
src/aatf/ml_defence.py
  CATEGORY_MAP: dict[str, int]
  FEATURE_DIM: int
  ActionFeatureEncoder
    encode(action: Action) -> np.ndarray
  collect_normal_baseline(n_samples, seed) -> np.ndarray
  IsolationForestDetector
    __init__(contamination, seed)
    fit(X) -> None
    score(x) -> float
  MLAnomalyDefence(Defence)
    __init__(threshold, contamination, seed, n_baseline)
    observe(action) -> DetectionResult
  evaluate_roc_auc(detector, X_normal, X_attack) -> float
```

## Relationships

```
Action ──encode()──> np.ndarray[FEATURE_DIM]
                          │
                     IsolationForestDetector.score()
                          │
                     float in [0,1]
                          │
                     MLAnomalyDefence.observe()
                          │
                     DetectionResult (existing contract)
                          │
                     EpisodeRecord.steps[i].detected (existing)
                          │
                     metrics.detection_rate() (existing, unchanged)
```
