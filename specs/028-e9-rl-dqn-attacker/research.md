# Research: RL/DQN Attacker (F28)

## Decision 1: Neural Network Framework — PyTorch

**Decision**: `torch>=2.2` (CPU-only wheels)

**Rationale**:
- DQN requires automatic differentiation and a neural network — numpy manual backprop is
  fragile and not maintainable. PyTorch is the industry standard for RL research.
- CPU-only wheels are ~500MB (vs 2GB for CUDA). Sufficient for 50-dim × 15-action MLP.
- `torch.manual_seed(seed)` provides exact reproducibility under Principle II.
- PyTorch 2.2 (Jan 2024) is stable with Python 3.12 and has a CPU wheel on the PyTorch index.

**Install strategy**: pip-tools does not support `--index-url` in requirements.in for a
single package. Solution: Add `torch>=2.2` to requirements.in; add an `.pip_extra_index`
note in Makefile's `lock` target:
```
pip-compile --generate-hashes --allow-unsafe \
  --extra-index-url https://download.pytorch.org/whl/cpu \
  --output-file=requirements.txt requirements.in
```
CI workflow also needs `--extra-index-url` for `pip install --require-hashes`.

**Alternatives considered**:
- **Numpy-only linear Q**: Rejected — not real DQN, doesn't scale, manual backprop is fragile.
- **JAX**: Heavier ecosystem, less familiar, no advantage for this scope.
- **TensorFlow**: Heavier, PyTorch is more natural for RL research.

---

## Decision 2: StepRecord Revision (episode.py change required)

**Decision**: Add `anomaly_score: float = 0.0` to `StepRecord` in `episode.py`.

**Rationale**: The original plan said "no changes to episode.py" but source inspection
reveals this is impossible without it. The anomaly_score is produced by `defence.observe()`
inside the episode loop (line 76) but discarded — only `detection.alerted` is used. Without
storing it in `StepRecord`, neither `cumulative_anomaly_exposure()` nor DQN reward shaping
can access per-step anomaly values after the episode returns.

**Change is backward-compatible**: `anomaly_score: float = 0.0` as a dataclass field with
a default means all existing code that creates `StepRecord` without this field continues
to work. All 335 existing tests stay green.

**In episode.py**: Change StepRecord creation from:
```python
steps.append(StepRecord(action_id=action_id, detected=result.detected,
    stage_progress=result.stage_progress, reward=reward))
```
to:
```python
steps.append(StepRecord(action_id=action_id, detected=result.detected,
    stage_progress=result.stage_progress, reward=reward,
    anomaly_score=detection.anomaly_score))
```

**Alternatives considered**:
- **Recording Defence wrapper**: Wrap the defence in run_experiment.py to capture anomaly
  scores as side effects. Rejected — creates hidden state and temporal coupling that's hard
  to test and confusing for future readers.
- **Separate anomaly log list**: Track anomaly scores in run_experiment.py alongside steps.
  Rejected — data already lives in StepRecord (once we add the field); separate list
  creates synchronisation bugs.

---

## Decision 3: ExperimentConfig — Add anomaly_lambda

**Decision**: Add `anomaly_lambda: float = Field(ge=0.0, default=0.0)` to `ExperimentConfig` in `config.py`.

**Rationale**: The reward shaping formula `reward - lambda * anomaly_score` needs lambda to
be configurable per-run. With default=0.0, existing configs (including `config.yaml`) are
unaffected — no shaping applied when anomaly_lambda=0. DQN config sets it to 1.0.

**config_dqn.yaml** declares `anomaly_lambda: 1.0`.

---

## Decision 4: DQN Architecture — 2-Layer MLP, Hard Target Copy

**Network**: `Linear(50→64) → ReLU → Linear(64→64) → ReLU → Linear(64→15)`

**Rationale**: 50-dim input (CONTEXT_DIM), 15 outputs (one per registry action), 2 hidden
layers of 64 units. Small enough for fast CPU training on 200 episodes of 10 steps each
(2000 total steps). No batch normalisation needed at this scale.

**Target network**: Hard copy every 10 gradient steps (not Polyak/soft update). Simpler,
sufficient for small action space, avoids hyperparameter tuning of tau.

**Replay buffer**: 2000 transitions (deque, FIFO eviction). At 10 steps/episode × 200
episodes = 2000 transitions — the buffer fills exactly once. Ensures old experience is
eventually discarded as the policy improves.

**Epsilon decay**: Linear from 1.0 → 0.1 over 500 steps. With 200 episodes × ~10 steps
= ~2000 total steps, epsilon reaches 0.1 at step 500 and stays there for the remaining
1500 steps. Gives adequate exploration early, then exploits learned Q-values.

---

## Decision 5: Reward Shaping — Applied in run_experiment.py, Not Inside Attacker

**Decision**: Shape reward externally in run_experiment.py before calling `attacker.observe()`.

```python
shaped_reward = step.reward - config.anomaly_lambda * step.anomaly_score
attacker.observe(step.action_id, ctx, shaped_reward)
```

**Rationale**: The `Attacker.observe()` interface accepts `reward: float` — the shaped value
IS the reward from the attacker's perspective. Shaping outside the attacker keeps
`DQNAttacker.observe()` clean and matches the interface contract. Any other attacker
(RandomAttacker, LinUCBAttacker) will also receive the shaped reward when anomaly_lambda>0,
which is correct behaviour — they just won't use it meaningfully.

---

## Decision 6: ALL_ACTION_IDS Index (confirmed from source)

```python
ALL_ACTION_IDS = sorted([a.action_id for a in REGISTRY.list_actions()])
# ['dns_exfil', 'dns_subdomain_enum', 'dns_zone_transfer', 'ftp_brute_force',
#  'http_basic_brute', 'http_dir_scan', 'http_exfil', 'http_sqli_probe',
#  'http_xss_probe', 'icmp_ping_sweep', 'ssh_brute_force', 'ssh_user_enum',
#  'ssh_version_probe', 'tcp_port_scan', 'udp_sweep']
# 15 actions, indices 0–14
```

---

## Constitution Check

| Principle | Status | Evidence |
|-----------|--------|---------|
| I — Safety & Isolation | ✅ PASS | DQN only selects action IDs; no payload generation; ActionExecutor is defanged |
| II — Reproducibility | ✅ PASS | `torch.manual_seed(seed)` + `random.seed(seed)` for replay sampling |
| III — Pluggable Attacker | ✅ PASS | `DQNAttacker(Attacker)` — zero coupling to DQN from episode loop |
| IV — Scientific Validity | ✅ PASS | SC-001: CAE(DQN) < CAE(Random) after 200 episodes |
| V — Explainability | ✅ PASS | Existing explainability engine unaffected; CAE adds observability |
| VI — Observability | ✅ PASS | anomaly_score stored in StepRecord → propagates to EpisodeRecord |
| VII — Phased Delivery | ✅ PASS | Phase 1 gate passed; E9 authorized |

**GATE: CLEARED. No NON-NEGOTIABLE violations.**

**Note on episode.py change**: Adding `anomaly_score: float = 0.0` to `StepRecord` is a
backward-compatible additive change, not a breaking refactor. It does not violate any
constitution principle.
