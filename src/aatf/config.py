from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    episodes: int = Field(gt=0)
    seed: int = Field(ge=0)
    output_dir: Path
    ruleset_path: Path
    detection_threshold: float = Field(ge=0.0, le=1.0)
    attacker_class: str = "RandomAttacker"
    anomaly_lambda: float = Field(ge=0.0, default=0.0)
    lab_target_ip: str = "172.28.0.2"
    detector: str = "isolation_forest"  # "isolation_forest" or "ae"


def load_config(path: Path | str = "config.yaml") -> ExperimentConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open() as f:
        data = yaml.safe_load(f)
    if data is None:
        data = {}
    return ExperimentConfig.model_validate(data)
