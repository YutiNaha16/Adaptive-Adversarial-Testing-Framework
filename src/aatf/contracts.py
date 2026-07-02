from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Action(BaseModel):
    model_config = ConfigDict(frozen=True)

    action_id: str
    category: str
    parameters: dict[str, Any]
    timestamp: datetime


class DetectionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    alerted: bool
    rule_ids: list[str]
    anomaly_score: float = Field(ge=0.0, le=1.0)
    coverage: Literal["covered", "uncovered", "unknown"]


class ContextVector(BaseModel):
    model_config = ConfigDict(frozen=True)

    alert_history: list[Annotated[float, Field(ge=0.0, le=1.0)]]
    attack_progress: float = Field(ge=0.0, le=1.0)
    current_stage: int = Field(ge=0, le=3)
    technique_detection_rates: dict[str, Annotated[float, Field(ge=0.0, le=1.0)]]
    time_since_last_alert: float = Field(ge=0.0)


class EpisodeRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    episode_id: str
    step: int = Field(ge=0)
    action: Action
    detection: DetectionResult
    reward: float
    context_before: ContextVector
    context_after: ContextVector
    timestamp: datetime


class RunManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    seed: int = Field(ge=0)
    python_version: str
    packages: dict[str, str]
    suricata_version: str
    ruleset_version: str
    git_commit: str
    config_snapshot: dict[str, Any]
    timestamp: str
