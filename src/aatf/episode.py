"""Episode loop — orchestrates a single attack episode end-to-end."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from aatf.action_library import REGISTRY
from aatf.attack_graph import ATTACK_GRAPH, AttackGraph
from aatf.context_vector import MAX_STEPS, EpisodeState
from aatf.contracts import Action
from aatf.defence import Defence
from aatf.feedback import collect_feedback
from aatf.reward import compute_reward


@dataclass(frozen=True)
class StepRecord:
    action_id: str
    detected: bool
    stage_progress: bool
    reward: float
    anomaly_score: float = 0.0


@dataclass(frozen=True)
class EpisodeResult:
    episode_state: EpisodeState
    steps: list[StepRecord]
    total_reward: float
    completed: bool


def run_episode(
    episode_state: EpisodeState,
    action_selector: Callable[[list[str], EpisodeState], str],
    execute_fn: Callable[[str], None],
    defence: Defence,
    *,
    attack_graph: AttackGraph = ATTACK_GRAPH,
    max_steps: int = MAX_STEPS,
) -> EpisodeResult:
    steps: list[StepRecord] = []
    total_reward = 0.0

    while True:
        reachable = attack_graph.available_actions(episode_state.completed_actions)
        available = [a for a in reachable if a not in episode_state.completed_actions]

        # FR-003: no-actions check BEFORE step-limit check
        if not available:
            return EpisodeResult(
                episode_state=episode_state,
                steps=steps,
                total_reward=total_reward,
                completed=True,
            )
        if episode_state.step >= max_steps:
            return EpisodeResult(
                episode_state=episode_state,
                steps=steps,
                total_reward=total_reward,
                completed=False,
            )

        action_id = action_selector(available, episode_state)
        execute_fn(action_id)

        action_def = REGISTRY.get_action(action_id)
        action = Action(
            action_id=action_id,
            category=action_def.category,
            parameters=action_def.default_parameters,
            timestamp=datetime.now(UTC),
        )
        detection = defence.observe(action)
        alert_fired = detection.alerted
        category = action_def.suricata_category if alert_fired else None

        result = collect_feedback(
            episode_state,
            action_id,
            alert_fired,
            attack_graph=attack_graph,
            category=category,
        )
        reward = compute_reward(result.detected, result.stage_progress)
        steps.append(
            StepRecord(
                action_id=action_id,
                detected=result.detected,
                stage_progress=result.stage_progress,
                reward=reward,
                anomaly_score=detection.anomaly_score,
            )
        )
        total_reward += reward
