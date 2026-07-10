"""Tests for reward function (F14) — covers C-001 through C-006."""

from __future__ import annotations

from aatf.reward import REWARD_DETECTED, REWARD_PROGRESS, REWARD_STALL, compute_reward

# ---------------------------------------------------------------------------
# US1 — Detection Penalty (C-001, C-002)
# ---------------------------------------------------------------------------


def test_detected_no_progress():
    """C-001: detected=True, stage_progress=False → REWARD_DETECTED (-1.0)."""
    assert compute_reward(detected=True, stage_progress=False) == REWARD_DETECTED
    assert compute_reward(detected=True, stage_progress=False) == -1.0


def test_detected_with_progress():
    """C-002: detected=True, stage_progress=True → REWARD_DETECTED (-1.0); detection wins."""
    assert compute_reward(detected=True, stage_progress=True) == REWARD_DETECTED
    assert compute_reward(detected=True, stage_progress=True) == -1.0


# ---------------------------------------------------------------------------
# US2 — Progress Reward (C-003)
# ---------------------------------------------------------------------------


def test_undetected_with_progress():
    """C-003: detected=False, stage_progress=True → REWARD_PROGRESS (+1.0)."""
    assert compute_reward(detected=False, stage_progress=True) == REWARD_PROGRESS
    assert compute_reward(detected=False, stage_progress=True) == 1.0


# ---------------------------------------------------------------------------
# US3 — No-Progress Penalty + Constants (C-004, C-005, C-006)
# ---------------------------------------------------------------------------


def test_undetected_no_progress():
    """C-004: detected=False, stage_progress=False → REWARD_STALL (-0.1)."""
    assert compute_reward(detected=False, stage_progress=False) == REWARD_STALL
    assert abs(compute_reward(detected=False, stage_progress=False) - (-0.1)) < 1e-9


def test_return_type_is_float():
    """C-005: compute_reward returns Python float."""
    assert isinstance(compute_reward(detected=False, stage_progress=True), float)


def test_named_constants():
    """C-006: named constants have correct values."""
    assert REWARD_DETECTED == -1.0
    assert REWARD_PROGRESS == 1.0
    assert abs(REWARD_STALL - (-0.1)) < 1e-9
