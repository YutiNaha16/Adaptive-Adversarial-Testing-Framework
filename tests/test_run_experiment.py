"""Tests for src/run_experiment.py — 8 contracts C-001..C-008."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# run_experiment.py lives in src/ alongside the aatf package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import run_experiment


def _write_config(
    tmp_path: Path,
    attacker_class: str = "RandomAttacker",
    episodes: int = 2,
) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    cfg = tmp_path / "config.yaml"
    out = tmp_path / "out"
    cfg.write_text(
        f"episodes: {episodes}\n"
        f"seed: 42\n"
        f"output_dir: {out}\n"
        f"ruleset_path: /tmp/rules\n"
        f"detection_threshold: 0.5\n"
        f"attacker_class: {attacker_class}\n"
    )
    return cfg


def test_c001_importability():
    import run_experiment as _re  # noqa: F401

    assert callable(_re.main)


def test_c002_output_dir_created(tmp_path):
    cfg = _write_config(tmp_path)
    out = tmp_path / "out"
    assert not out.exists()
    run_experiment.main(config_path=cfg)
    assert out.exists()


def test_c003_report_md_written(tmp_path):
    cfg = _write_config(tmp_path)
    run_experiment.main(config_path=cfg)
    out = tmp_path / "out"
    md_files = list(out.glob("*.md"))
    assert len(md_files) >= 1


def test_c004_manifest_json_written(tmp_path):
    cfg = _write_config(tmp_path)
    run_experiment.main(config_path=cfg)
    out = tmp_path / "out"
    manifests = list(out.glob("run_manifest_*.json"))
    assert len(manifests) >= 1


def test_c005_manifest_keys(tmp_path):
    cfg = _write_config(tmp_path)
    run_experiment.main(config_path=cfg)
    out = tmp_path / "out"
    manifest_path = next(out.glob("run_manifest_*.json"))
    data = json.loads(manifest_path.read_text())
    assert "seed" in data
    assert "config_snapshot" in data
    assert "timestamp" in data
    assert "git_commit" in data
    assert data["config_snapshot"]["attacker_class"] == "RandomAttacker"


def test_c006_determinism(tmp_path, capsys):
    cfg1 = _write_config(tmp_path / "run1", episodes=3)
    run_experiment.main(config_path=cfg1)
    out1 = capsys.readouterr().out

    cfg2 = _write_config(tmp_path / "run2", episodes=3)
    run_experiment.main(config_path=cfg2)
    out2 = capsys.readouterr().out

    def _get_dr(output: str) -> str:
        for line in output.splitlines():
            if "Detection Rate" in line:
                return line.strip()
        return ""

    assert _get_dr(out1) == _get_dr(out2)
    assert _get_dr(out1) != ""


def test_c007_missing_config_exits(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        run_experiment.main(config_path=tmp_path / "nonexistent.yaml")
    assert exc_info.value.code != 0


def test_c008_unknown_attacker_class_exits(tmp_path):
    cfg = _write_config(tmp_path, attacker_class="BogusAttacker")
    with pytest.raises(SystemExit) as exc_info:
        run_experiment.main(config_path=cfg)
    assert exc_info.value.code != 0
