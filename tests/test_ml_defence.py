"""Tests for aatf.ml_defence — 10 contracts C-001..C-010."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from aatf.action_library import REGISTRY
from aatf.contracts import Action, DetectionResult
from aatf.ml_defence import (
    FEATURE_DIM,
    ActionFeatureEncoder,
    IsolationForestDetector,
    MLAnomalyDefence,
    collect_normal_baseline,
    evaluate_roc_auc,
)


def _make_action(category: str = "scan", params: dict | None = None) -> Action:
    return Action(
        action_id="port_scan",
        category=category,
        parameters=params or {},
        timestamp=datetime.now(UTC),
    )


def _attack_action() -> Action:
    return _make_action(
        category="scan",
        params={"port_range_start": 1, "port_range_end": 1024, "attempts": 50},
    )


def _benign_action() -> Action:
    return _make_action(category="scan", params={})


# C-001: imports work
def test_c001_imports() -> None:
    from aatf.ml_defence import (  # noqa: F401
        ActionFeatureEncoder,
        IsolationForestDetector,
        MLAnomalyDefence,
        collect_normal_baseline,
        evaluate_roc_auc,
    )


# C-002: encode returns ndarray of shape (FEATURE_DIM,)
def test_c002_encode_shape() -> None:
    enc = ActionFeatureEncoder()
    x = enc.encode(_make_action())
    assert isinstance(x, np.ndarray)
    assert x.shape == (FEATURE_DIM,)


# C-003: dtype float64, all values in [0, 1]
def test_c003_encode_dtype_range() -> None:
    enc = ActionFeatureEncoder()
    x = enc.encode(_make_action())
    assert x.dtype == np.float64
    assert float(x.min()) >= 0.0
    assert float(x.max()) <= 1.0


# C-004: baseline shape (500, FEATURE_DIM) dtype float64
def test_c004_baseline_shape() -> None:
    X = collect_normal_baseline(500, 42)
    assert isinstance(X, np.ndarray)
    assert X.shape == (500, FEATURE_DIM)
    assert X.dtype == np.float64


# C-005: baseline deterministic with same seed
def test_c005_baseline_deterministic() -> None:
    X1 = collect_normal_baseline(100, 42)
    X2 = collect_normal_baseline(100, 42)
    np.testing.assert_array_equal(X1, X2)


# C-006: score before fit raises RuntimeError
def test_c006_score_before_fit_raises() -> None:
    det = IsolationForestDetector()
    x = np.zeros(FEATURE_DIM)
    with pytest.raises(RuntimeError, match="not fitted"):
        det.score(x)


# C-007: score after fit returns float in [0, 1]
def test_c007_score_after_fit_range() -> None:
    X = collect_normal_baseline(100, 42)
    det = IsolationForestDetector(seed=42)
    det.fit(X)
    x = np.zeros(FEATURE_DIM)
    s = det.score(x)
    assert isinstance(s, float)
    assert 0.0 <= s <= 1.0


# C-008: observe returns DetectionResult with coverage="covered", anomaly_score in [0,1]
def test_c008_observe_returns_detection_result() -> None:
    defence = MLAnomalyDefence(seed=42)
    result = defence.observe(_make_action())
    assert isinstance(result, DetectionResult)
    assert result.coverage == "covered"
    assert 0.0 <= result.anomaly_score <= 1.0


# C-009: attack action scores higher than benign action
def test_c009_attack_scores_higher_than_benign() -> None:
    defence = MLAnomalyDefence(seed=42)
    attack_score = defence.observe(_attack_action()).anomaly_score
    benign_score = defence.observe(_benign_action()).anomaly_score
    assert attack_score > benign_score, (
        f"Expected attack ({attack_score:.4f}) > benign ({benign_score:.4f})"
    )


# C-010: evaluate_roc_auc > 0.5 on normal vs all registry attack vectors
def test_c010_roc_auc_gt_0_5() -> None:
    X_normal = collect_normal_baseline(500, 42)
    det = IsolationForestDetector(seed=42)
    det.fit(X_normal)
    enc = ActionFeatureEncoder()
    now = datetime.now(UTC)
    X_attack = np.array(
        [
            enc.encode(
                Action(
                    action_id=adef.action_id,
                    category=adef.category,
                    parameters=adef.default_parameters,
                    timestamp=now,
                )
            )
            for adef in REGISTRY.list_actions()
        ]
    )
    auc = evaluate_roc_auc(det, X_normal[:50], X_attack)
    assert isinstance(auc, float)
    assert auc > 0.5, f"ROC-AUC {auc:.4f} not > 0.5"
