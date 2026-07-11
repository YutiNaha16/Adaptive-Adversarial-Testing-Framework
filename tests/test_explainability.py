"""Tests for aatf.explainability — C-001..C-012."""

from __future__ import annotations

import dataclasses

import pytest

from aatf.action_library import REGISTRY, ActionDefinition, ActionRegistry
from aatf.episode import StepRecord
from aatf.explainability import ActionExplanation, explain_evasions
from aatf.metrics import EpisodeRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _step(action_id: str, detected: bool) -> StepRecord:
    return StepRecord(action_id=action_id, detected=detected, stage_progress=0, reward=0.0)


def _ep(*steps: StepRecord) -> EpisodeRecord:
    return EpisodeRecord(
        attacker_class="test",
        seed=0,
        steps=list(steps),
        total_reward=0.0,
        completed=False,
        episode_index=0,
    )


def _reg(*defs: ActionDefinition) -> ActionRegistry:
    return ActionRegistry(list(defs))


def _defn(action_id: str, suricata_category: str, description: str = "desc") -> ActionDefinition:
    return ActionDefinition(
        action_id=action_id,
        category="test",
        description=description,
        default_parameters={"target_ip": "172.28.0.2"},
        suricata_category=suricata_category,
    )


# ---------------------------------------------------------------------------
# US1 — ActionExplanation container
# ---------------------------------------------------------------------------


def test_c001_action_explanation_field_access() -> None:
    ex = ActionExplanation(
        action_id="ssh_brute_force",
        suricata_category="ET BRUTE_FORCE",
        description="SSH brute-force probe",
        evasion_count=3,
        total_count=4,
        evasion_rate=0.75,
        remediation="tune thresholds",
        false_positive_risk="medium",
    )
    assert ex.action_id == "ssh_brute_force"
    assert ex.suricata_category == "ET BRUTE_FORCE"
    assert ex.description == "SSH brute-force probe"
    assert ex.evasion_count == 3
    assert ex.total_count == 4
    assert ex.evasion_rate == pytest.approx(0.75)
    assert ex.remediation == "tune thresholds"
    assert ex.false_positive_risk == "medium"


def test_c002_action_explanation_immutable() -> None:
    ex = ActionExplanation(
        action_id="x",
        suricata_category="ET SCAN",
        description="d",
        evasion_count=1,
        total_count=1,
        evasion_rate=1.0,
        remediation="r",
        false_positive_risk="f",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        ex.evasion_count = 99  # type: ignore[misc]


def test_c003_importable() -> None:
    assert callable(explain_evasions)
    assert isinstance(ActionExplanation, type)


# ---------------------------------------------------------------------------
# US2 — Evasion analysis
# ---------------------------------------------------------------------------


def test_c004_ranking_by_evasion_rate() -> None:
    reg = _reg(
        _defn("scan_tcp", "ET SCAN"),
        _defn("dns_recon", "ET DNS"),
    )
    records = [
        _ep(
            _step("scan_tcp", False),
            _step("scan_tcp", False),
            _step("scan_tcp", False),
            _step("scan_tcp", True),
        ),  # 3/4 → 0.75
        _ep(
            _step("dns_recon", False),
            _step("dns_recon", True),
            _step("dns_recon", True),
            _step("dns_recon", True),
        ),  # 1/4 → 0.25
    ]
    result = explain_evasions(records, reg)
    assert len(result) == 2
    assert result[0].action_id == "scan_tcp"
    assert result[1].action_id == "dns_recon"
    assert result[0].evasion_rate == pytest.approx(0.75)
    assert result[0].evasion_count == 3
    assert result[0].total_count == 4


def test_c005_tiebreak_by_action_id() -> None:
    reg = _reg(
        _defn("zzz_action", "ET SCAN"),
        _defn("aaa_action", "ET SCAN"),
    )
    records = [
        _ep(_step("zzz_action", False), _step("zzz_action", True)),  # 0.5
        _ep(_step("aaa_action", False), _step("aaa_action", True)),  # 0.5
    ]
    result = explain_evasions(records, reg)
    assert len(result) == 2
    assert result[0].action_id == "aaa_action"
    assert result[1].action_id == "zzz_action"


def test_c006_fully_detected_excluded() -> None:
    reg = _reg(_defn("scan_tcp", "ET SCAN"))
    records = [_ep(_step("scan_tcp", True), _step("scan_tcp", True))]
    assert explain_evasions(records, reg) == []


def test_c007_empty_records() -> None:
    reg = _reg()
    assert explain_evasions([], reg) == []


def test_c008_all_steps_detected() -> None:
    reg = _reg(
        _defn("scan_tcp", "ET SCAN"),
        _defn("dns_recon", "ET DNS"),
    )
    records = [
        _ep(_step("scan_tcp", True), _step("dns_recon", True)),
        _ep(_step("scan_tcp", True), _step("dns_recon", True)),
    ]
    assert explain_evasions(records, reg) == []


def test_c009_registry_lookup() -> None:
    records = [_ep(_step("ssh_brute_force", False))]
    result = explain_evasions(records, REGISTRY)
    defn = REGISTRY.get_action("ssh_brute_force")
    assert len(result) == 1
    assert result[0].suricata_category == defn.suricata_category
    assert result[0].description == defn.description


# ---------------------------------------------------------------------------
# US3 — Remediation and risk hints
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "category",
    [
        "ET SCAN",
        "ET BRUTE_FORCE",
        "ET EXPLOIT",
        "ET DNS",
        "ET POLICY",
        "ET TROJAN",
        "ET WEB_CLIENT",
        "ET WEB_SERVER",
    ],
)
def test_c010_known_category_non_empty(category: str) -> None:
    reg = _reg(_defn("act", category))
    records = [_ep(_step("act", False))]
    result = explain_evasions(records, reg)
    assert len(result) == 1
    assert len(result[0].remediation) > 0
    assert len(result[0].false_positive_risk) > 0


def test_c011_unknown_category_fallback() -> None:
    reg = _reg(_defn("custom_act", "ET CUSTOM_UNKNOWN"))
    records = [_ep(_step("custom_act", False))]
    result = explain_evasions(records, reg)
    assert len(result) == 1
    assert len(result[0].remediation) > 0
    assert len(result[0].false_positive_risk) > 0


def test_c012_same_category_identical_strings() -> None:
    reg = _reg(
        _defn("action_a", "ET SCAN"),
        _defn("action_b", "ET SCAN"),
    )
    records = [_ep(_step("action_a", False), _step("action_b", False))]
    result = explain_evasions(records, reg)
    assert len(result) == 2
    a = next(r for r in result if r.action_id == "action_a")
    b = next(r for r in result if r.action_id == "action_b")
    assert a.remediation == b.remediation
    assert a.false_positive_risk == b.false_positive_risk
