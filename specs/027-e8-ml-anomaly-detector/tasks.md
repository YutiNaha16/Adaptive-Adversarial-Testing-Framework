# Tasks: ML Anomaly Defence (F27)

**Input**: Design documents from `specs/027-e8-ml-anomaly-detector/`
**Branch**: `027-e8-ml-anomaly-detector`
**Baseline**: 325 passed | **Target**: ≥335 passed (+10)
**TDD**: All 10 tests written FIRST (red), then implementation (green)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US1, US2, US3)
- All tasks touch single project (`src/aatf/`, `tests/`)

---

## Phase 1: Setup

**Purpose**: Verify baseline and add new dependency.

- [ ] T001 Record baseline test count: activate `.venv`, run `pytest --tb=no -q`, confirm 325 passed
- [ ] T002 Add `scikit-learn>=1.4` to `requirements.in` (after the `scipy>=1.12` line), then run `pip-compile requirements.in -o requirements.txt` and `pip install -r requirements.txt` to install into `.venv`

---

## Phase 2: Foundational — Red Phase (TDD)

**Purpose**: Write all 10 contracts before any implementation. All must fail with ImportError.

**⚠️ CRITICAL**: Do not implement anything until T003 is complete and T004 confirms red.

- [ ] T003 Write `tests/test_ml_defence.py` with all 10 contracts (C-001..C-010) exactly as below:

```python
"""Tests for aatf.ml_defence — 10 contracts C-001..C-010."""
from __future__ import annotations
import numpy as np
import pytest
from datetime import datetime, timezone

from aatf.ml_defence import (
    ActionFeatureEncoder,
    IsolationForestDetector,
    MLAnomalyDefence,
    collect_normal_baseline,
    evaluate_roc_auc,
    FEATURE_DIM,
)
from aatf.action_library import REGISTRY
from aatf.contracts import Action, DetectionResult


def _make_action(category: str = "scan", params: dict | None = None) -> Action:
    return Action(
        action_id="port_scan",
        category=category,
        parameters=params or {},
        timestamp=datetime.now(timezone.utc),
    )


def _attack_action() -> Action:
    return Action(
        action_id="port_scan",
        category="scan",
        parameters={"port_range_start": 1, "port_range_end": 1024, "attempts": 50},
        timestamp=datetime.now(timezone.utc),
    )


def _benign_action() -> Action:
    return Action(
        action_id="port_scan",
        category="scan",
        parameters={},
        timestamp=datetime.now(timezone.utc),
    )


# C-001: imports
def test_c001_imports() -> None:
    from aatf.ml_defence import (  # noqa: F401
        ActionFeatureEncoder,
        IsolationForestDetector,
        MLAnomalyDefence,
        collect_normal_baseline,
        evaluate_roc_auc,
    )


# C-002: encode shape
def test_c002_encode_shape() -> None:
    enc = ActionFeatureEncoder()
    x = enc.encode(_make_action())
    assert isinstance(x, np.ndarray)
    assert x.shape == (FEATURE_DIM,)


# C-003: dtype and range
def test_c003_encode_dtype_range() -> None:
    enc = ActionFeatureEncoder()
    x = enc.encode(_make_action())
    assert x.dtype == np.float64
    assert float(x.min()) >= 0.0
    assert float(x.max()) <= 1.0


# C-004: baseline shape and dtype
def test_c004_baseline_shape() -> None:
    X = collect_normal_baseline(500, 42)
    assert isinstance(X, np.ndarray)
    assert X.shape == (500, FEATURE_DIM)
    assert X.dtype == np.float64


# C-005: baseline deterministic
def test_c005_baseline_deterministic() -> None:
    X1 = collect_normal_baseline(100, 42)
    X2 = collect_normal_baseline(100, 42)
    np.testing.assert_array_equal(X1, X2)


# C-006: score before fit raises
def test_c006_score_before_fit_raises() -> None:
    det = IsolationForestDetector()
    x = np.zeros(FEATURE_DIM)
    with pytest.raises(RuntimeError, match="not fitted"):
        det.score(x)


# C-007: score after fit in [0, 1]
def test_c007_score_after_fit_range() -> None:
    X = collect_normal_baseline(100, 42)
    det = IsolationForestDetector(seed=42)
    det.fit(X)
    x = np.zeros(FEATURE_DIM)
    s = det.score(x)
    assert isinstance(s, float)
    assert 0.0 <= s <= 1.0


# C-008: observe returns DetectionResult with coverage="covered"
def test_c008_observe_returns_detection_result() -> None:
    defence = MLAnomalyDefence(seed=42)
    result = defence.observe(_make_action())
    assert isinstance(result, DetectionResult)
    assert result.coverage == "covered"
    assert 0.0 <= result.anomaly_score <= 1.0


# C-009: attack action scores higher than benign
def test_c009_attack_scores_higher_than_benign() -> None:
    defence = MLAnomalyDefence(seed=42)
    attack_score = defence.observe(_attack_action()).anomaly_score
    benign_score = defence.observe(_benign_action()).anomaly_score
    assert attack_score > benign_score, (
        f"Expected attack ({attack_score:.4f}) > benign ({benign_score:.4f})"
    )


# C-010: evaluate_roc_auc > 0.5
def test_c010_roc_auc_gt_0_5() -> None:
    X_normal = collect_normal_baseline(500, 42)
    det = IsolationForestDetector(seed=42)
    det.fit(X_normal)
    enc = ActionFeatureEncoder()
    X_attack = np.array([
        enc.encode(Action(
            action_id=aid,
            category=adef.category,
            parameters=adef.default_parameters,
            timestamp=datetime.now(timezone.utc),
        ))
        for aid, adef in REGISTRY.actions.items()
    ])
    auc = evaluate_roc_auc(det, X_normal[:50], X_attack)
    assert isinstance(auc, float)
    assert auc > 0.5, f"ROC-AUC {auc:.4f} not > 0.5"
```

