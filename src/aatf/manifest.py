import importlib.metadata
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from aatf.config import ExperimentConfig

KNOWN_PACKAGES = ["pip-tools", "pytest", "ruff", "pydantic", "pyyaml", "numpy"]


def _get_git_commit() -> str:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return f"{sha}-dirty" if dirty else sha
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


def _collect_packages() -> dict[str, str]:
    result = {}
    for name in KNOWN_PACKAGES:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    return result


def write_manifest(
    config: ExperimentConfig,
    seed: int,
    *,
    suricata_version: str = "unknown",
    ruleset_version: str = "unknown",
) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    config.output_dir.mkdir(parents=True, exist_ok=True)

    vi = sys.version_info
    manifest = {
        "seed": seed,
        "python_version": f"{vi.major}.{vi.minor}.{vi.micro}",
        "packages": _collect_packages(),
        "suricata_version": suricata_version,
        "ruleset_version": ruleset_version,
        "git_commit": _get_git_commit(),
        "config_snapshot": config.model_dump(mode="json"),
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    out_path = config.output_dir / f"run_manifest_{timestamp}.json"
    out_path.write_text(json.dumps(manifest, indent=2))
    return out_path
