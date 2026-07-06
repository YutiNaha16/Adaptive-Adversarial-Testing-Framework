from __future__ import annotations

from abc import ABC, abstractmethod

from aatf.contracts import Action, DetectionResult


class DefenceError(Exception):
    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class Defence(ABC):
    @abstractmethod
    def observe(self, action: Action) -> DetectionResult: ...


class NullDefence(Defence):
    def observe(self, action: Action) -> DetectionResult:
        return DetectionResult(
            alerted=False,
            rule_ids=[],
            anomaly_score=0.0,
            coverage="unknown",
        )
