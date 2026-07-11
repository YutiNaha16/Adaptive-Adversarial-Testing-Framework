"""Tests for aatf.ground_truth — 12 contracts C-001..C-012."""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from aatf.explainability import ActionExplanation
from aatf.ground_truth import (
    SURICATA_SID_CATEGORIES,
    ValidationResult,
    validate_blind_spots,
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
        "ET SCAN", "ET BRUTE_FORCE", "ET EXPLOIT", "ET DNS",
        "ET POLICY", "ET TROJAN", "ET WEB_CLIENT", "ET WEB_SERVER",
    }
    assert required <= set(SURICATA_SID_CATEGORIES.values())
