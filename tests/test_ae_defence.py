"""Tests for aatf.ae_defence — 6 contracts C-001..C-006."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from aatf.ae_defence import FEATURE_DIM, AEAnomalyDefence, AutoencoderDetector
from aatf.contracts import Action, DetectionResult
from aatf.ml_defence import collect_normal_baseline


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
    from aatf.ae_defence import AEAnomalyDefence, AutoencoderDetector  # noqa: F401


# C-002: score before fit raises RuntimeError
def test_c002_score_before_fit_raises() -> None:
    det = AutoencoderDetector(seed=42)
    x = np.zeros(FEATURE_DIM)
    with pytest.raises(RuntimeError, match="not fitted"):
        det.score(x)


# C-003: score after fit returns float in [0, 1]
def test_c003_score_after_fit_range() -> None:
    X = collect_normal_baseline(100, 42)
    det = AutoencoderDetector(seed=42)
    det.fit(X)
    x = np.zeros(FEATURE_DIM)
    s = det.score(x)
    assert isinstance(s, float)
    assert 0.0 <= s <= 1.0


# C-004: observe returns DetectionResult with coverage="covered"
def test_c004_observe_returns_detection_result() -> None:
    defence = AEAnomalyDefence(seed=42)
    result = defence.observe(_make_action())
    assert isinstance(result, DetectionResult)
    assert result.coverage == "covered"
    assert 0.0 <= result.anomaly_score <= 1.0


# C-005: attack action scores higher than benign action
def test_c005_attack_scores_higher_than_benign() -> None:
    defence = AEAnomalyDefence(seed=42)
    attack_score = defence.observe(_attack_action()).anomaly_score
    benign_score = defence.observe(_benign_action()).anomaly_score
    assert attack_score > benign_score, (
        f"Expected attack ({attack_score:.4f}) > benign ({benign_score:.4f})"
    )


# C-006: AEAnomalyDefence with detector="ae" config field wires correctly
def test_c006_config_detector_ae(tmp_path) -> None:
    import yaml

    from aatf.config import load_config

    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "episodes": 1,
                "seed": 42,
                "output_dir": str(tmp_path / "out"),
                "ruleset_path": str(tmp_path),
                "detection_threshold": 0.6,
                "detector": "ae",
            }
        )
    )
    config = load_config(cfg_file)
    assert config.detector == "ae"
