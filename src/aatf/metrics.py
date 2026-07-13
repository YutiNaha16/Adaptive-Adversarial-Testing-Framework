"""Offline evaluator — Phase 1 headline metrics."""

from __future__ import annotations

from dataclasses import dataclass

from aatf.episode import StepRecord


@dataclass(frozen=True)
class EpisodeRecord:
    attacker_class: str
    seed: int
    steps: list[StepRecord]
    total_reward: float
    completed: bool
    episode_index: int


def detection_rate(records: list[EpisodeRecord]) -> float:
    total = sum(len(r.steps) for r in records)
    if total == 0:
        return 0.0
    detected = sum(1 for r in records for s in r.steps if s.detected)
    return detected / total


def robustness_score(records: list[EpisodeRecord], window: int) -> float:
    if window <= 0:
        return 0.0
    return detection_rate(records[-window:])


def adaptation_gain(
    baseline_records: list[EpisodeRecord],
    learner_records: list[EpisodeRecord],
) -> float:
    return (detection_rate(baseline_records) - detection_rate(learner_records)) * 100.0


def convergence_episodes(
    records: list[EpisodeRecord],
    threshold: float = 0.5,
    *,
    window: int = 5,
) -> int | None:
    for i, record in enumerate(records):
        start = max(0, i - window + 1)
        if detection_rate(records[start : i + 1]) < threshold:
            return record.episode_index
    return None


def cumulative_anomaly_exposure(records: list[EpisodeRecord]) -> float:
    if not records:
        return 0.0
    return sum(sum(s.anomaly_score for s in r.steps) for r in records) / len(records)
