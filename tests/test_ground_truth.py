"""Tests for aatf.ground_truth — 12 contracts C-001..C-012."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from aatf.action_library import REGISTRY
from aatf.episode import StepRecord
from aatf.explainability import ActionExplanation
from aatf.ground_truth import (
    SURICATA_SID_CATEGORIES,
    ValidationResult,
    explain_double_blind_spots,
    validate_blind_spots,
)
from aatf.metrics import EpisodeRecord


def _step(action_id: str, detected: bool, anomaly_score: float = 0.0) -> StepRecord:
    return StepRecord(
        action_id=action_id,
        detected=detected,
        stage_progress=0,
        reward=0.0,
        anomaly_score=anomaly_score,
    )


def _ep(*steps: StepRecord) -> EpisodeRecord:
    return EpisodeRecord(
        attacker_class="test",
        seed=0,
        steps=list(steps),
        total_reward=0.0,
        completed=False,
        episode_index=0,
    )


def _expl(action_id: str, suricata_category: str) -> ActionExplanation:
    return ActionExplanation(
        action_id=action_id,
        suricata_category=suricata_category,
        description="test",
        evasion_count=1,
        total_count=1,
        evasion_rate=1.0,
        remediation="fix it",
        false_positive_risk="low",
    )


def test_c001_importability():
    from aatf.ground_truth import (  # noqa: F401
        SURICATA_SID_CATEGORIES,
        ValidationResult,
        validate_blind_spots,
    )


def test_c002_validation_result_field_types():
    r = ValidationResult(
        blind_spot_precision=0.5,
        true_positives=1,
        false_positives=1,
        total_reported=2,
        disabled_sid_count=1,
    )
    assert isinstance(r.blind_spot_precision, float)
    assert isinstance(r.true_positives, int)
    assert isinstance(r.false_positives, int)
    assert isinstance(r.total_reported, int)
    assert isinstance(r.disabled_sid_count, int)


def test_c003_validation_result_immutable():
    r = ValidationResult(
        blind_spot_precision=0.5,
        true_positives=1,
        false_positives=1,
        total_reported=2,
        disabled_sid_count=1,
    )
    with pytest.raises((FrozenInstanceError, AttributeError)):
        r.blind_spot_precision = 0.9


def test_c004_meets_gate_true_above_threshold():
    r = ValidationResult(
        blind_spot_precision=0.85,
        true_positives=17,
        false_positives=3,
        total_reported=20,
        disabled_sid_count=5,
    )
    assert r.meets_gate is True


def test_c005_meets_gate_false_below_threshold():
    r = ValidationResult(
        blind_spot_precision=0.75,
        true_positives=3,
        false_positives=1,
        total_reported=4,
        disabled_sid_count=2,
    )
    assert r.meets_gate is False


def test_c006_meets_gate_boundary_inclusive():
    r = ValidationResult(
        blind_spot_precision=0.8,
        true_positives=4,
        false_positives=1,
        total_reported=5,
        disabled_sid_count=2,
    )
    assert r.meets_gate is True


def test_c007_both_confirmed_precision_one():
    result = validate_blind_spots(
        [_expl("a", "ET SCAN"), _expl("b", "ET BRUTE_FORCE")],
        {"2001219", "2002087"},
    )
    assert result.true_positives == 2
    assert result.false_positives == 0
    assert result.blind_spot_precision == pytest.approx(1.0)
    assert result.total_reported == 2
    assert result.disabled_sid_count == 2


def test_c008_one_confirmed_one_not():
    result = validate_blind_spots(
        [_expl("a", "ET SCAN"), _expl("b", "ET EXPLOIT")],
        {"2001219"},
    )
    assert result.true_positives == 1
    assert result.false_positives == 1
    assert result.blind_spot_precision == pytest.approx(0.5)


def test_c009_empty_explanations():
    result = validate_blind_spots([], {"2001219"})
    assert result.blind_spot_precision == 0.0
    assert result.true_positives == 0
    assert result.false_positives == 0
    assert result.total_reported == 0
    assert result.disabled_sid_count == 1


def test_c010_empty_disabled_sids():
    result = validate_blind_spots([_expl("a", "ET SCAN")], set())
    assert result.blind_spot_precision == 0.0
    assert result.true_positives == 0
    assert result.false_positives == 1
    assert result.disabled_sid_count == 0


def test_c011_unknown_sid_ignored():
    result = validate_blind_spots([_expl("a", "ET SCAN")], {"9999999"})
    assert result.true_positives == 0
    assert result.false_positives == 1
    assert result.blind_spot_precision == 0.0


def test_c012_sid_categories_covers_all_phase1():
    required = {
        "ET SCAN",
        "ET BRUTE_FORCE",
        "ET EXPLOIT",
        "ET DNS",
        "ET POLICY",
        "ET TROJAN",
        "ET WEB_CLIENT",
        "ET WEB_SERVER",
    }
    assert required <= set(SURICATA_SID_CATEGORIES.values())


def test_c013_meets_gate_vacuous_pass_when_nothing_reported():
    r = ValidationResult(
        blind_spot_precision=0.0,
        true_positives=0,
        false_positives=0,
        total_reported=0,
        disabled_sid_count=3,
    )
    assert r.meets_gate is True


def test_c014_meets_gate_still_fails_with_reported_false_claims():
    r = ValidationResult(
        blind_spot_precision=0.5,
        true_positives=1,
        false_positives=1,
        total_reported=2,
        disabled_sid_count=1,
    )
    assert r.meets_gate is False


def test_c015_explain_double_blind_spots_excludes_detected_steps():
    action_id = REGISTRY.list_actions()[0].action_id
    records = [_ep(_step(action_id, detected=True, anomaly_score=0.0))]
    assert explain_double_blind_spots(records, REGISTRY) == []


def test_c016_explain_double_blind_spots_excludes_high_anomaly_evasions():
    action_id = REGISTRY.list_actions()[0].action_id
    records = [_ep(_step(action_id, detected=False, anomaly_score=0.61))]
    assert explain_double_blind_spots(records, REGISTRY) == []


def test_c017_explain_double_blind_spots_includes_true_dbs():
    action_id = REGISTRY.list_actions()[0].action_id
    records = [_ep(_step(action_id, detected=False, anomaly_score=0.1))]
    result = explain_double_blind_spots(records, REGISTRY)
    assert len(result) == 1
    assert result[0].action_id == action_id
    assert result[0].evasion_count == 1
    assert result[0].total_count == 1


def test_c018_explain_double_blind_spots_mixed_steps_only_counts_dbs():
    action_id = REGISTRY.list_actions()[0].action_id
    records = [
        _ep(
            _step(action_id, detected=False, anomaly_score=0.1),  # true DBS
            _step(action_id, detected=True, anomaly_score=0.0),  # detected, not DBS
            _step(action_id, detected=False, anomaly_score=0.9),  # evaded but high anomaly
        )
    ]
    result = explain_double_blind_spots(records, REGISTRY)
    assert len(result) == 1
    assert result[0].evasion_count == 1
    assert result[0].total_count == 1


def test_c019_ground_truth_uses_dbs_not_raw_evasions_end_to_end():
    """Regression test for the BSP/DBS mismatch: an action that evades Suricata
    with a high anomaly score (not a true double blind spot) must not count
    toward blind-spot-precision validation."""
    action_id = REGISTRY.list_actions()[0].action_id
    records = [_ep(_step(action_id, detected=False, anomaly_score=0.9))]
    explanations = explain_double_blind_spots(records, REGISTRY)
    result = validate_blind_spots(explanations, {"2001219"})
    assert result.total_reported == 0
    assert result.blind_spot_precision == 0.0
    assert result.meets_gate is True
