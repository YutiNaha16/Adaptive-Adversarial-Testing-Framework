"""Experiment entrypoint — load config, run N episodes, generate report and manifest."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from aatf.action_library import REGISTRY
from aatf.attacker import FixedScriptAttacker, LinUCBAttacker, RandomAttacker
from aatf.config import load_config
from aatf.context_vector import EpisodeState, build_context
from aatf.contracts import Action
from aatf.defence import NullDefence
from aatf.dqn_attacker import DQNAttacker, DQNModel, ParameterizedDQNAttacker, ParameterizedDQNModel
from aatf.episode import run_episode
from aatf.explainability import explain_evasions
from aatf.gate import phase1_gate
from aatf.ground_truth import ValidationResult, validate_blind_spots
from aatf.linucb import LinUCBModel
from aatf.manifest import write_manifest
from aatf.metrics import (
    EpisodeRecord,
    cumulative_anomaly_exposure,
    detection_rate,
    robustness_score,
)
from aatf.report import generate_report
from aatf.seeding import seed_everything

_ATTACKER_REGISTRY = {
    "RandomAttacker": lambda seed, ctx_dim, n_actions: RandomAttacker(seed=seed),
    "FixedScriptAttacker": lambda seed, ctx_dim, n_actions: FixedScriptAttacker(),
    "LinUCBAttacker": lambda seed, ctx_dim, n_actions: LinUCBAttacker(LinUCBModel(d=ctx_dim)),
    "DQNAttacker": lambda seed, ctx_dim, n_actions: DQNAttacker(
        DQNModel(n_actions=n_actions, state_dim=ctx_dim, seed=seed)
    ),
    "ParameterizedDQNAttacker": lambda seed, ctx_dim, n_actions: ParameterizedDQNAttacker(
        ParameterizedDQNModel(n_actions=n_actions, state_dim=ctx_dim, seed=seed)
    ),
}


def _make_attacker(name: str, seed: int, ctx_dim: int, n_actions: int):
    if name not in _ATTACKER_REGISTRY:
        raise ValueError(f"Unknown attacker_class {name!r}. Valid: {sorted(_ATTACKER_REGISTRY)}")
    return _ATTACKER_REGISTRY[name](seed, ctx_dim, n_actions)


def _load_disabled_sids(disabled_conf: Path) -> set[str]:
    sids: set[str] = set()
    if not disabled_conf.exists():
        return sids
    for line in disabled_conf.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            sids.add(line)
    return sids


def main(
    config_path: str | Path = "config.yaml",
    lab: bool = False,
    eve_path: str | Path = "logs/suricata/eve.json",
    disabled_conf: str | Path = "lab/rules/disabled.conf",
    evasive_cache: str | Path | None = None,
    checkpoint_dir: str | Path | None = None,
) -> None:
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

    ml_defence = None

    if lab:
        from aatf.action_executor import ActionExecutor
        from aatf.action_intensity import get_params_for_intensity
        from aatf.defence import CompositeDefence
        from aatf.ml_defence import MLAnomalyDefence, load_evasive_cache
        from aatf.suricata_defence import SuricataDefence

        ml_defence = MLAnomalyDefence(threshold=config.detection_threshold, seed=config.seed)
        if evasive_cache and Path(evasive_cache).exists():
            n_loaded = load_evasive_cache(ml_defence, Path(evasive_cache))
            print(f"Loaded {n_loaded} evasive vectors from {evasive_cache}")
        defence = CompositeDefence(
            primary=SuricataDefence(eve_path),
            secondary=ml_defence,
        )
        executor = ActionExecutor(seed=config.seed)

        def execute_fn(action_id: str) -> None:
            action_def = REGISTRY.get_action(action_id)
            intensity = (
                attacker.get_last_intensity()
                if isinstance(attacker, ParameterizedDQNAttacker)
                else 1
            )
            params = get_params_for_intensity(
                action_id,
                intensity,
                action_def.default_parameters,
                target_ip=config.lab_target_ip,
            )
            action = Action(
                action_id=action_id,
                category=action_def.category,
                parameters=params,
                timestamp=datetime.now(UTC),
            )
            executor.execute(action)
            time.sleep(1.5)

        mode_label = "LAB (Suricata + ML)"
    else:
        execute_fn = lambda _: None  # noqa: E731
        if config.anomaly_lambda > 0:
            if config.detector == "ae":
                from aatf.ae_defence import AEAnomalyDefence
                from aatf.ae_defence import load_evasive_cache as ae_load_cache

                ml_defence = AEAnomalyDefence(
                    threshold=config.detection_threshold, seed=config.seed
                )
                if evasive_cache and Path(evasive_cache).exists():
                    n_loaded = ae_load_cache(ml_defence, Path(evasive_cache))
                    print(f"Loaded {n_loaded} evasive vectors from {evasive_cache}")
                mode_label = f"ML-simulation (Autoencoder, anomaly_lambda={config.anomaly_lambda})"
            else:
                from aatf.ml_defence import MLAnomalyDefence, load_evasive_cache

                ml_defence = MLAnomalyDefence(
                    threshold=config.detection_threshold, seed=config.seed
                )
                if evasive_cache and Path(evasive_cache).exists():
                    n_loaded = load_evasive_cache(ml_defence, Path(evasive_cache))
                    print(f"Loaded {n_loaded} evasive vectors from {evasive_cache}")
                mode_label = (
                    f"ML-simulation (IsolationForest, anomaly_lambda={config.anomaly_lambda})"
                )
            defence = ml_defence
        else:
            ml_defence = None
            defence = NullDefence()
            mode_label = "Simulation (NullDefence)"

    records: list[EpisodeRecord] = []

    # Build parameterize_fn for ParameterizedDQNAttacker so intensity-adjusted params
    # reach defence.observe() in both lab and sim modes.
    if isinstance(attacker, ParameterizedDQNAttacker):
        from aatf.action_intensity import get_params_for_intensity

        def parameterize_fn(action_id: str) -> dict:
            action_def = REGISTRY.get_action(action_id)
            intensity = attacker.get_last_intensity()
            return get_params_for_intensity(
                action_id,
                intensity,
                action_def.default_parameters,
                target_ip=config.lab_target_ip,
            )

    else:
        parameterize_fn = None

    print("Adaptive Adversarial Testing Framework")
    print("=" * 38)
    print(f"Mode     : {mode_label}")
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

        result = run_episode(
            state, action_selector, execute_fn, defence, parameterize_fn=parameterize_fn
        )

        for step, ctx in zip(result.steps, step_contexts, strict=False):
            shaped = step.reward - config.anomaly_lambda * step.anomaly_score
            attacker.observe(step.action_id, ctx, shaped)

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

    # Save model checkpoint if requested and attacker supports it
    if checkpoint_dir is not None:
        ckpt_path = Path(checkpoint_dir)
        ckpt_path.mkdir(parents=True, exist_ok=True)
        model = getattr(attacker, "_model", None)
        if model is not None and hasattr(model, "save"):
            ckpt_file = ckpt_path / f"{config.attacker_class.lower()}_checkpoint.pt"
            model.save(ckpt_file)
            print(f"Checkpoint saved : {ckpt_file}")

    dr = detection_rate(records)
    window = min(10, len(records))
    rs = robustness_score(records, window=window)

    if lab:
        disabled_sids = _load_disabled_sids(Path(disabled_conf))
        explanations = explain_evasions(records, REGISTRY)
        validation_result = validate_blind_spots(explanations, disabled_sids)
    else:
        validation_result = ValidationResult(
            blind_spot_precision=0.0,
            true_positives=0,
            false_positives=0,
            total_reported=0,
            disabled_sid_count=0,
        )
    gate_result = phase1_gate(records, validation_result, lab_mode=lab)
    cae = cumulative_anomaly_exposure(records)

    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")

    # Per-episode learning curve
    import json as _json

    # Save Q-value policy snapshot for ParameterizedDQNAttacker
    if isinstance(attacker, ParameterizedDQNAttacker):
        import numpy as _np

        neutral_state = _np.zeros(ctx_dim, dtype=_np.float32)
        policy = attacker._model.extract_policy(neutral_state)
        policy_path = output_dir / f"policy_{ts}.json"
        policy_path.write_text(_json.dumps(policy, indent=2))
        print(f"Policy snapshot  : {policy_path}")

    curve = [
        {
            "episode": r.episode_index,
            "total_reward": round(r.total_reward, 4),
            "steps": len(r.steps),
            "detected": sum(1 for s in r.steps if s.detected),
            "mean_anomaly": round(
                sum(s.anomaly_score for s in r.steps) / len(r.steps) if r.steps else 0.0, 4
            ),
        }
        for r in records
    ]
    curve_path = output_dir / f"learning_curve_{ts}.json"
    curve_path.write_text(_json.dumps(curve, indent=2))

    report_path = output_dir / f"report_{ts}.md"
    generate_report(records, REGISTRY, report_path)
    manifest_path = write_manifest(
        config,
        config.seed,
        extra_metadata={
            "detection_rate": dr,
            "robustness_score": rs,
            "cae": cae,
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
            },
        },
    )

    print("-" * 38)
    print(f"Detection Rate   : {dr:.4f}")
    print(f"Robustness Score : {rs:.4f}")
    print(f"Cumul. Anomaly Exp: {cae:.4f}")
    print(f"Report written   : {report_path}")
    print(f"Manifest written : {manifest_path}")
    print("-" * 38)
    for c in gate_result.criteria:
        if c.skipped:
            print(f"  {c.name:<22}: N/A  (lab mode only)  [SKIP]")
        else:
            status = "PASS" if c.passed else "FAIL"
            print(f"  {c.name:<22}: {c.value:.4f} (≥{c.threshold:.4f}) [{status}]")
    print(gate_result.summary)

    if ml_defence is not None and cae > 0:
        from aatf.ml_defence import auto_remediate, save_evasive_cache

        # Use detection_threshold as evasion_threshold so we cache any action that slipped through
        new_defence, rem = auto_remediate(
            ml_defence, records, evasion_threshold=config.detection_threshold
        )
        cache_path = output_dir / "evasive_cache.npy"
        save_evasive_cache(new_defence, cache_path)
        print("-" * 38)
        print("Auto-Remediation:")
        print(f"  Double blind spots found : {rem.total_evaded}")
        if rem.total_evaded > 0:
            print(f"  Gaps closed              : {rem.gaps_closed}/{rem.total_evaded}")
            print(f"  Avg ML score before      : {rem.avg_score_before:.4f}")
            print(f"  Avg ML score after       : {rem.avg_score_after:.4f}")
            print(f"  Actions remediated       : {', '.join(rem.remediated_action_ids)}")
            print(f"  Cache saved              : {cache_path}")
        else:
            print("  No double blind spots — ML detector caught all evaded actions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AATF experiment")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument(
        "--lab",
        action="store_true",
        help="Use real Suricata defence + ActionExecutor (Docker lab must be running)",
    )
    parser.add_argument(
        "--eve-path",
        default="logs/suricata/eve.json",
        help="Path to Suricata eve.json (used with --lab)",
    )
    parser.add_argument(
        "--disabled-conf",
        default="lab/rules/disabled.conf",
        help="Path to disabled.conf for BSP validation (used with --lab)",
    )
    parser.add_argument(
        "--evasive-cache",
        default=None,
        help="Path to evasive_cache.npy from a previous run (pre-loads auto-remediation vectors)",
    )
    parser.add_argument(
        "--checkpoint-dir",
        default=None,
        help="Directory to save trained model checkpoint after run (DQN/ParameterizedDQN only)",
    )
    args = parser.parse_args()
    main(
        config_path=args.config,
        lab=args.lab,
        eve_path=args.eve_path,
        disabled_conf=args.disabled_conf,
        evasive_cache=args.evasive_cache,
        checkpoint_dir=args.checkpoint_dir,
    )