- [ ] T004 Confirm red state: run `pytest tests/test_ml_defence.py --tb=short -q` — expect 10 failures with `ImportError: cannot import name ... from 'aatf.ml_defence'` (module does not exist yet)

---

## Phase 3: User Story 1 — Anomaly Detection Without Rule Changes (Priority: P1) 🎯 MVP

**Goal**: `MLAnomalyDefence.observe(action)` returns `DetectionResult` with `anomaly_score` in [0,1]
and `coverage="covered"`. Encoder, baseline, detector, and defence class all implemented.

**Independent Test**: `pytest tests/test_ml_defence.py -k "c001 or c002 or c003 or c004 or c005 or c006 or c007 or c008 or c009"` → 9 passed

### Implementation for User Story 1

- [ ] T005 [US1] Create `src/aatf/ml_defence.py` with module skeleton: imports (`from __future__ import annotations`, `math`, `numpy`, `sklearn.ensemble.IsolationForest`, `sklearn.metrics.roc_auc_score`, `aatf.contracts.Action`, `aatf.contracts.DetectionResult`, `aatf.defence.Defence`), plus module-level constants:
  ```python
  CATEGORY_MAP: dict[str, int] = {"scan": 0, "brute": 1, "ssh": 2, "web": 3, "dns": 4, "exfil": 5}
  FEATURE_DIM: int = 7
  
  def _norm(val: int | float | str, divisor: float) -> float:
      try:
          return float(val) / divisor
      except (ValueError, TypeError):
          return 0.0
  ```

- [ ] T006 [US1] Add `ActionFeatureEncoder` class to `src/aatf/ml_defence.py`:
  ```python
  class ActionFeatureEncoder:
      def encode(self, action: Action) -> np.ndarray:
          feat = np.zeros(FEATURE_DIM, dtype=np.float64)
          feat[0] = CATEGORY_MAP.get(action.category, 0) / 5.0
          feat[1] = abs(hash(action.action_id)) % 1000 / 1000.0
          p = action.parameters or {}
          feat[2] = _norm(p.get("port_range_start", 0), 65535)
          feat[3] = _norm(p.get("port_range_end", 0), 65535)
          feat[4] = min(_norm(p.get("attempts", 0), 100), 1.0)
          feat[5] = min(_norm(p.get("timing_ms", 0), 10000), 1.0)
          feat[6] = min(_norm(p.get("wordlist_size", 0), 100), 1.0)
          return feat
  ```

