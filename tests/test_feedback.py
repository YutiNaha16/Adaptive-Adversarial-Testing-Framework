"""Tests for feedback collector (F15) — covers C-001 through C-010."""

from __future__ import annotations

from aatf.context_vector import EpisodeState
from aatf.feedback import collect_feedback


def _fresh() -> EpisodeState:
    return EpisodeState()


# ---------------------------------------------------------------------------
# US1 — Episode State Recording (C-001 to C-004)
# ---------------------------------------------------------------------------


def test_alert_history_appended():
    """C-001: alert_history grows by 1 per call."""
    state = _fresh()
    collect_feedback(state, "tcp_port_scan", True)
    assert state.alert_history == [True]
    collect_feedback(state, "ssh_brute_force", False)
    assert state.alert_history == [True, False]


def test_detection_history_per_action():
    """C-002: detection_history[action_id] list grows per call."""
    state = _fresh()
    collect_feedback(state, "tcp_port_scan", True)
    assert state.detection_history["tcp_port_scan"] == [True]
    collect_feedback(state, "tcp_port_scan", False)
    assert state.detection_history["tcp_port_scan"] == [True, False]


def test_completed_actions_updated():
    """C-003: action_id added to completed_actions after call."""
    state = _fresh()
    collect_feedback(state, "tcp_port_scan", False)
    assert "tcp_port_scan" in state.completed_actions


def test_step_incremented():
    """C-004: step incremented by exactly 1 per call."""
    state = _fresh()
    assert state.step == 0
    collect_feedback(state, "tcp_port_scan", False)
    assert state.step == 1
    collect_feedback(state, "ssh_brute_force", False)
    assert state.step == 2


# ---------------------------------------------------------------------------
# US2 — Stage Progress Detection (C-005 to C-007)
# ---------------------------------------------------------------------------


def test_stage_progress_true():
    """C-005: stage_progress=True when completing entry point unlocks successors."""
    state = _fresh()
    # tcp_port_scan is an entry point with 4 successors (ftp_brute_force, http_dir_scan,
    # ssh_brute_force, ssh_user_enum) — completing it unlocks them all
    result = collect_feedback(state, "tcp_port_scan", False)
    assert result.stage_progress is True


def test_stage_progress_false_terminal():
    """C-006: stage_progress=False when completed action has no successors."""
    # Pre-populate so ftp_brute_force is already reachable; it has no outgoing edges
    state = EpisodeState(completed_actions={"tcp_port_scan"})
    result = collect_feedback(state, "ftp_brute_force", False)
    assert result.stage_progress is False


def test_detected_mirrors_alert_fired():
    """C-007: detected in FeedbackResult mirrors alert_fired input."""
    state1 = _fresh()
    r1 = collect_feedback(state1, "tcp_port_scan", True)
    assert r1.detected is True

    state2 = _fresh()
    r2 = collect_feedback(state2, "tcp_port_scan", False)
    assert r2.detected is False


# ---------------------------------------------------------------------------
# US3 — Alert Category Tracking (C-008 to C-010)
# ---------------------------------------------------------------------------


def test_category_added_on_alert():
    """C-008: category added to fired_categories when alert_fired=True and category provided."""
    state = _fresh()
    collect_feedback(state, "tcp_port_scan", True, category="ET SCAN")
    assert "ET SCAN" in state.fired_categories


def test_category_skipped_when_no_alert():
    """C-009: fired_categories unchanged when alert_fired=False."""
    state = _fresh()
    collect_feedback(state, "tcp_port_scan", False, category="ET SCAN")
    assert "ET SCAN" not in state.fired_categories


def test_category_skipped_when_none():
    """C-010: fired_categories unchanged when category=None."""
    state = _fresh()
    collect_feedback(state, "tcp_port_scan", True, category=None)
    assert len(state.fired_categories) == 0
