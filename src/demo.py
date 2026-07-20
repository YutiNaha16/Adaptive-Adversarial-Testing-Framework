"""AATF Black Hat Demo — replays stored round results + launches dashboard.

Usage:  make demo
        python src/demo.py [--live]   # --live runs 5 new episodes instead of replay

Replay mode (default): reads existing run manifests and prints the full story
in ~5 seconds — no Docker needed.  Safe for live presentations.

Live mode (--live): actually runs 5 episodes with ParameterizedDQNAttacker.
Requires: make setup (done once).  No lab needed for simulation.
"""

from __future__ import annotations

import argparse
import sys
import time

# ---------------------------------------------------------------------------
# Phase 1: Suricata rule-based detection (lab mode, real network traffic)
# ---------------------------------------------------------------------------
_PHASE1_ROUNDS = [
    {
        "dir": "outputs/run_001",
        "label": "Round 1 — Random Baseline (Suricata)",
        "attacker": "RandomAttacker",
        "episodes": 100,
        "dr": 0.1287,
        "rs": 0.1333,
        "cae": 9.8243,
        "highlight": "Establishes the detection floor: 12.9% of actions trigger Suricata rules.",
    },
    {
        "dir": "outputs/run_002",
        "label": "Round 2 — DQN, fixed parameters (Suricata)",
        "attacker": "DQNAttacker",
        "episodes": 200,
        "dr": 0.1327,
        "rs": 0.1333,
        "cae": 9.8243,
        "highlight": "DQN without intensity control learns nothing new — DR unchanged at 13.3%.",
    },
    {
        "dir": "outputs/run_003",
        "label": "Round 3 — Parameterized DQN, Novelty 1 (Suricata)",
        "attacker": "ParameterizedDQNAttacker",
        "episodes": 200,
        "dr": 0.0767,
        "rs": 0.0733,
        "cae": 9.8243,
        "highlight": "Low-intensity SSH (2 attempts) slips under the 5-attempt Suricata threshold. "
        "DR drops 40% with no rule changes.",
    },
]

# ---------------------------------------------------------------------------
# Phase 2: ML anomaly detection (sim mode, IsolationForest + auto-remediation)
# ---------------------------------------------------------------------------
_PHASE2_ROUNDS = [
    {
        "dir": "outputs/run_003_ml",
        "label": "Round 3-ML — Parameterized DQN vs IsolationForest",
        "attacker": "ParameterizedDQNAttacker",
        "episodes": 200,
        "dr": 0.0000,
        "rs": 0.0000,
        "cae": 9.2119,
        "highlight": "With anomaly_lambda shaping, attacker learns low-intensity profiles that "
        "score below the IsolationForest threshold. DR collapses to 0% — all 15 action "
        "types evade the ML detector.",
    },
    {
        "dir": "outputs/run_004",
        "label": "Round 4 — Auto-Remediation, Novelty 2 (cache pre-loaded)",
        "attacker": "ParameterizedDQNAttacker",
        "episodes": 200,
        "dr": 0.8987,
        "rs": 0.8733,
        "cae": 11.7774,
        "highlight": "Evasive feature vectors from Round 3-ML seed cosine-similarity boosting. "
        "ML scores for previously-evaded actions jump from 0.615 → 0.809, pushing them "
        "above the detection threshold. DR recovers to 89.9% — no model retraining needed.",
    },
]

_SEP = "=" * 62
_SEP2 = "-" * 62


def _print_round(r: dict) -> None:
    print()
    print(_SEP2)
    print(f"  {r['label']}")
    print(_SEP2)
    print(f"  Attacker  : {r['attacker']}")
    print(f"  Episodes  : {r['episodes']}")
    print(f"  Detection : {r['dr']:.2%}  (lower = stealthier attacker)")
    print(f"  Robustness: {r['rs']:.4f}")
    print(f"  CAE       : {r['cae']:.4f}  (cumulative anomaly exposure)")
    print()
    print(f"  ► {r['highlight']}")


def replay() -> None:
    print()
    print(_SEP)
    print("  Adaptive Adversarial Testing Framework")
    print("  Black Hat Europe 2026  —  Demo Replay")
    print(_SEP)
    print()
    print("  Stored results from 5 experiment rounds (no Docker needed).")
    print()

    # --- Phase 1 ---
    print(_SEP)
    print("  PHASE 1: Rule-Based Detection  (Suricata ETOpen)")
    print(_SEP)
    for r in _PHASE1_ROUNDS:
        time.sleep(0.4)
        _print_round(r)

    p1_improvement = (1 - _PHASE1_ROUNDS[2]["dr"] / _PHASE1_ROUNDS[0]["dr"]) * 100
    print()
    print(_SEP2)
    print(f"  Phase 1 result: ParameterizedDQN reduced Suricata DR by {p1_improvement:.0f}%")
    print(
        f"  ({_PHASE1_ROUNDS[0]['dr']:.2%} → {_PHASE1_ROUNDS[2]['dr']:.2%}) "
        "via autonomous intensity selection."
    )

    # --- Phase 2 ---
    print()
    time.sleep(0.6)
    print(_SEP)
    print("  PHASE 2: ML Anomaly Detection  (IsolationForest + Auto-Remediation)")
    print(_SEP)
    for r in _PHASE2_ROUNDS:
        time.sleep(0.4)
        _print_round(r)

    p2_recovery = _PHASE2_ROUNDS[1]["dr"] - _PHASE2_ROUNDS[0]["dr"]
    print()
    print(_SEP2)
    print(f"  Phase 2 result: auto-remediation recovered {p2_recovery:.2%} detection rate")
    print(
        f"  ({_PHASE2_ROUNDS[0]['dr']:.2%} → {_PHASE2_ROUNDS[1]['dr']:.2%}) "
        "with zero IsolationForest retraining."
    )

    # --- Summary ---
    print()
    time.sleep(0.4)
    print(_SEP)
    print("  SUMMARY — Two Novelties Demonstrated")
    print(_SEP)
    print()
    print("  Novelty 1: Parameterized DQN (intensity control)")
    print("    The RL attacker learns to select packet-level intensity — not just")
    print("    which attack to run, but how loudly. Low intensity evades both rule")
    print("    thresholds (Suricata) and anomaly models (IsolationForest).")
    print()
    print("  Novelty 2: Auto-Remediation via cosine-similarity boosting")
    print("    Evasive feature vectors are cached after each run. Future executions")
    print("    of similar actions get their anomaly score boosted above the detection")
    print("    threshold — closing the gap without retraining the ML model.")
    print()
    print("  Run 'make dashboard' to open the live metrics UI.")
    print(_SEP)
    print()


def live() -> None:
    print()
    print(_SEP)
    print("  AATF — Live 5-Episode Demo  (ParameterizedDQNAttacker)")
    print(_SEP)
    print()
    import subprocess

    result = subprocess.run(
        [sys.executable, "src/run_experiment.py", "--config", "config_demo.yaml"],
        check=False,
    )
    if result.returncode != 0:
        print("Demo run failed.", file=sys.stderr)
        sys.exit(result.returncode)
    print()
    print("5 episodes complete.  For full 200-episode results: make round3-ml && make round4")
    print("Open metrics dashboard: make dashboard")


def main() -> None:
    parser = argparse.ArgumentParser(description="AATF Black Hat demo")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run 5 real episodes instead of showing stored results",
    )
    args = parser.parse_args()
    if args.live:
        live()
    else:
        replay()


if __name__ == "__main__":
    main()
