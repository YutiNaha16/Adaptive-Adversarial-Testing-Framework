"""Hyperparameter sweep — vary anomaly_lambda and detection_threshold, report DR/CAE.

Usage:
    python src/run_sweep.py --config config_round3_ml.yaml
    make sweep CONFIG=config_round3_ml.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import yaml

import run_experiment as _re

_LAMBDA_VALUES = [0.0, 0.2, 0.5, 0.8, 1.2]
_THRESHOLD_VALUES = [0.55, 0.60, 0.63, 0.68, 0.73]


def _run_cell(base_cfg: dict, lam: float, thresh: float, sweep_dir: Path) -> dict:
    label = f"lam{lam:.2f}_thr{thresh:.2f}".replace(".", "")
    out_dir = sweep_dir / label
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = dict(base_cfg)
    cfg["anomaly_lambda"] = lam
    cfg["detection_threshold"] = thresh
    cfg["output_dir"] = str(out_dir)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, dir=out_dir) as fh:
        yaml.dump(cfg, fh)
        tmp = Path(fh.name)

    try:
        _re.main(config_path=tmp)
    finally:
        tmp.unlink(missing_ok=True)

    manifests = sorted(out_dir.glob("run_manifest_*.json"))
    if not manifests:
        return {"dr": None, "cae": None, "rs": None}
    data = json.loads(manifests[-1].read_text())
    return {
        "dr": round(float(data.get("detection_rate", 0.0)), 4),
        "rs": round(float(data.get("robustness_score", 0.0)), 4),
        "cae": round(float(data.get("cae", 0.0)), 4),
    }


def main(config_path: str) -> None:
    cfg_path = Path(config_path)
    if not cfg_path.exists():
        print(f"ERROR: config not found: {cfg_path}", file=sys.stderr)
        sys.exit(1)

    with cfg_path.open() as f:
        base_cfg = yaml.safe_load(f)

    sweep_dir = Path(base_cfg.get("output_dir", "outputs/sweep")) / "sweep"
    sweep_dir.mkdir(parents=True, exist_ok=True)

    attacker = base_cfg.get("attacker_class", "?")
    episodes = base_cfg.get("episodes", "?")

    print("=" * 60)
    print(f"Hyperparameter sweep: {cfg_path.name}")
    print(f"Attacker: {attacker}  Episodes: {episodes}")
    print(f"anomaly_lambda   : {_LAMBDA_VALUES}")
    print(f"detection_threshold: {_THRESHOLD_VALUES}")
    print("=" * 60)

    results = {}
    total = len(_LAMBDA_VALUES) * len(_THRESHOLD_VALUES)
    done = 0
    for lam in _LAMBDA_VALUES:
        for thresh in _THRESHOLD_VALUES:
            done += 1
            print(f"\n[{done}/{total}] lambda={lam}  threshold={thresh}")
            r = _run_cell(base_cfg, lam, thresh, sweep_dir)
            results[f"lam={lam},thr={thresh}"] = r
            print(f"  DR={r['dr']}  RS={r['rs']}  CAE={r['cae']}")

    # Print summary table
    print()
    print("=" * 60)
    print("DR HEATMAP (rows=lambda, cols=threshold)")
    print("=" * 60)
    header = "lambda\\thresh  " + "  ".join(f"{t:.2f}" for t in _THRESHOLD_VALUES)
    print(header)
    for lam in _LAMBDA_VALUES:
        row = f"{lam:<14}"
        for thresh in _THRESHOLD_VALUES:
            val = results[f"lam={lam},thr={thresh}"]["dr"]
            row += f"  {val:.3f}" if val is not None else "   N/A"
        print(row)

    print()
    print("CAE HEATMAP (rows=lambda, cols=threshold)")
    print("=" * 60)
    print(header)
    for lam in _LAMBDA_VALUES:
        row = f"{lam:<14}"
        for thresh in _THRESHOLD_VALUES:
            val = results[f"lam={lam},thr={thresh}"]["cae"]
            row += f"  {val:.3f}" if val is not None else "   N/A"
        print(row)

    out = sweep_dir / "sweep_summary.json"
    out.write_text(
        json.dumps(
            {
                "config": str(cfg_path),
                "attacker_class": attacker,
                "episodes": episodes,
                "lambda_values": _LAMBDA_VALUES,
                "threshold_values": _THRESHOLD_VALUES,
                "results": results,
            },
            indent=2,
        )
    )
    print()
    print(f"Full results: {out}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AATF hyperparameter sweep")
    parser.add_argument("--config", default="config_round3_ml.yaml")
    args = parser.parse_args()
    main(args.config)