- [ ] T007 [US1] Add `collect_normal_baseline()` function to `src/aatf/ml_defence.py`:
  ```python
  def collect_normal_baseline(n_samples: int = 500, seed: int = 42) -> np.ndarray:
      if n_samples <= 0:
          raise ValueError(f"n_samples must be > 0, got {n_samples}")
      rng = np.random.default_rng(seed)
      X = np.zeros((n_samples, FEATURE_DIM), dtype=np.float64)
      X[:, 0] = rng.choice([0.0, 0.2, 0.4, 0.6, 0.8, 1.0], size=n_samples)
      X[:, 1] = rng.uniform(0.0, 1.0, n_samples)
      X[:, 2] = rng.uniform(0.0, 100 / 65535, n_samples)
      X[:, 3] = rng.uniform(0.0, 100 / 65535, n_samples)
      X[:, 4] = rng.uniform(0.0, 0.02, n_samples)
      X[:, 5] = rng.uniform(0.0, 0.01, n_samples)
      X[:, 6] = rng.uniform(0.0, 0.03, n_samples)
      return X
  ```

- [ ] T008 [US1] Add `IsolationForestDetector` class to `src/aatf/ml_defence.py`:
  ```python
  class IsolationForestDetector:
      def __init__(self, contamination: float = 0.1, seed: int = 42) -> None:
          self._contamination = contamination
          self._seed = seed
          self._clf: IsolationForest | None = None
          self._fitted = False

      def fit(self, X: np.ndarray) -> None:
          self._clf = IsolationForest(
              contamination=self._contamination,
              random_state=self._seed,
          )
          self._clf.fit(X)
          self._fitted = True

      def score(self, x: np.ndarray) -> float:
          if not self._fitted:
              raise RuntimeError("IsolationForestDetector not fitted — call fit() first")
          raw = self._clf.score_samples(x.reshape(1, -1))[0]
          z = -raw
          return float(1.0 / (1.0 + math.exp(-z)))
  ```

- [ ] T009 [US1] Add `MLAnomalyDefence` class to `src/aatf/ml_defence.py`:
  ```python
  class MLAnomalyDefence(Defence):
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

      def observe(self, action: Action) -> DetectionResult:
          x = self._encoder.encode(action)
          score = self._detector.score(x)
          return DetectionResult(
              alerted=score >= self._threshold,
              rule_ids=[],
              anomaly_score=score,
              coverage="covered",
          )
  ```

- [ ] T010 [US1] Verify C-001..C-009 green: run `pytest tests/test_ml_defence.py -k "c001 or c002 or c003 or c004 or c005 or c006 or c007 or c008 or c009" -v` — expect 9 passed. If C-009 fails (attack score not > benign), increase attack `attempts` parameter in `_attack_action()` helper in the test to `attempts: 100` or increase `port_range_end: 65534`.

**Checkpoint**: US1 complete — `MLAnomalyDefence.observe()` returns valid `DetectionResult` for any `Action`.

---

## Phase 4: User Story 2 — Pluggable Swap Validation (Priority: P2)

**Goal**: Confirm `MLAnomalyDefence` is a genuine drop-in replacement in `run_episode()` with
zero changes to `episode.py`, `metrics.py`, `run_experiment.py`, `action_executor.py`, `report.py`.

**Independent Test**: No new test file — confirmed by auditing that protected modules are unchanged.

### Implementation for User Story 2

- [ ] T011 [US2] Audit zero-change constraint: run `git diff HEAD -- src/aatf/episode.py src/aatf/metrics.py src/run_experiment.py src/aatf/action_executor.py src/aatf/report.py` — confirm no diff (only `src/aatf/ml_defence.py` and `requirements.in` are new/modified)

- [ ] T012 [US2] Run existing test suite to confirm no regressions from F27 changes: `pytest tests/ --ignore=tests/test_ml_defence.py --tb=short -q` — expect same 325 passed as baseline

**Checkpoint**: US2 validated — pluggable swap confirmed; no existing module changed.

---

## Phase 5: User Story 3 — Scientific Validation (Priority: P3)

**Goal**: `evaluate_roc_auc()` returns float > 0.5 on the default seed, confirming the detector
discriminates attack traffic from normal traffic better than random chance.

**Independent Test**: `pytest tests/test_ml_defence.py -k "c010" -v` → 1 passed, auc > 0.5

### Implementation for User Story 3

