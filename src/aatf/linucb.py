"""LinUCB contextual-bandit attacker — per-action belief update and UCB selection."""

from __future__ import annotations

import math

import numpy as np


class LinUCBModel:
    def __init__(
        self,
        d: int,
        alpha: float = 1.0,
        *,
        _arms: dict[str, tuple[np.ndarray, np.ndarray]] | None = None,
    ) -> None:
        self.d = d
        self.alpha = alpha
        self._arms: dict[str, tuple[np.ndarray, np.ndarray]] = _arms if _arms is not None else {}

    def _get_or_init_arm(self, action_id: str) -> tuple[np.ndarray, np.ndarray]:
        if action_id not in self._arms:
            self._arms[action_id] = (
                np.eye(self.d, dtype=float),
                np.zeros(self.d, dtype=float),
            )
        return self._arms[action_id]

    def update(self, action_id: str, context: np.ndarray, reward: float) -> None:
        A_inv, b = self._get_or_init_arm(action_id)
        x = A_inv @ context
        A_inv = A_inv - np.outer(x, x) / (1.0 + float(context @ x))
        b = b + reward * context
        self._arms[action_id] = (A_inv, b)

    def select_action(self, available: list[str], context: np.ndarray) -> str:
        best_id = sorted(available)[0]
        best_score = float("-inf")
        for action_id in sorted(available):
            A_inv, b = self._get_or_init_arm(action_id)
            theta = A_inv @ b
            score = float(theta @ context) + self.alpha * math.sqrt(
                max(0.0, float(context @ A_inv @ context))
            )
            if score > best_score:
                best_score = score
                best_id = action_id
        return best_id

    def to_dict(self) -> dict:
        return {
            "d": self.d,
            "alpha": self.alpha,
            "arms": {
                action_id: {
                    "A_inv": A_inv.tolist(),
                    "b": b.tolist(),
                }
                for action_id, (A_inv, b) in self._arms.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> LinUCBModel:
        arms = {
            action_id: (
                np.array(arm["A_inv"], dtype=float),
                np.array(arm["b"], dtype=float),
            )
            for action_id, arm in data.get("arms", {}).items()
        }
        return cls(d=data["d"], alpha=data["alpha"], _arms=arms)
