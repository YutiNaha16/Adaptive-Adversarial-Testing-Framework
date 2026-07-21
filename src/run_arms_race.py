"""Arms race loop — iterates attacker vs defender across N rounds.

Each round:
  1. Fresh ParameterizedDQNAttacker trains against the current defender
  2. Evasive vectors are cached and added to the defender's cosine-boost pool
  3. Threshold tightens by `--threshold-delta` per round
  4. Next round's attacker must find NEW evasion paths

This models the real-world arms race: defender adapts → attacker adapts back.

Usage:
    python src/run_arms_race.py --config config_round3_ml.yaml --rounds 5
    make arms-race
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import yaml

import run_experiment as _re


def _run_round(
    base_cfg: dict,
    round_idx: int,
    threshold: float,
    cache_path: Path | None,
    race_dir: Path,
) -> tuple[dict, Path]:
    """Run one arms-race round. Returns (manifest_data, new_cache_path)."""
    round_dir = race_dir / f"round_{round_idx:02d}"
    round_dir.mkdir(parents=True, exist_ok=True)

    cfg = dict(base_cfg)
    cfg["output_dir"] = str(round_dir)
    cfg["detection_threshold"] = round(threshold, 4)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, dir=round_dir) as fh:
        yaml.dump(cfg, fh)
        tmp = Path(fh.name)

    try:
        _re.main(
            config_path=tmp,
            evasive_cache=str(cache_path) if cache_path and cache_path.exists() else None,
        )
    finally:
        tmp.unlink(missing_ok=True)

    manifests = sorted(round_dir.glob("run_manifest_*.json"))
    if not manifests:
        raise RuntimeError(f"No manifest for round {round_idx}")
    data = json.loads(manifests[-1].read_text())

    # The evasive cache produced by auto_remediate in this round
    new_cache = round_dir / "evasive_cache.npy"

    # Accumulate: merge previous cache with this round's new evasive vectors
    if cache_path and cache_path.exists() and new_cache.exists():
        old = np.load(cache_path)
        new = np.load(new_cache)
        merged = np.unique(np.vstack([old, new]), axis=0)
        acc_path = race_dir / f"accumulated_cache_{round_idx:02d}.npy"
        np.save(acc_path, merged)
        return data, acc_path
    elif new_cache.exists():
        return data, new_cache
    else:
        # No evasions found — return previous cache unchanged
        return data, cache_path or round_dir / "evasive_cache.npy"


def main(config_path: str, n_rounds: int, threshold_delta: float) -> None:
    cfg_path = Path(config_path)
    if not cfg_path.exists():
        print(f"ERROR: config not found: {cfg_path}", file=sys.stderr)
        sys.exit(1)

    with cfg_path.open() as f:
        base_cfg = yaml.safe_load(f)

    if base_cfg.get("anomaly_lambda", 0.0) == 0.0:
        print("ERROR: arms race requires anomaly_lambda > 0 in config", file=sys.stderr)
        sys.exit(1)

    race_dir = Path(base_cfg.get("output_dir", "outputs/arms_race")) / "arms_race"
    race_dir.mkdir(parents=True, exist_ok=True)

    base_threshold = float(base_cfg.get("detection_threshold", 0.63))
    attacker = base_cfg.get("attacker_class", "?")
    episodes = base_cfg.get("episodes", "?")

    print("=" * 60)
    print("AATF Arms Race Loop")
    print("=" * 60)
    print(f"Config    : {cfg_path.name}")
    print(f"Attacker  : {attacker}")
    print(f"Episodes  : {episodes} per round")
    print(f"Rounds    : {n_rounds}")
    print(f"Threshold : {base_threshold:.3f} → +{threshold_delta:.3f}/round (defender tightens)")
    print("=" * 60)

    rounds_log = []
    cache_path: Path | None = None
    threshold = base_threshold

    for r in range(n_rounds):
        print(f"\n{'=' * 60}")
        cache_status = "yes" if cache_path and cache_path.exists() else "none"
        print(f"ROUND {r}  |  threshold={threshold:.4f}  |  cache={cache_status}")
        print(f"{'=' * 60}")

        data, cache_path = _run_round(base_cfg, r, threshold, cache_path, race_dir)

        dr = float(data.get("detection_rate", 0.0))
        rs = float(data.get("robustness_score", 0.0))
        cae = float(data.get("cae", 0.0))

        rounds_log.append(
            {
                "round": r,
                "threshold": round(threshold, 4),
                "cache_vectors": (
                    int(len(np.load(cache_path))) if cache_path and cache_path.exists() else 0
                ),
                "detection_rate": round(dr, 4),
                "robustness_score": round(rs, 4),
                "cae": round(cae, 4),
            }
        )

        print(f"\n  Round {r} result: DR={dr:.4f}  RS={rs:.4f}  CAE={cae:.4f}")
        threshold = min(0.95, threshold + threshold_delta)

    # Summary
    print()
    print("=" * 60)
    print("ARMS RACE SUMMARY")
    print("=" * 60)
    print(f"  {'Round':<8} {'Threshold':<12} {'Cache':<8} {'DR':<10} {'RS':<10} {'CAE'}")
    print(f"  {'-' * 8} {'-' * 12} {'-' * 8} {'-' * 10} {'-' * 10} {'-' * 6}")
    for row in rounds_log:
        print(
            f"  {row['round']:<8} {row['threshold']:<12.4f} {row['cache_vectors']:<8} "
            f"{row['detection_rate']:<10.4f} {row['robustness_score']:<10.4f} {row['cae']:.4f}"
        )

    # DR trend
    drs = [row["detection_rate"] for row in rounds_log]
    if len(drs) >= 2:
        trend = drs[-1] - drs[0]
        direction = "improved" if trend > 0 else "degraded"
        print()
        print(f"  Defender DR {direction} by {abs(trend):.4f} over {n_rounds} rounds")
        print(f"  (Round 0: {drs[0]:.4f} → Round {n_rounds - 1}: {drs[-1]:.4f})")

    out = race_dir / "arms_race_summary.json"
    out.write_text(
        json.dumps(
            {
                "config": str(cfg_path),
                "attacker_class": attacker,
                "episodes_per_round": episodes,
                "n_rounds": n_rounds,
                "threshold_delta": threshold_delta,
                "rounds": rounds_log,
            },
            indent=2,
        )
    )
    print()
    print(f"Full log: {out}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AATF arms race loop")
    parser.add_argument("--config", default="config_round3_ml.yaml")
    parser.add_argument("--rounds", type=int, default=4, help="Number of arms race rounds")
    parser.add_argument(
        "--threshold-delta",
        type=float,
        default=0.02,
        help="Threshold tightening per round (default 0.02)",
    )
    args = parser.parse_args()
    main(args.config, args.rounds, args.threshold_delta)