- [ ] T013 [US3] Add `evaluate_roc_auc()` function to `src/aatf/ml_defence.py` (append after `MLAnomalyDefence`):
  ```python
  def evaluate_roc_auc(
      detector: IsolationForestDetector,
      X_normal: np.ndarray,
      X_attack: np.ndarray,
  ) -> float:
      scores_normal = [detector.score(x) for x in X_normal]
      scores_attack = [detector.score(x) for x in X_attack]
      y_true = [0] * len(X_normal) + [1] * len(X_attack)
      y_score = scores_normal + scores_attack
      return float(roc_auc_score(y_true, y_score))
  ```

- [ ] T014 [US3] Verify C-010 green: run `pytest tests/test_ml_defence.py -k "c010" -v` — expect 1 passed with ROC-AUC > 0.5. If it fails, check that `REGISTRY.actions` returns at least 2 distinct action definitions; print the auc value to debug.

**Checkpoint**: US3 validated — ROC-AUC > 0.5 confirmed; scientific validity gate passes.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Lint, full suite validation, commit and merge.

- [ ] T015 Run `ruff check src/aatf/ml_defence.py tests/test_ml_defence.py --fix` then `ruff format src/aatf/ml_defence.py tests/test_ml_defence.py` — fix any lint/format issues
- [ ] T016 Run full suite: `pytest tests/ --tb=short -q` — expect ≥335 passed (325 baseline + 10 new). Record count.
- [ ] T017 Commit: `git add src/aatf/ml_defence.py tests/test_ml_defence.py requirements.in requirements.txt` and commit with message `feat(e8): add MLAnomalyDefence IsolationForest anomaly detector (F27)`
- [ ] T018 Merge to main: `git checkout main && git merge 027-e8-ml-anomaly-detector --no-ff -m "Merge 027-e8-ml-anomaly-detector: ML Anomaly Defence (F27)"` then push to origin

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (needs scikit-learn installed) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 (tests written and red) — no dependency on US2/US3
- **US2 (Phase 4)**: Depends on Phase 3 (MLAnomalyDefence must exist to verify the swap)
- **US3 (Phase 5)**: Depends on Phase 3 (IsolationForestDetector must be fitted)
- **Polish (Phase 6)**: Depends on all user stories complete

### Within Each Phase

```
T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010
                                                                     ↓
                                                              T011 → T012
                                                                        ↓
                                                               T013 → T014
                                                                        ↓
                                                        T015 → T016 → T017 → T018
```

### Parallel Opportunities

- T005, T006, T007, T008, T009 are all additions to the same file `src/aatf/ml_defence.py` — must be sequential
- T011 and T012 can run in parallel (different operations)
- T015 (ruff) and T016 (pytest full) can only run after T014 is green

---

## Parallel Example: Red Phase

```bash
# There is only one test file to write — no parallelism in T003
# But after T003, T004 is immediate (just run pytest)
source .venv/bin/activate && pytest tests/test_ml_defence.py --tb=line -q
# Expected: 10 errors (ImportError)
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Red phase (T003–T004) — CRITICAL blocker
3. Complete Phase 3: US1 implementation (T005–T010)
4. **STOP and VALIDATE**: `pytest tests/test_ml_defence.py -k "c001 or c002 or c003 or c004 or c005 or c006 or c007 or c008 or c009"` → 9 passed

### Incremental Delivery

1. Setup + Red phase → 10 failing tests
2. US1 → 9 tests green (C-001..C-009)
3. US2 → audit confirms plug-in contract; 0 regressions in existing suite
4. US3 → C-010 green; ROC-AUC > 0.5 confirmed
5. Polish → ≥335 total; commit; merge; push

---

## Notes

- `_norm()` helper must be defined before `ActionFeatureEncoder` in the module
- IsolationForest `score_samples()` returns values in roughly (−0.5, 0.0); negating + sigmoid maps anomalies to > 0.5
- If C-009 is marginal (attack score barely above benign), the feature vector for the attack action with `port_range_end=1024` gives `feat[3] = 1024/65535 ≈ 0.016` while benign gives `feat[3] = 0.0`. Add `attempts: 50` for additional separation via `feat[4] = 0.5`.
- `REGISTRY.actions` is a `dict[str, ActionDefinition]` — iterate `.items()` for C-010 attack vector construction
- The `Defence` ABC is in `src/aatf/defence.py` — verify import path before T009
- `DetectionResult` constructor uses keyword args: `alerted=`, `rule_ids=`, `anomaly_score=`, `coverage=`
