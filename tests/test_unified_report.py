"""Test contracts C-001..C-005: F29 unified ML blind-spot report."""

from __future__ import annotations

from pathlib import Path

from aatf.action_library import REGISTRY
from aatf.episode import StepRecord
from aatf.metrics import EpisodeRecord
from aatf.report import generate_report


def _ep(
    steps: list[StepRecord], attacker_class: str = "DQNAttacker", seed: int = 42
) -> EpisodeRecord:
    return EpisodeRecord(
        attacker_class=attacker_class,
        seed=seed,
        total_reward=sum(s.reward for s in steps),
        steps=steps,
        completed=True,
        episode_index=0,
    )


# --- C-001 -------------------------------------------------------------------


def test_c001_no_ml_section_when_all_anomaly_scores_zero(tmp_path: Path) -> None:
    step = StepRecord(action_id="tcp_port_scan", detected=False, stage_progress=0, reward=1.0)
    rendered = generate_report([_ep([step])], REGISTRY, tmp_path / "report.md")
    assert "ML Anomaly Defence Analysis" not in rendered


# --- C-002 -------------------------------------------------------------------


def test_c002_ml_section_appears_and_shows_cae(tmp_path: Path) -> None:
    step = StepRecord(
        action_id="tcp_port_scan", detected=False, stage_progress=0, reward=1.0, anomaly_score=0.5
    )
    rendered = generate_report([_ep([step])], REGISTRY, tmp_path / "report.md")
    assert "ML Anomaly Defence Analysis" in rendered
    # CAE = mean-of-episode-sums = 0.5 / 1 episode = 0.5000
    assert "0.5000" in rendered


# --- C-003 -------------------------------------------------------------------


def test_c003_evasive_table_ranks_ascending_by_undetected_anomaly(tmp_path: Path) -> None:
    # tcp_port_scan undetected anomaly 0.1 < udp_sweep undetected anomaly 0.4
    # → tcp_port_scan must appear first in the "Most Evasive Actions" table
    steps = [
        StepRecord(
            action_id="tcp_port_scan",
            detected=False,
            stage_progress=0,
            reward=1.0,
            anomaly_score=0.1,
        ),
        StepRecord(
            action_id="udp_sweep", detected=False, stage_progress=0, reward=1.0, anomaly_score=0.4
        ),
    ]
    rendered = generate_report([_ep(steps)], REGISTRY, tmp_path / "report.md")
    assert "Most Evasive Actions" in rendered
    evasive_section = rendered.split("Most Evasive Actions")[1].split("Most Suspicious Actions")[0]
    assert evasive_section.index("tcp_port_scan") < evasive_section.index("udp_sweep")


# --- C-004 -------------------------------------------------------------------


def test_c004_suspicious_table_ranks_descending_by_overall_anomaly(tmp_path: Path) -> None:
    # tcp_port_scan overall anomaly 0.9 > udp_sweep overall anomaly 0.2
    # → tcp_port_scan must appear first in the "Most Suspicious Actions" table
    # Both detected=True so evasive table is empty; only suspicious table shows them.
    steps = [
        StepRecord(
            action_id="tcp_port_scan",
            detected=True,
            stage_progress=0,
            reward=-1.0,
            anomaly_score=0.9,
        ),
        StepRecord(
            action_id="udp_sweep", detected=True, stage_progress=0, reward=-1.0, anomaly_score=0.2
        ),
    ]
    rendered = generate_report([_ep(steps)], REGISTRY, tmp_path / "report.md")
    assert "Most Suspicious Actions" in rendered
    suspicious_section = rendered.split("Most Suspicious Actions")[1].split(
        "Retraining Recommendation"
    )[0]
    assert suspicious_section.index("tcp_port_scan") < suspicious_section.index("udp_sweep")


# --- C-005 -------------------------------------------------------------------


def test_c005_retrain_categories_and_no_gap_message(tmp_path: Path) -> None:
    # Below threshold (0.25 < 0.3): tcp_port_scan's category "ET SCAN" must appear
    # in the Retraining Recommendation section.
    step_low = StepRecord(
        action_id="tcp_port_scan", detected=False, stage_progress=0, reward=1.0, anomaly_score=0.25
    )
    rendered_low = generate_report([_ep([step_low])], REGISTRY, tmp_path / "low.md")
    recommendation_section = rendered_low.split("Retraining Recommendation")[1]
    assert "ET SCAN" in recommendation_section

    # Above threshold (0.7 > 0.3): retrain_categories is empty → no-gap message shown.
    step_high = StepRecord(
        action_id="tcp_port_scan", detected=False, stage_progress=0, reward=1.0, anomaly_score=0.7
    )
    rendered_high = generate_report([_ep([step_high])], REGISTRY, tmp_path / "high.md")
    assert "No ML gap identified" in rendered_high
