from __future__ import annotations

from aatf.episode import StepRecord
from aatf.metrics import (
    EpisodeRecord,
    adaptation_gain,
    convergence_episodes,
    detection_rate,
    robustness_score,
)


def _step(detected: bool, stage_progress: bool = False, reward: float = 0.0) -> StepRecord:
    return StepRecord(
        action_id="scan", detected=detected, stage_progress=stage_progress, reward=reward
    )


def _ep(episode_index: int, steps: list[StepRecord], *, completed: bool = True) -> EpisodeRecord:
    return EpisodeRecord(
        attacker_class="TestAttacker",
        seed=0,
        steps=steps,
        total_reward=sum(s.reward for s in steps),
        completed=completed,
        episode_index=episode_index,
    )


# --- US1: EpisodeRecord ---


def test_c001_episode_record_construction() -> None:
    steps = [_step(True), _step(False)]
    rec = _ep(episode_index=0, steps=steps)
    assert rec.attacker_class == "TestAttacker"
    assert rec.seed == 0
    assert rec.steps == steps
    assert rec.completed is True
    assert rec.episode_index == 0


def test_c002_episode_record_incomplete() -> None:
    rec = _ep(episode_index=3, steps=[_step(True), _step(True)], completed=False)
    assert rec.completed is False
    assert rec.episode_index == 3


def test_c003_episode_record_empty_steps() -> None:
    rec = _ep(episode_index=0, steps=[])
    assert rec.steps == []
    assert rec.total_reward == 0.0


# --- US2: detection_rate ---


def test_c004_detection_rate_all_detected() -> None:
    records = [
        _ep(0, [_step(True), _step(True), _step(True)]),
        _ep(1, [_step(True), _step(True)]),
    ]
    assert detection_rate(records) == 1.0


def test_c005_detection_rate_none_detected() -> None:
    records = [
        _ep(0, [_step(False), _step(False)]),
        _ep(1, [_step(False), _step(False), _step(False)]),
    ]
    assert detection_rate(records) == 0.0


def test_c006_detection_rate_partial() -> None:
    records = [
        _ep(0, [_step(True), _step(True), _step(False)]),
        _ep(1, [_step(False), _step(False)]),
    ]
    assert abs(detection_rate(records) - 0.4) < 1e-9


def test_c007_detection_rate_empty() -> None:
    assert detection_rate([]) == 0.0


# --- US3: robustness_score ---


def test_c008_robustness_score_last_window() -> None:
    records = [_ep(i, [_step(True)]) for i in range(3)] + [
        _ep(i + 3, [_step(False)]) for i in range(3)
    ]
    assert robustness_score(records, window=3) == 0.0


def test_c009_robustness_score_window_exceeds_len() -> None:
    records = [_ep(i, [_step(True)]) for i in range(3)]
    assert robustness_score(records, window=20) == 1.0


def test_c010_robustness_score_empty() -> None:
    assert robustness_score([], window=5) == 0.0


# --- US3: adaptation_gain ---


def test_c011_adaptation_gain_positive() -> None:
    baseline = [
        _ep(0, [_step(True), _step(True), _step(True), _step(True), _step(False)]),
        _ep(1, [_step(True), _step(True), _step(True), _step(True), _step(False)]),
    ]
    learner = [
        _ep(0, [_step(True), _step(True), _step(False), _step(False), _step(False)]),
        _ep(1, [_step(True), _step(True), _step(True), _step(False), _step(False)]),
    ]
    assert abs(adaptation_gain(baseline, learner) - 30.0) < 1e-9


def test_c012_adaptation_gain_zero() -> None:
    records = [_ep(i, [_step(True), _step(False)]) for i in range(3)]
    assert adaptation_gain(records, records) == 0.0


def test_c013_adaptation_gain_negative() -> None:
    baseline = [
        _ep(0, [_step(True), _step(False), _step(False), _step(False), _step(False)]),
        _ep(1, [_step(True), _step(True), _step(False), _step(False), _step(False)]),
    ]
    learner = [
        _ep(0, [_step(True), _step(True), _step(True), _step(False), _step(False)]),
        _ep(1, [_step(True), _step(True), _step(True), _step(False), _step(False)]),
    ]
    assert abs(adaptation_gain(baseline, learner) - (-30.0)) < 1e-9


# --- US4: convergence_episodes ---


def test_c014_convergence_at_known_episode() -> None:
    records = [_ep(i, [_step(True)]) for i in range(2)] + [
        _ep(i + 2, [_step(False)]) for i in range(3)
    ]
    # i=3: records[1:4] = [T, F, F] → dr=1/3 < 0.5 → return records[3].episode_index = 3
    assert convergence_episodes(records, threshold=0.5, window=3) == 3


def test_c015_no_convergence() -> None:
    records = [_ep(i, [_step(True)]) for i in range(5)]
    assert convergence_episodes(records, threshold=0.5) is None


def test_c016_immediate_convergence() -> None:
    records = [_ep(0, [_step(False)]), _ep(1, [_step(False)])]
    assert convergence_episodes(records, threshold=0.5, window=1) == 0


def test_c017_convergence_empty_records() -> None:
    assert convergence_episodes([]) is None
