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


class CompositeDefence(Defence):
    """Merges two defences: primary controls alerted/rule_ids; secondary provides anomaly_score."""

    def __init__(self, primary: Defence, secondary: Defence) -> None:
        self._primary = primary
        self._secondary = secondary

    def observe(self, action: Action) -> DetectionResult:
        p = self._primary.observe(action)
        s = self._secondary.observe(action)
        return DetectionResult(
            alerted=p.alerted,
            rule_ids=p.rule_ids,
            anomaly_score=s.anomaly_score,
            coverage=p.coverage,
        )
