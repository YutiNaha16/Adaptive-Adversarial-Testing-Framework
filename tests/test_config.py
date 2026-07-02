from pathlib import Path

import pytest
from pydantic import ValidationError

from aatf.config import ExperimentConfig, load_config


def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(content)
    return p


def test_load_valid_config(tmp_path):
    cfg_path = _write_yaml(
        tmp_path,
        """
episodes: 100
seed: 42
output_dir: outputs/run_001
ruleset_path: /etc/suricata/rules
detection_threshold: 0.5
""",
    )
    cfg = load_config(cfg_path)
    assert isinstance(cfg, ExperimentConfig)
    assert cfg.episodes == 100
    assert cfg.seed == 42
    assert cfg.output_dir == Path("outputs/run_001")
    assert cfg.ruleset_path == Path("/etc/suricata/rules")
    assert cfg.detection_threshold == 0.5


def test_load_missing_file(tmp_path):
    missing = tmp_path / "does_not_exist.yaml"
    with pytest.raises(FileNotFoundError) as exc_info:
        load_config(missing)
    assert str(missing) in str(exc_info.value)


def test_load_missing_field(tmp_path):
    cfg_path = _write_yaml(
        tmp_path,
        """
episodes: 100
output_dir: outputs/run_001
ruleset_path: /etc/suricata/rules
detection_threshold: 0.5
""",
    )
    with pytest.raises(ValidationError) as exc_info:
        load_config(cfg_path)
    assert "seed" in str(exc_info.value)


def test_load_wrong_type(tmp_path):
    cfg_path = _write_yaml(
        tmp_path,
        """
episodes: "ten"
seed: 42
output_dir: outputs/run_001
ruleset_path: /etc/suricata/rules
detection_threshold: 0.5
""",
    )
    with pytest.raises(ValidationError) as exc_info:
        load_config(cfg_path)
    assert "episodes" in str(exc_info.value)


def test_load_empty_file(tmp_path):
    cfg_path = _write_yaml(tmp_path, "")
    with pytest.raises(ValidationError):
        load_config(cfg_path)


def test_config_is_frozen(tmp_path):
    cfg_path = _write_yaml(
        tmp_path,
        """
episodes: 100
seed: 42
output_dir: outputs/run_001
ruleset_path: /etc/suricata/rules
detection_threshold: 0.5
""",
    )
    cfg = load_config(cfg_path)
    with pytest.raises(ValidationError):
        cfg.episodes = 999


def test_detection_threshold_bounds(tmp_path):
    cfg_path = _write_yaml(
        tmp_path,
        """
episodes: 100
seed: 42
output_dir: outputs/run_001
ruleset_path: /etc/suricata/rules
detection_threshold: 1.5
""",
    )
    with pytest.raises(ValidationError) as exc_info:
        load_config(cfg_path)
    assert "detection_threshold" in str(exc_info.value)


def test_config_dump(tmp_path):
    cfg_path = _write_yaml(
        tmp_path,
        """
episodes: 100
seed: 42
output_dir: outputs/run_001
ruleset_path: /etc/suricata/rules
detection_threshold: 0.5
""",
    )
    cfg = load_config(cfg_path)
    d = cfg.model_dump(mode="json")
    assert isinstance(d["output_dir"], str)
    assert isinstance(d["ruleset_path"], str)
    assert d["episodes"] == 100
