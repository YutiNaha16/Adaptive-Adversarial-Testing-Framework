"""Feedback collector — updates EpisodeState in-place and returns FeedbackResult."""

from __future__ import annotations

from dataclasses import dataclass

from aatf.attack_graph import ATTACK_GRAPH, AttackGraph
from aatf.context_vector import EpisodeState


@dataclass(frozen=True)
class FeedbackResult:
    detected: bool
    stage_progress: bool


def collect_feedback(
    episode_state: EpisodeState,
    action_id: str,
    alert_fired: bool,
    *,
    attack_graph: AttackGraph = ATTACK_GRAPH,
    category: str | None = None,
) -> FeedbackResult:
    before_actions = set(attack_graph.available_actions(episode_state.completed_actions))
    episode_state.alert_history.append(alert_fired)
    episode_state.detection_history.setdefault(action_id, []).append(alert_fired)
    episode_state.completed_actions.add(action_id)
    episode_state.step += 1
    if alert_fired and category is not None:
        episode_state.fired_categories.add(category)
    after_actions = set(attack_graph.available_actions(episode_state.completed_actions))
    stage_progress = bool(after_actions - before_actions)
    return FeedbackResult(detected=alert_fired, stage_progress=stage_progress)
