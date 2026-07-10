"""Tests for context vector builder (F13) — covers C-001 through C-016."""

from __future__ import annotations

import numpy as np
import pytest

from aatf.context_vector import (
    _SORTED_ACTION_IDS,
    CONTEXT_DIM,
    ET_CATEGORIES,
    EpisodeState,
    build_context,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_T0 = 1_000_000.0  # fixed start_time for deterministic tests


def _fresh(step: int = 0) -> EpisodeState:
    return EpisodeState(
        completed_actions=set(),
        detection_history={},
        alert_history=[],
        step=step,
        start_time=_T0,
        fired_categories=set(),
    )


# ---------------------------------------------------------------------------
# US1 — Entry-Point Observation (C-001, C-002, C-003, C-004)
# ---------------------------------------------------------------------------


def test_output_shape_and_dtype():
    """C-001: build_context returns float32 array of shape (CONTEXT_DIM,)."""
    vec = build_context(_fresh(), current_time=_T0)
    assert vec.shape == (CONTEXT_DIM,)
    assert vec.dtype == np.float32


def test_context_dim_equals_50():
    """C-002: CONTEXT_DIM constant equals 50."""
    assert CONTEXT_DIM == 50


def test_build_context_is_deterministic():
    """C-003: two calls with identical inputs return bitwise-identical arrays."""
    state = _fresh()
    v1 = build_context(state, current_time=_T0)
    v2 = build_context(state, current_time=_T0)
    assert np.array_equal(v1, v2)


def test_fresh_state_all_zeros():
    """C-004: fresh EpisodeState with current_time==start_time produces all-zeros vector."""
    vec = build_context(_fresh(), current_time=_T0)
    assert np.all(vec == 0.0)


# ---------------------------------------------------------------------------
# US2 — Attack Progress & Technique History (C-005, C-006, C-007, C-008, C-009)
# ---------------------------------------------------------------------------


def test_alert_history_padding():
    """C-005: 3-entry history zero-pads left; most-recent in slot 9."""
    state = _fresh()
    state.alert_history = [True, False, True]
    vec = build_context(state, current_time=_T0)
    expected = np.array([0, 0, 0, 0, 0, 0, 0, 1, 0, 1], dtype=np.float32)
    assert np.array_equal(vec[0:10], expected)


def test_alert_history_truncation():
    """C-006: history longer than ALERT_WINDOW uses only last 10 entries."""
    state = _fresh()
    state.alert_history = [True] * 2 + [False] * 10  # 12 entries; last 10 are all False
    vec = build_context(state, current_time=_T0)
    assert np.all(vec[0:10] == 0.0)


def test_attack_progress_flag():
    """C-007: completed action sets its slot to 1.0; all others remain 0.0."""
    state = _fresh()
    state.completed_actions = {"tcp_port_scan"}
    vec = build_context(state, current_time=_T0)
    progress = vec[10:25]
    tcp_idx = _SORTED_ACTION_IDS.index("tcp_port_scan")
    assert progress[tcp_idx] == pytest.approx(1.0)
    assert progress.sum() == pytest.approx(1.0)


def test_technique_history_rate():
    """C-008: detection rate = detected_count / total_executions."""
    state = _fresh()
    state.detection_history = {"ssh_brute_force": [True, True, False]}
    vec = build_context(state, current_time=_T0)
    tech = vec[25:40]
    ssh_idx = _SORTED_ACTION_IDS.index("ssh_brute_force")
    assert abs(tech[ssh_idx] - 2 / 3) < 1e-5


def test_technique_history_no_nan_for_zero_executions():
    """C-009: never-executed action yields 0.0, not NaN."""
    state = _fresh()
    state.detection_history = {}
    vec = build_context(state, current_time=_T0)
    assert not np.any(np.isnan(vec[25:40]))
    assert np.all(vec[25:40] == 0.0)


# ---------------------------------------------------------------------------
# US3 — Alert History & Rule Category Signals (C-010, C-011, C-012, C-013, C-014, C-015, C-016)
# ---------------------------------------------------------------------------


def test_timing_step_normalisation():
    """C-010: step/MAX_STEPS clipped to [0, 1]."""
    state = _fresh(step=50)
    vec = build_context(state, current_time=_T0)
    assert abs(vec[40] - 0.5) < 1e-5

    state2 = _fresh(step=200)
    vec2 = build_context(state2, current_time=_T0)
    assert vec2[40] == pytest.approx(1.0)


def test_timing_elapsed_normalisation():
    """C-011: elapsed/MAX_EPISODE_SECONDS clipped to [0, 1]."""
    state = _fresh(step=0)
    vec = build_context(state, current_time=_T0 + 1800)
    assert abs(vec[41] - 0.5) < 1e-5


def test_rule_category_flags():
    """C-012: fired categories set correct flag positions to 1.0."""
    state = _fresh()
    state.fired_categories = {"ET SCAN", "ET DNS"}
    vec = build_context(state, current_time=_T0)
    cats = vec[42:50]
    assert cats[ET_CATEGORIES.index("ET SCAN")] == pytest.approx(1.0)
    assert cats[ET_CATEGORIES.index("ET DNS")] == pytest.approx(1.0)
    assert cats.sum() == pytest.approx(2.0)


def test_unknown_fired_category_ignored():
    """C-013: unknown category string in fired_categories is silently ignored."""
    state = _fresh()
    state.fired_categories = {"ET SCAN", "UNKNOWN_CATEGORY_XYZ"}
    vec = build_context(state, current_time=_T0)
    assert vec[42:50].sum() == pytest.approx(1.0)


def test_negative_step_raises():
    """C-014: EpisodeState with step < 0 raises ValueError."""
    with pytest.raises(ValueError, match="step must be non-negative"):
        EpisodeState(step=-1, start_time=_T0)


def test_unknown_action_id_in_completed_raises():
    """C-015: unknown action_id in completed_actions raises ValueError."""
    with pytest.raises(ValueError, match="unknown action_id"):
        EpisodeState(completed_actions={"nonexistent_xyz"}, start_time=_T0)


def test_no_nan_or_inf_in_valid_state():
    """C-016: no NaN or infinity in output for any valid EpisodeState."""
    state = EpisodeState(
        completed_actions={"tcp_port_scan", "ssh_brute_force"},
        detection_history={
            "tcp_port_scan": [False, False],
            "ssh_brute_force": [True, False, True],
        },
        alert_history=[True, False, True],
        step=5,
        start_time=_T0,
        fired_categories={"ET SCAN"},
    )
    vec = build_context(state, current_time=_T0 + 300)
    assert not np.any(np.isnan(vec))
    assert not np.any(np.isinf(vec))
