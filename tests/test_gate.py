"""Tests for aatf.gate — 10 contracts C-001..C-010."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from aatf.gate import CriterionResult, GateResult, phase1_gate
from aatf.ground_truth import ValidationResult
from aatf.metrics import EpisodeRecord

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import run_experiment


def _make_vr(bsp: float = 0.9) -> ValidationResult:
    return ValidationResult(
        blind_spot_precision=bsp,
        true_positives=9,
        false_positives=1,
        total_reported=10,
        disabled_sid_count=5,
    )


def _make_records(n: int = 3) -> list[EpisodeRecord]:
    return [
        EpisodeRecord(
            attacker_class="RandomAttacker",
            seed=42,
            steps=[],
            total_reward=0.0,
            completed=True,
            episode_index=i,
        )
        for i in range(n)
    ]


def _write_config(tmp_path: Path, episodes: int = 2) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    cfg = tmp_path / "config.yaml"
    out = tmp_path / "out"
    cfg.write_text(
        f"episodes: {episodes}\n"
        f"seed: 42\n"
        f"output_dir: {out}\n"
        f"ruleset_path: /tmp/rules\n"
        f"detection_threshold: 0.5\n"
        f"attacker_class: RandomAttacker\n"
    )
    return cfg


def test_c001_importability():
    from aatf.gate import CriterionResult, GateResult, phase1_gate  # noqa: F401
    assert callable(phase1_gate)


def test_c002_gate_result_frozen():
    from dataclasses import FrozenInstanceError
    gr = GateResult(passed=True, criteria=(), summary="Phase 1 PASSED (0/0 criteria met)")
    with pytest.raises(FrozenInstanceError):
        gr.passed = False


def test_c003_criterion_result_frozen():
    from dataclasses import FrozenInstanceError
    cr = CriterionResult(name="test", passed=True, value=1.0, threshold=0.0)
    with pytest.raises(FrozenInstanceError):
        cr.passed = False


def test_c004_all_pass():
    result = phase1_gate(_make_records(3), _make_vr(0.9))
    assert result.passed is True
    assert all(c.passed for c in result.criteria)
    assert len(result.criteria) == 3


def test_c005_bsp_fails():
    result = phase1_gate(_make_records(3), _make_vr(0.5))
    assert result.passed is False
    bsp_criterion = next(c for c in result.criteria if c.name == "blind_spot_precision")
    assert bsp_criterion.passed is False
    assert bsp_criterion.value == pytest.approx(0.5)


def test_c006_empty_records_fails():
    result = phase1_gate([], _make_vr(0.9))
    assert result.passed is False


def test_c007_single_episode_passes_dr_rs():
    result = phase1_gate(_make_records(1), _make_vr(0.9))
    dr_criterion = next(c for c in result.criteria if c.name == "detection_rate")
    rs_criterion = next(c for c in result.criteria if c.name == "robustness_score")
    assert dr_criterion.passed is True
    assert rs_criterion.passed is True


def test_c008_summary_keywords():
    passed_result = phase1_gate(_make_records(3), _make_vr(0.9))
    assert "PASSED" in passed_result.summary

    failed_result = phase1_gate([], _make_vr(0.9))
    assert "FAILED" in failed_result.summary


def test_c009_run_experiment_stdout_contains_gate(tmp_path, capsys):
    cfg = _write_config(tmp_path)
    run_experiment.main(config_path=cfg)
    out = capsys.readouterr().out
    assert "Phase 1" in out


def test_c010_determinism():
    records = _make_records(5)
    vr = _make_vr(0.9)
    result1 = phase1_gate(records, vr)
    result2 = phase1_gate(records, vr)
    assert result1 == result2
