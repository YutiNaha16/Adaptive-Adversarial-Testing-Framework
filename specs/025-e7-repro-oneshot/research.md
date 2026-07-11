# Research: One-Command Reproducibility (F25)

**Phase**: 0 — Research
**Date**: 2026-07-11
**Feature**: 025-e7-repro-oneshot

## Decision 1: Config class name and loader function

**Decision**: `ExperimentConfig` (not `Config`), loaded via `load_config(path: Path | str) -> ExperimentConfig` from `aatf.config`.

**Rationale**: Inspected `src/aatf/config.py` — class is `ExperimentConfig`, load function is `load_config`. The prompt's `Config.from_yaml` does not exist.

**Alternatives considered**: Proposing a rename — rejected to avoid unnecessary churn.

---

## Decision 2: seed_everything location

**Decision**: `from aatf.seeding import seed_everything` (not `from aatf.config import seed_everything`).

**Rationale**: Inspected `src/aatf/seeding.py` — `seed_everything(seed: int) -> None` lives there.

---

## Decision 3: Attacker module location

**Decision**: `from aatf.attacker import RandomAttacker, LinUCBAttacker, FixedScriptAttacker` (not `aatf.baselines`).

**Rationale**: Inspected `src/aatf/attacker.py`. No `baselines.py` exists. `RandomAttacker(seed)` and `LinUCBAttacker(model)` are in `attacker.py`.

**LinUCBAttacker construction**: Requires a `LinUCBModel` — instantiate via `LinUCBModel(n_actions=len(REGISTRY.actions), context_dim=N)` where N is the context vector dimension from `build_context`.

---

## Decision 4: Episode API — function not class

**Decision**: Use `run_episode(episode_state, action_selector, execute_fn, defence)` from `aatf.episode`. No `EpisodeLoop` class exists.

**Rationale**: Inspected `src/aatf/episode.py` — the public function is `run_episode()`. It returns `EpisodeResult` (not `EpisodeRecord`).

**Orchestration**: `run_experiment.py` must loop over N episodes, calling `run_episode` each time with a fresh `EpisodeState` and a closure `action_selector` that calls `build_context(episode_state)` then `attacker.choose_action(available, ctx)`.

---

## Decision 5: EpisodeRecord vs EpisodeResult

**Decision**: `EpisodeResult` is in `aatf.episode`; `EpisodeRecord` is in `aatf.metrics`. The entrypoint must convert `EpisodeResult → EpisodeRecord` after each episode.

**Rationale**: `aatf.metrics.EpisodeRecord` fields: `attacker_class, seed, steps, total_reward, completed, episode_index`. `aatf.episode.EpisodeResult` fields: `episode_state, steps, total_reward, completed`. Conversion is trivial.

---

## Decision 6: Manifest writing — use existing write_manifest

**Decision**: `from aatf.manifest import write_manifest` — already fully implemented; call `write_manifest(config, config.seed)`.

**Rationale**: `src/aatf/manifest.py` has `write_manifest(config: ExperimentConfig, seed: int) -> Path` which handles directory creation, provenance capture, and JSON writing.

---

## Decision 7: Defence choice in entrypoint

**Decision**: Use `NullDefence()` from `aatf.defence` as the default when lab is not running. If `SuricataDefence` is available (lab up), it can be swapped in.

**Rationale**: Constitution Principle I — traffic only inside lab. `NullDefence` returns `alerted=False` always — the experiment completes without live traffic. For a real run with `make lab-up`, user would instantiate `SuricataDefence`. For the single-command MVP, `NullDefence` allows the pipeline to complete end-to-end without requiring the lab.

**Alternative considered**: Auto-detect lab status and choose defence — deferred to avoid complexity; `NullDefence` is documented behaviour.

---

## Decision 8: Action executor in entrypoint

**Decision**: `execute_fn` is a no-op lambda `lambda action_id: None` when lab is not running. This avoids socket errors in the entrypoint while keeping `run_episode`'s interface satisfied.

**Rationale**: `ActionExecutor.execute()` would raise `ExternalTargetError` or connection error without a live lab. A no-op is safe and keeps the entrypoint runnable without Docker.

---

## Decision 9: attacker_class config field

**Decision**: Add `attacker_class: str = "RandomAttacker"` to `ExperimentConfig` and `config.yaml`.

**Rationale**: `config.yaml` currently has `episodes, seed, output_dir, ruleset_path, detection_threshold` — no `attacker_class`. The entrypoint needs it to dispatch to the correct attacker.

---

## Decision 10: Makefile run target

**Decision**: Update `Makefile` `run:` target from `$(PY) -m aatf` (the stub) to `$(PY) src/run_experiment.py`.

**Rationale**: Current run target calls `__main__.py` which prints "scaffold only". F25 replaces it with the real entrypoint.

---

## Decision 11: Context dimension for LinUCBAttacker

**Decision**: Derive `context_dim` at runtime from `len(build_context(initial_state))`.

**Rationale**: `build_context` returns a fixed-length numpy float32 array; its length can be inferred at startup by building one context vector from an initial `EpisodeState`.

---

## Decision 12: Attacker observe (update) in entrypoint

**Decision**: Track per-step contexts inside the `action_selector` closure using a list; after `run_episode` returns, zip steps with stored contexts to call `attacker.observe(action_id, ctx, reward)` for each step.

**Rationale**: `run_episode` doesn't call `attacker.observe` internally — the entrypoint is responsible for the update loop. Storing contexts in a closure list is the minimal correct approach.
