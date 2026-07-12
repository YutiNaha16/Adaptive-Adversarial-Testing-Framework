"""Experiment entrypoint — load config, run N episodes, generate report and manifest."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from aatf.action_library import REGISTRY
from aatf.attacker import FixedScriptAttacker, LinUCBAttacker, RandomAttacker
from aatf.config import load_config
from aatf.context_vector import EpisodeState, build_context
from aatf.defence import NullDefence
from aatf.episode import run_episode
from aatf.gate import phase1_gate
from aatf.ground_truth import ValidationResult
from aatf.linucb import LinUCBModel
from aatf.manifest import write_manifest
from aatf.metrics import EpisodeRecord, detection_rate, robustness_score
from aatf.report import generate_report
from aatf.seeding import seed_everything

_ATTACKER_REGISTRY = {
    "RandomAttacker": lambda seed, ctx_dim, n_actions: RandomAttacker(seed=seed),
    "FixedScriptAttacker": lambda seed, ctx_dim, n_actions: FixedScriptAttacker(),
    "LinUCBAttacker": lambda seed, ctx_dim, n_actions: LinUCBAttacker(
        LinUCBModel(n_actions=n_actions, context_dim=ctx_dim)
    ),
}


def _make_attacker(name: str, seed: int, ctx_dim: int, n_actions: int):
    if name not in _ATTACKER_REGISTRY:
        raise ValueError(f"Unknown attacker_class {name!r}. Valid: {sorted(_ATTACKER_REGISTRY)}")
    return _ATTACKER_REGISTRY[name](seed, ctx_dim, n_actions)


def main(config_path: str | Path = "config.yaml") -> None:
    try:
        config = load_config(config_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    seed_everything(config.seed)
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    initial_state = EpisodeState()
    ctx_dim = len(build_context(initial_state))
    n_actions = len(REGISTRY.list_actions())

    try:
        attacker = _make_attacker(config.attacker_class, config.seed, ctx_dim, n_actions)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)

    defence = NullDefence()
    records: list[EpisodeRecord] = []

    print("Adaptive Adversarial Testing Framework")
    print("=" * 38)
    print(f"Attacker : {config.attacker_class}")
    print(f"Episodes : {config.episodes}")
    print(f"Seed     : {config.seed}")
    print("-" * 38)
    print(f"Running {config.episodes} episodes...")

    for i in range(config.episodes):
        state = EpisodeState()
        step_contexts: list = []

        def action_selector(available, ep_state, _sc=step_contexts):
            ctx = build_context(ep_state)
            _sc.append(ctx)
            return attacker.choose_action(available, ctx)

        result = run_episode(state, action_selector, lambda _: None, defence)

        for step, ctx in zip(result.steps, step_contexts, strict=False):
            attacker.observe(step.action_id, ctx, step.reward)

        records.append(
            EpisodeRecord(
                attacker_class=config.attacker_class,
                seed=config.seed,
                steps=result.steps,
                total_reward=result.total_reward,
                completed=result.completed,
                episode_index=i,
            )
        )

    dr = detection_rate(records)
    window = min(10, len(records))
    rs = robustness_score(records, window=window)

    validation_result = ValidationResult(
        blind_spot_precision=0.0,
        true_positives=0,
        false_positives=0,
        total_reported=0,
        disabled_sid_count=0,
    )
    gate_result = phase1_gate(records, validation_result)

    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    report_path = output_dir / f"report_{ts}.md"
    generate_report(records, REGISTRY, report_path)
    manifest_path = write_manifest(
        config,
        config.seed,
        extra_metadata={
            "phase1_gate": {
                "passed": gate_result.passed,
                "summary": gate_result.summary,
                "criteria": [
                    {
                        "name": c.name,
                        "passed": c.passed,
                        "value": c.value,
                        "threshold": c.threshold,
                    }
                    for c in gate_result.criteria
                ],
            }
        },
    )

    print("-" * 38)
    print(f"Detection Rate   : {dr:.4f}")
    print(f"Robustness Score : {rs:.4f}")
    print(f"Report written   : {report_path}")
    print(f"Manifest written : {manifest_path}")
    print("-" * 38)
    for c in gate_result.criteria:
        status = "PASS" if c.passed else "FAIL"
        print(f"  {c.name:<22}: {c.value:.4f} (≥{c.threshold:.4f}) [{status}]")
    print(gate_result.summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AATF experiment")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()
    main(config_path=args.config)
