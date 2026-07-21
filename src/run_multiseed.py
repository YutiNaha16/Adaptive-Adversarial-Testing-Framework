"""Multi-seed experiment runner — runs one config across N seeds and reports 95% CI.

Usage:
    python src/run_multiseed.py --config config_round3_ml.yaml --seeds 0,1,2,3,4
    make multiseed CONFIG=config_round3_ml.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import yaml

import run_experiment as _re
from aatf.statistics import summarise_metric


def _run_one_seed(base_cfg: dict, seed: int, base_output: Path) -> dict:
    """Run a single seed and return the manifest data."""
    seed_dir = base_output / f"seed_{seed}"
    seed_dir.mkdir(parents=True, exist_ok=True)

    cfg = dict(base_cfg)
    cfg["seed"] = seed
    cfg["output_dir"] = str(seed_dir)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, dir=seed_dir) as fh:
        yaml.dump(cfg, fh)
        tmp_cfg = Path(fh.name)

    try:
        _re.main(config_path=tmp_cfg)
    finally:
        tmp_cfg.unlink(missing_ok=True)

    manifests = sorted(seed_dir.glob("run_manifest_*.json"))
    if not manifests:
        raise RuntimeError(f"No manifest produced for seed {seed}")
    return json.loads(manifests[-1].read_text())


def main(config_path: str, seeds: list[int]) -> None:
    cfg_path = Path(config_path)
    if not cfg_path.exists():
        print(f"ERROR: config not found: {cfg_path}", file=sys.stderr)
        sys.exit(1)

    with cfg_path.open() as f:
        base_cfg = yaml.safe_load(f)

    base_output = Path(base_cfg.get("output_dir", "outputs/multiseed")) / "multiseed"
    base_output.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print(f"Multi-seed run: {cfg_path.name}")
    print(f"Seeds         : {seeds}")
    print(f"Attacker      : {base_cfg.get('attacker_class', '?')}")
    print(f"Episodes/seed : {base_cfg.get('episodes', '?')}")
    print("=" * 50)

    dr_vals, rs_vals, cae_vals = [], [], []
    for seed in seeds:
        print(f"\n--- Seed {seed} ---")
        data = _run_one_seed(base_cfg, seed, base_output)
        dr_vals.append(float(data.get("detection_rate", 0.0)))
        rs_vals.append(float(data.get("robustness_score", 0.0)))
        cae_vals.append(float(data.get("cae", 0.0)))
        print(f"  DR={dr_vals[-1]:.4f}  RS={rs_vals[-1]:.4f}  CAE={cae_vals[-1]:.4f}")

    print()
    print("=" * 50)
    print("Aggregate Results (95% bootstrap CI)")
    print("=" * 50)

    summary: dict = {}
    metric_pairs = [("detection_rate", dr_vals), ("robustness_score", rs_vals), ("cae", cae_vals)]
    for name, vals in metric_pairs:
        s = summarise_metric(name, vals)
        summary[name] = {
            "mean": round(s.mean, 4),
            "std": round(s.std, 4),
            "ci_low": round(s.ci_low, 4),
            "ci_high": round(s.ci_high, 4),
            "values": [round(v, 4) for v in vals],
        }
        print(
            f"  {name:<22}: {s.mean:.4f} ± {s.std:.4f}  [95% CI: {s.ci_low:.4f} – {s.ci_high:.4f}]"
        )

    out = base_output / "multiseed_summary.json"
    out.write_text(
        json.dumps(
            {
                "config": str(cfg_path),
                "seeds": seeds,
                "attacker_class": base_cfg.get("attacker_class"),
                "episodes_per_seed": base_cfg.get("episodes"),
                "metrics": summary,
            },
            indent=2,
        )
    )
    print()
    print(f"Summary saved: {out}")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-seed AATF runner")
    parser.add_argument("--config", default="config_round3_ml.yaml")
    parser.add_argument(
        "--seeds",
        default="0,1,2,3,4",
        help="Comma-separated seed list (default: 0,1,2,3,4)",
    )
    args = parser.parse_args()
    seeds = [int(s.strip()) for s in args.seeds.split(",")]
    main(args.config, seeds)
