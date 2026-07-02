import json
import re
import unittest.mock

import pytest

from aatf.config import ExperimentConfig
from aatf.manifest import write_manifest


@pytest.fixture()
def cfg(tmp_path):
    return ExperimentConfig.model_validate(
        {
            "episodes": 10,
            "seed": 42,
            "output_dir": str(tmp_path / "outputs"),
            "ruleset_path": "/etc/suricata/rules",
            "detection_threshold": 0.5,
        }
    )


def test_manifest_written(cfg):
    path = write_manifest(cfg, 42)
    assert path.exists()


def test_manifest_filename_pattern(cfg):
    path = write_manifest(cfg, 42)
    assert re.match(r"run_manifest_\d{8}T\d{6}\d+Z\.json", path.name)


def test_manifest_no_overwrite(cfg):
    p1 = write_manifest(cfg, 42)
    p2 = write_manifest(cfg, 42)
    assert p1 != p2
    assert p1.exists() and p2.exists()


def test_manifest_schema(cfg):
    path = write_manifest(cfg, 42)
    data = json.loads(path.read_text())
    required_keys = {
        "seed",
        "python_version",
        "packages",
        "suricata_version",
        "ruleset_version",
        "git_commit",
        "config_snapshot",
        "timestamp",
    }
    assert required_keys.issubset(data.keys())


def test_manifest_seed_field(cfg):
    path = write_manifest(cfg, 99)
    data = json.loads(path.read_text())
    assert data["seed"] == 99


def test_manifest_config_snapshot(cfg):
    path = write_manifest(cfg, 42)
    data = json.loads(path.read_text())
    snap = data["config_snapshot"]
    assert snap["episodes"] == 10
    assert snap["seed"] == 42
    assert snap["detection_threshold"] == 0.5


def test_manifest_creates_output_dir(tmp_path):
    out_dir = tmp_path / "new_dir" / "nested"
    cfg = ExperimentConfig.model_validate(
        {
            "episodes": 5,
            "seed": 1,
            "output_dir": str(out_dir),
            "ruleset_path": "/etc/suricata/rules",
            "detection_threshold": 0.5,
        }
    )
    assert not out_dir.exists()
    path = write_manifest(cfg, 1)
    assert out_dir.exists()
    assert path.exists()


def test_manifest_unknown_suricata(cfg):
    path = write_manifest(cfg, 42)
    data = json.loads(path.read_text())
    assert data["suricata_version"] == "unknown"


def test_manifest_custom_versions(cfg):
    path = write_manifest(cfg, 42, suricata_version="7.0.3", ruleset_version="2026-06-01")
    data = json.loads(path.read_text())
    assert data["suricata_version"] == "7.0.3"
    assert data["ruleset_version"] == "2026-06-01"


def test_manifest_git_absent(cfg):
    with unittest.mock.patch("subprocess.run", side_effect=FileNotFoundError):
        path = write_manifest(cfg, 42)
    data = json.loads(path.read_text())
    assert data["git_commit"] == "unknown"


def test_manifest_packages_dict(cfg):
    path = write_manifest(cfg, 42)
    data = json.loads(path.read_text())
    pkgs = data["packages"]
    assert isinstance(pkgs, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in pkgs.items())
    assert "pydantic" in pkgs
