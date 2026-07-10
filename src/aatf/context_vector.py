"""Context vector builder — encodes EpisodeState into a fixed-length float32 observation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from aatf.action_library import REGISTRY

CONTEXT_DIM = 50
ALERT_WINDOW = 10
MAX_STEPS = 100
MAX_EPISODE_SECONDS = 3600
ET_CATEGORIES = [
    "ET SCAN",
    "ET EXPLOIT",
    "ET BRUTE_FORCE",
    "ET WEB_SPECIFIC_APPS",
    "ET DNS",
    "ET POLICY",
    "ET TROJAN",
    "ET INFO",
]

_SORTED_ACTION_IDS: list[str] = sorted(d.action_id for d in REGISTRY.list_actions())

_REGISTRY_IDS: frozenset[str] = frozenset(_SORTED_ACTION_IDS)


@dataclass
class EpisodeState:
    """Mutable snapshot of all observable episode data at one step."""

    completed_actions: set[str] = field(default_factory=set)
    detection_history: dict[str, list[bool]] = field(default_factory=dict)
    alert_history: list[bool] = field(default_factory=list)
    step: int = 0
    start_time: float = field(default_factory=time.time)
    fired_categories: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.step < 0:
            raise ValueError("step must be non-negative")
        for aid in self.completed_actions:
            if aid not in _REGISTRY_IDS:
                raise ValueError(f"unknown action_id: {aid!r}")


def _build_alert_history(alert_history: list[bool]) -> np.ndarray:
    window = alert_history[-ALERT_WINDOW:]
    padded = [0.0] * (ALERT_WINDOW - len(window)) + [1.0 if x else 0.0 for x in window]
    return np.array(padded, dtype=np.float32)


def _build_attack_progress(completed: set[str]) -> np.ndarray:
    return np.array(
        [1.0 if aid in completed else 0.0 for aid in _SORTED_ACTION_IDS],
        dtype=np.float32,
    )


def _build_technique_history(history: dict[str, list[bool]]) -> np.ndarray:
    rates = []
    for aid in _SORTED_ACTION_IDS:
        execs = history.get(aid, [])
        rate = sum(execs) / max(len(execs), 1)
        rates.append(rate)
    return np.array(rates, dtype=np.float32)


def _build_timing(step: int, start_time: float, current_time: float) -> np.ndarray:
    step_norm = min(step / MAX_STEPS, 1.0)
    elapsed_norm = min((current_time - start_time) / MAX_EPISODE_SECONDS, 1.0)
    return np.array([step_norm, elapsed_norm], dtype=np.float32)


def _build_rule_categories(fired: set[str]) -> np.ndarray:
    return np.array([1.0 if cat in fired else 0.0 for cat in ET_CATEGORIES], dtype=np.float32)


def build_context(
    episode_state: EpisodeState,
    current_time: float | None = None,
) -> np.ndarray:
    """Return a float32 array of shape (CONTEXT_DIM,) encoding the episode state."""
    if current_time is None:
        current_time = time.time()
    alert = _build_alert_history(episode_state.alert_history)
    progress = _build_attack_progress(episode_state.completed_actions)
    technique = _build_technique_history(episode_state.detection_history)
    timing = _build_timing(episode_state.step, episode_state.start_time, current_time)
    cats = _build_rule_categories(episode_state.fired_categories)
    return np.concatenate([alert, progress, technique, timing, cats]).astype(np.float32)
