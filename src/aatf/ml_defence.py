from __future__ import annotations

import math

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score

from aatf.contracts import Action, DetectionResult
from aatf.defence import Defence

CATEGORY_MAP: dict[str, int] = {
    "scan": 0,
    "brute": 1,
    "ssh": 2,
    "web": 3,
    "dns": 4,
    "exfil": 5,
}
FEATURE_DIM: int = 7


def _norm(val: int | float | str, divisor: float) -> float:
    try:
        return float(val) / divisor
    except (ValueError, TypeError):
        return 0.0


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
        raw = self._clf.score_samples(x.reshape(1, -1))[0]  # type: ignore[union-attr]
        z = -raw  # negate: anomaly (more negative raw) → positive z → sigmoid > 0.5
        return float(1.0 / (1.0 + math.exp(-z)))


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
