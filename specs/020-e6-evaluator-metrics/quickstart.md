# Quickstart: Evaluator & Metrics (F20)

**Feature**: 020-e6-evaluator-metrics
**Date**: 2026-07-11

## Integration Scenarios

### Scenario 1: Compute detection rate from a completed run

```python
from aatf.episode import StepRecord
from aatf.metrics import EpisodeRecord, detection_rate

# Simulate 3 episodes of run data
records = [
    EpisodeRecord(
        attacker_class="LinUCBAttacker",
        seed=42,
        steps=[
            StepRecord(action_id="tcp_port_scan", detected=True,  stage_progress=False, reward=-1.0),
            StepRecord(action_id="ssh_brute",     detected=False, stage_progress=True,  reward=1.0),
        ],
        total_reward=0.0,
        completed=False,
        episode_index=0,
    ),
    EpisodeRecord(
        attacker_class="LinUCBAttacker",
        seed=42,
        steps=[
            StepRecord(action_id="tcp_port_scan", detected=False, stage_progress=True,  reward=1.0),
            StepRecord(action_id="dns_enum",      detected=False, stage_progress=True,  reward=1.0),
        ],
        total_reward=2.0,
        completed=False,
        episode_index=1,
    ),
]

dr = detection_rate(records)
# 1 detected out of 4 total steps → 0.25
assert abs(dr - 0.25) < 1e-9
```

---

### Scenario 2: Measure steady-state robustness

```python
from aatf.metrics import EpisodeRecord, robustness_score

# Last 5 episodes of a long run: none detected → attacker has converged
recent_records = [...]  # 10+ episodes
score = robustness_score(recent_records, window=5)
# If score < 0.2: defence has been largely bypassed in steady state
```

---

### Scenario 3: Compare LinUCB vs RandomAttacker (RQ1)

```python
from aatf.metrics import adaptation_gain

linucb_records   = [...]  # episodes run with LinUCBAttacker
random_records   = [...]  # same scenario with RandomAttacker

gain = adaptation_gain(
    baseline_records=random_records,
    learner_records=linucb_records,
)
# gain > 0 → LinUCB evades more (lower detection rate)
# gain >= 15.0 → Phase 1 gate criterion met
print(f"Adaptation Gain: {gain:.1f} pp")
```

---

### Scenario 4: Find when LinUCB started converging

```python
from aatf.metrics import convergence_episodes

# records: all LinUCB episodes in order
ep_idx = convergence_episodes(linucb_records, threshold=0.5, window=5)
if ep_idx is not None:
    print(f"Attacker converged at episode {ep_idx}")
else:
    print("Attacker never sustained evasion below 50% detection rate")
```

---

## Running Tests

```bash
cd /home/yuti/Adaptive-Adversarial-Testing-Framework
source .venv/bin/activate
cd src && pytest ../tests/test_metrics.py -v
```

Expected: 17 tests (C-001 to C-017), all pass.

Full suite (verify no regressions):
```bash
cd src && pytest ../tests/ --tb=short -q 2>&1 | tail -5
```
