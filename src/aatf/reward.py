"""Reward function — single authoritative Phase 1 reward computation."""

from __future__ import annotations

REWARD_DETECTED = -1.0
REWARD_PROGRESS = 1.0
REWARD_STALL = -0.1


def compute_reward(detected: bool, stage_progress: bool) -> float:
    if detected:
        return REWARD_DETECTED
    if stage_progress:
        return REWARD_PROGRESS
    return REWARD_STALL
