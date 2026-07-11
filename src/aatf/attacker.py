"""Attacker policy interface and baseline implementations."""

from __future__ import annotations

import itertools
import random
from abc import ABC, abstractmethod
from collections.abc import Iterator

import numpy as np

from aatf.linucb import LinUCBModel


class Attacker(ABC):
    @abstractmethod
    def choose_action(self, available: list[str], context: np.ndarray) -> str: ...

    @abstractmethod
    def observe(self, action_id: str, context: np.ndarray, reward: float) -> None: ...


class RandomAttacker(Attacker):
    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)

    def choose_action(self, available: list[str], context: np.ndarray) -> str:
        if not available:
            raise ValueError("available must be non-empty")
        return self._rng.choice(available)

    def observe(self, action_id: str, context: np.ndarray, reward: float) -> None:
        pass


class FixedScriptAttacker(Attacker):
    def __init__(self, script: list[str] | None = None) -> None:
        self._script: list[str] | None = script
        self._cycle: Iterator[str] | None = None

    def choose_action(self, available: list[str], context: np.ndarray) -> str:
        if self._cycle is None:
            if self._script is None:
                self._script = sorted(available)
            self._cycle = itertools.cycle(self._script)
        return next(self._cycle)

    def observe(self, action_id: str, context: np.ndarray, reward: float) -> None:
        pass


class LinUCBAttacker(Attacker):
    def __init__(self, model: LinUCBModel) -> None:
        self._model = model

    def choose_action(self, available: list[str], context: np.ndarray) -> str:
        return self._model.select_action(available, context)

    def observe(self, action_id: str, context: np.ndarray, reward: float) -> None:
        self._model.update(action_id, context, reward)
