from __future__ import annotations

import dataclasses
import hashlib
import math
from typing import TYPE_CHECKING

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score

from aatf.contracts import Action, DetectionResult
from aatf.defence import Defence

if TYPE_CHECKING:
    from aatf.metrics import EpisodeRecord

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
        feat[1] = (
            int(hashlib.md5(action.action_id.encode(), usedforsecurity=False).hexdigest(), 16)
            % 1000
            / 1000.0
        )
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
        self._seed = seed
        self._n_baseline = n_baseline
        self._threshold = threshold
        self._contamination = contamination
        X_normal = collect_normal_baseline(n_baseline, seed)
        self._detector = IsolationForestDetector(contamination, seed)
        self._detector.fit(X_normal)
        # Known-evasive cache: feature vectors of attacks that previously evaded the detector.
        # Auto-remediation populates this; similarity boosting raises their future scores.
        self._evasive_cache: list[np.ndarray] = []

    def observe(self, action: Action) -> DetectionResult:
        x = self._encoder.encode(action)
        base_score = self._detector.score(x)
        boost = self._similarity_boost(x)
        score = min(1.0, base_score + boost)
        return DetectionResult(
            alerted=score >= self._threshold,
            rule_ids=[],
            anomaly_score=score,
            coverage="covered",
        )

    def _similarity_boost(self, feat: np.ndarray) -> float:
        """Return a score boost if feat is close to any known-evasive vector."""
        if not self._evasive_cache:
            return 0.0
        nf = np.linalg.norm(feat)
        if nf == 0:
            return 0.0
        max_sim = max(
            float(np.dot(feat, ev) / (nf * (np.linalg.norm(ev) + 1e-9)))
            for ev in self._evasive_cache
        )
        # similarity in [-1, 1]; only boost when cosine > 0.9 (very close match)
        return max(0.0, (max_sim - 0.9) * 5.0) * (1.0 - self._detector.score(feat))


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


# ---------------------------------------------------------------------------
# Novelty 2: Auto-Remediation
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class RemediationReport:
    """Result of one auto-remediation pass."""

    total_evaded: int
    gaps_closed: int
    avg_score_before: float
    avg_score_after: float
    remediated_action_ids: list[str]

    @property
    def improvement(self) -> float:
        return self.avg_score_after - self.avg_score_before


def auto_remediate(
    defence: MLAnomalyDefence,
    records: list[EpisodeRecord],
    evasion_threshold: float = 0.3,
) -> tuple[MLAnomalyDefence, RemediationReport]:
    """Identify attack vectors that evaded the ML detector and patch the defence.

    Steps:
    1. Find steps where detected=False AND anomaly_score < evasion_threshold.
       These are the true double-blind-spots: evaded Suricata AND looked normal to ML.
    2. Encode their feature vectors and add to the detector's evasive_cache.
       Future calls to observe() use cosine-similarity boosting to raise their scores.
    3. Verify improvement by re-scoring the same vectors with the updated detector.
    4. Return the patched defence and a RemediationReport.
    """
    from datetime import UTC, datetime

    from aatf.action_library import REGISTRY

    encoder = ActionFeatureEncoder()

    # Collect (action_id, feature_vector, original_score) for each evaded step
    evaded: list[tuple[str, np.ndarray, float]] = []
    for record in records:
        for step in record.steps:
            if not step.detected and step.anomaly_score < evasion_threshold:
                try:
                    action_def = REGISTRY.get_action(step.action_id)
                    action = Action(
                        action_id=step.action_id,
                        category=action_def.category,
                        parameters=action_def.default_parameters,
                        timestamp=datetime.now(UTC),
                    )
                    feat = encoder.encode(action)
                    evaded.append((step.action_id, feat, step.anomaly_score))
                except Exception:
                    pass

    if not evaded:
        return defence, RemediationReport(
            total_evaded=0,
            gaps_closed=0,
            avg_score_before=0.0,
            avg_score_after=0.0,
            remediated_action_ids=[],
        )

    # Deduplicate by action_id (keep one representative vector per action)
    seen: set[str] = set()
    unique_evaded: list[tuple[str, np.ndarray, float]] = []
    for action_id, feat, score in evaded:
        if action_id not in seen:
            seen.add(action_id)
            unique_evaded.append((action_id, feat, score))

    avg_before = float(np.mean([s for _, _, s in unique_evaded]))

    # Build a new defence with the evasive cache populated
    import copy

    new_defence = copy.copy(defence)
    new_defence._evasive_cache = list(defence._evasive_cache) + [f for _, f, _ in unique_evaded]

    # Verify: re-score the same vectors with the patched detector
    new_scores = []
    for action_id, _feat, _ in unique_evaded:
        action_def = REGISTRY.get_action(action_id)
        from datetime import UTC, datetime

        action = Action(
            action_id=action_id,
            category=action_def.category,
            parameters=action_def.default_parameters,
            timestamp=datetime.now(UTC),
        )
        result = new_defence.observe(action)
        new_scores.append(result.anomaly_score)

    avg_after = float(np.mean(new_scores))
    gaps_closed = sum(1 for s in new_scores if s >= defence._threshold)

    return new_defence, RemediationReport(
        total_evaded=len(unique_evaded),
        gaps_closed=gaps_closed,
        avg_score_before=avg_before,
        avg_score_after=avg_after,
        remediated_action_ids=sorted(seen),
    )
