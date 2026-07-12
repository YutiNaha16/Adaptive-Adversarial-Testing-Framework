"""Tests for aatf.report — generate_report function (F24). Contracts C-001..C-010."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from aatf.action_library import ActionDefinition, ActionRegistry
from aatf.episode import StepRecord
from aatf.metrics import EpisodeRecord
from aatf.report import generate_report

FIXED_TS = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)


def _step(action_id: str, detected: bool) -> StepRecord:
    return StepRecord(action_id=action_id, detected=detected, stage_progress=0, reward=0.0)


def _ep(
    attacker_class: str, seed: int, *steps: StepRecord, total_reward: float = 0.0
) -> EpisodeRecord:
    return EpisodeRecord(
        attacker_class=attacker_class,
        seed=seed,
        steps=list(steps),
        total_reward=total_reward,
        completed=False,
        episode_index=0,
    )


def _defn(action_id: str, suricata_category: str) -> ActionDefinition:
    return ActionDefinition(
        action_id=action_id,
        category="test",
        description="test desc",
        default_parameters={},
        suricata_category=suricata_category,
    )


def _reg(*defs: ActionDefinition) -> ActionRegistry:
    return ActionRegistry(list(defs))


# ---------------------------------------------------------------------------
# US1 — Core generation (C-001..C-004)
# ---------------------------------------------------------------------------


def test_c001_importable() -> None:
    assert callable(generate_report)


def test_c002_returns_string_and_writes_file(tmp_path: pytest.TempPathFactory) -> None:
    reg = _reg(
        _defn("ssh_brute_force", "ET BRUTE_FORCE"),
        _defn("tcp_port_scan", "ET SCAN"),
    )
    ep = _ep("LinUCB", 0, _step("ssh_brute_force", False), _step("tcp_port_scan", True))
    out = tmp_path / "report.md"
    result = generate_report([ep], reg, out, generated_at=FIXED_TS)
    assert isinstance(result, str)
    assert len(result) > 0
    assert out.read_text(encoding="utf-8") == result


def test_c003_determinism(tmp_path: pytest.TempPathFactory) -> None:
    reg = _reg(_defn("ssh_brute_force", "ET BRUTE_FORCE"))
    ep = _ep("LinUCB", 0, _step("ssh_brute_force", False))
    r1 = generate_report([ep], reg, tmp_path / "r1.md", generated_at=FIXED_TS)
    r2 = generate_report([ep], reg, tmp_path / "r2.md", generated_at=FIXED_TS)
    assert r1 == r2


def test_c004_empty_records(tmp_path: pytest.TempPathFactory) -> None:
    reg = _reg()
    result = generate_report([], reg, tmp_path / "report.md", generated_at=FIXED_TS)
    assert len(result) > 0
    assert "0" in result


# ---------------------------------------------------------------------------
# US2 — Headline metrics (C-005..C-006)
# ---------------------------------------------------------------------------


def test_c005_detection_rate_in_report(tmp_path: pytest.TempPathFactory) -> None:
    reg = _reg(
        _defn("tcp_port_scan", "ET SCAN"),
        _defn("ssh_brute_force", "ET BRUTE_FORCE"),
    )
    ep = _ep("LinUCB", 0, _step("tcp_port_scan", True), _step("ssh_brute_force", False))
    result = generate_report([ep], reg, tmp_path / "report.md", generated_at=FIXED_TS)
    assert "50.0%" in result


def test_c006_mean_reward_in_report(tmp_path: pytest.TempPathFactory) -> None:
    reg = _reg(_defn("ssh_brute_force", "ET BRUTE_FORCE"))
    ep1 = _ep("LinUCB", 0, _step("ssh_brute_force", False), total_reward=1.0)
    ep2 = _ep("LinUCB", 1, _step("ssh_brute_force", False), total_reward=-1.0)
    result = generate_report([ep1, ep2], reg, tmp_path / "report.md", generated_at=FIXED_TS)
    assert "0.0000" in result


# ---------------------------------------------------------------------------
# US3 — Blind-spots table (C-007..C-008)
# ---------------------------------------------------------------------------


def test_c007_blind_spots_ranked(tmp_path: pytest.TempPathFactory) -> None:
    reg = _reg(_defn("action_a", "ET SCAN"), _defn("action_b", "ET SCAN"))
    # action_a: 3/4 evaded (0.75), action_b: 1/4 evaded (0.25)
    eps = [
        _ep(
            "LinUCB",
            0,
            _step("action_a", False),
            _step("action_a", False),
            _step("action_a", False),
            _step("action_a", True),
            _step("action_b", False),
            _step("action_b", True),
            _step("action_b", True),
            _step("action_b", True),
        )
    ]
    result = generate_report(eps, reg, tmp_path / "report.md", generated_at=FIXED_TS)
    assert result.index("action_a") < result.index("action_b")


def test_c008_no_blind_spots_message(tmp_path: pytest.TempPathFactory) -> None:
    reg = _reg(_defn("tcp_port_scan", "ET SCAN"))
    ep = _ep("LinUCB", 0, _step("tcp_port_scan", True), _step("tcp_port_scan", True))
    result = generate_report([ep], reg, tmp_path / "report.md", generated_at=FIXED_TS)
    assert "No blind spots detected" in result


# ---------------------------------------------------------------------------
# US4 — Run metadata and footer (C-009..C-010)
# ---------------------------------------------------------------------------


def test_c009_metadata_fields(tmp_path: pytest.TempPathFactory) -> None:
    reg = _reg(_defn("tcp_port_scan", "ET SCAN"))
    ep1 = _ep("LinUCBAttacker", 42, _step("tcp_port_scan", True))
    ep2 = _ep("LinUCBAttacker", 99, _step("tcp_port_scan", True))
    result = generate_report([ep1, ep2], reg, tmp_path / "report.md", generated_at=FIXED_TS)
    assert "LinUCBAttacker" in result
    assert "42" in result
    assert "99" in result
    assert "2024-01-01" in result


def test_c010_missing_parent_raises() -> None:
    reg = _reg()
    with pytest.raises(FileNotFoundError):
        generate_report([], reg, "/nonexistent_dir_xyz/report.md", generated_at=FIXED_TS)
