# Quickstart: RL/DQN Attacker (F28)

## Scenario 1: Basic usage — choose and observe

```python
from aatf.dqn_attacker import DQNModel, DQNAttacker
from aatf.context_vector import EpisodeState, build_context

model = DQNModel(n_actions=15, state_dim=50, seed=42)
attacker = DQNAttacker(model)

state = EpisodeState()
ctx = build_context(state)
available = ["tcp_port_scan", "ssh_brute_force", "dns_exfil"]

# Step 1: choose
action_id = attacker.choose_action(available, ctx)
print(action_id)  # one of the three available actions

# Step 2: (execute + observe defence — in real loop this is done by run_episode)
shaped_reward = 0.5 - 1.0 * 0.3  # reward=0.5, anomaly_score=0.3, lambda=1.0
attacker.observe(action_id, ctx, shaped_reward)
```

---

## Scenario 2: Run 200-episode DQN experiment

```bash
source .venv/bin/activate
python src/run_experiment.py --config config_dqn.yaml
```

Expected output:
```
Adaptive Adversarial Testing Framework
======================================
Mode     : Simulation (NullDefence)
Attacker : DQNAttacker
Episodes : 200
Seed     : 42
--------------------------------------
Running 200 episodes...
--------------------------------------
Detection Rate   : 0.xxxx
Robustness Score : 0.xxxx
Cumul. Anomaly Exp: 0.xxxx
Report written   : outputs/dqn_run_001/report_*.md
Manifest written : outputs/dqn_run_001/run_manifest_*.json
```

---

## Scenario 3: Compute CAE metric

```python
from aatf.metrics import cumulative_anomaly_exposure, EpisodeRecord
from aatf.episode import StepRecord

# Build synthetic records for testing
steps = [
    StepRecord(action_id="tcp_port_scan", detected=False,
               stage_progress=True, reward=0.5, anomaly_score=0.3),
    StepRecord(action_id="ssh_brute_force", detected=True,
               stage_progress=False, reward=-0.5, anomaly_score=0.7),
]
record = EpisodeRecord(attacker_class="DQNAttacker", seed=42,
                       steps=steps, total_reward=0.0,
                       completed=False, episode_index=0)

cae = cumulative_anomaly_exposure([record])
print(cae)  # 1.0 = (0.3 + 0.7) / 1 episode
```

---

## Scenario 4: Reproducibility check

```python
from aatf.dqn_attacker import DQNModel, DQNAttacker
import numpy as np

def run_sequence(seed):
    model = DQNModel(seed=seed)
    attacker = DQNAttacker(model)
    ctx = np.zeros(50, dtype=np.float32)
    available = ["tcp_port_scan", "ssh_brute_force"]
    actions = [attacker.choose_action(available, ctx) for _ in range(5)]
    return actions

assert run_sequence(42) == run_sequence(42)
print("Reproducible ✓")
```

---

## File Locations

| File | Purpose |
|------|---------|
| `src/aatf/dqn_attacker.py` | QNetwork, ReplayBuffer, DQNModel, DQNAttacker (~160 LOC) |
| `src/aatf/episode.py` | +anomaly_score field in StepRecord |
| `src/aatf/config.py` | +anomaly_lambda field in ExperimentConfig |
| `src/aatf/metrics.py` | +cumulative_anomaly_exposure() |
| `src/run_experiment.py` | +DQNAttacker factory, reward shaping, CAE output |
| `tests/test_dqn_attacker.py` | 10 TDD contracts C-001..C-010 |
| `config_dqn.yaml` | episodes=200, DQNAttacker, anomaly_lambda=1.0 |
| `requirements.in` | +torch>=2.2 |

## Test Command

```bash
source .venv/bin/activate
pytest tests/test_dqn_attacker.py -v
```

## Expected Test Output (green phase)

```
tests/test_dqn_attacker.py::test_c001_imports PASSED
tests/test_dqn_attacker.py::test_c002_qnetwork_forward PASSED
tests/test_dqn_attacker.py::test_c003_replay_buffer PASSED
tests/test_dqn_attacker.py::test_c004_select_action_valid PASSED
tests/test_dqn_attacker.py::test_c005_action_mask PASSED
tests/test_dqn_attacker.py::test_c006_observe_before_choose_raises PASSED
tests/test_dqn_attacker.py::test_c007_full_step PASSED
tests/test_dqn_attacker.py::test_c008_train_step PASSED
tests/test_dqn_attacker.py::test_c009_cae_metric PASSED
tests/test_dqn_attacker.py::test_c010_reproducibility PASSED
10 passed
```
