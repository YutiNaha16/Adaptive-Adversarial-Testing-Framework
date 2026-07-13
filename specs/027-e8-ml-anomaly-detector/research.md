# Research: ML Anomaly Defence (F27)

## Decision 1: Model Choice — IsolationForest vs Autoencoder

**Decision**: scikit-learn `IsolationForest`

**Rationale**:
- Works well with small feature vectors (7 dims) and few training samples (500)
- No training epochs, no hyperparameter tuning beyond `contamination` and `n_estimators`
- Fully reproducible with `random_state=seed` — identical output across machines
- `score_samples()` returns a real-valued anomaly score, easily mapped to [0,1] via sigmoid
- Already approved in constitution: "autoencoder or isolation forest (PyTorch / scikit-learn)"
- Avoids adding PyTorch as a new dependency (scikit-learn is smaller, faster, no GPU needed)

**Alternatives considered**:
- **Autoencoder (PyTorch)**: More powerful but requires epochs, GPU opt-in, much larger dependency.
  Rejected: overkill for Phase 2 initial demo; adds torch to requirements unnecessarily.
- **One-Class SVM**: Slower, less intuitive contamination control. Rejected.
- **DBSCAN / LOF**: No `score_samples` API suitable for single-sample inference. Rejected.

---

## Decision 2: Feature Vector Design

**Decision**: 7-dimensional vector — `[category_norm, action_id_hash_norm, p0..p4]`

**Confirmed categories (from REGISTRY)**:
```python
CATEGORY_MAP = {"scan": 0, "brute": 1, "ssh": 2, "web": 3, "dns": 4, "exfil": 5}
```
6 categories → max index = 5 → normalize by dividing by 5.

**Feature slots**:
- `feature[0]` = `CATEGORY_MAP[category] / 5.0` → [0, 1]
- `feature[1]` = `abs(hash(action_id)) % 1000 / 1000.0` → [0, 1)
- `feature[2]` = port_range_start / 65535 (0.0 if absent)
- `feature[3]` = port_range_end / 65535 (0.0 if absent)
- `feature[4]` = attempts / 100 capped at 1.0 (0.0 if absent)
- `feature[5]` = timing_ms / 10000 capped at 1.0 (0.0 if absent)
- `feature[6]` = wordlist_size / 100 capped at 1.0 (0.0 if absent)

**Rationale**: Captures the key distinguishing dimensions between benign (low intensity) and
attack (high intensity) traffic patterns. Port scanning = large range → high feature[3] value.
Brute force = many attempts → high feature[4] value. Pure benign traffic has small values.

---

## Decision 3: Normal Baseline Generation Strategy

**Decision**: Synthetic benign feature vectors via seeded NumPy RNG

**Normal distribution parameters** (reflect low-intensity benign traffic):
- category_norm: uniform choice over {0.0, 0.2, 0.4, 0.6, 0.8, 1.0} — all categories can appear benign
- action_id_hash_norm: uniform [0, 1)
- port_range_start_norm: uniform [0, 1/65535 × 100] ≈ very low single ports
- port_range_end_norm: uniform [0, 1/65535 × 100] ≈ narrow range
- attempts_norm: uniform [0, 2/100] = 0 to 0.02 (1-2 attempts)
- timing_ms_norm: uniform [0, 100/10000] = 0 to 0.01 (slow, patient)
- wordlist_size_norm: uniform [0, 3/100] = 0 to 0.03 (tiny wordlists)

**Rationale**: Benign traffic has small port ranges, few attempts, slow timing. Attack traffic
(from REGISTRY defaults) has port_range "1-1024" → feature[3] = 1024/65535 ≈ 0.016, but
attempts=10 → feature[4] = 0.1 vs benign 0.01. The separation is meaningful for IsolationForest.

**Attack vectors** (for ROC-AUC evaluation): Encode all 15 REGISTRY actions with their
`default_parameters`. These serve as the "attack" class in the evaluation.

---

## Decision 4: Anomaly Score Normalization

**Decision**: `sigmoid(-raw_score)` where `raw_score = clf.score_samples(x)[0]`

**Rationale**:
- IsolationForest `score_samples` returns negative values: more anomalous = more negative
- Negating gives positive-anomaly direction: more anomalous = larger positive value
- `sigmoid(z) = 1 / (1 + exp(-z))` maps ℝ → (0, 1) smoothly
- Typical `score_samples` range for IsolationForest: −0.5 (normal) to −0.1 (anomalous)
- After negation and sigmoid: normal ≈ sigmoid(−0.5) ≈ 0.38, anomalous ≈ sigmoid(0.1) ≈ 0.52+
- With `threshold=0.6`, only clearly anomalous actions alert — avoids false positives on baseline

**Note**: Exact score values will vary with `contamination` and `n_samples`. The sigmoid 
mapping is monotone, so ROC-AUC is preserved regardless of the exact scale.

---

## Decision 5: scikit-learn Version Constraint

**Decision**: `scikit-learn>=1.4` in `requirements.in`

**Rationale**:
- 1.4 introduced cleaner `set_output` API and improved `IsolationForest` stability
- 1.4 released January 2024, well-supported in Python 3.12
- No upper bound: project uses only stable IsolationForest API present since 1.0

---

## Constitution Check Results

| Principle | Status | Notes |
|-----------|--------|-------|
| I — Safety & Isolation | ✅ PASS | No network traffic emitted; pure in-memory feature encoding |
| II — Reproducibility | ✅ PASS | `random_state=seed` + `np.random.default_rng(seed)` — fully deterministic |
| III — Pluggable Defence | ✅ PASS | `MLAnomalyDefence(Defence)` — one new class, no other changes |
| IV — Scientific Validity | ✅ PASS | ROC-AUC > 0.5 required; TDD with 10 contracts |
| V — Explainability | ✅ PASS | `coverage="covered"` enables existing explainability engine to work |
| VI — Observability | ✅ PASS | `anomaly_score` in DetectionResult propagates to EpisodeRecord |
| VII — Phased Delivery | ✅ PASS | Phase 1 gate passed; E8 is authorized to proceed |

**No NON-NEGOTIABLE violations.** Plan is cleared to proceed.
