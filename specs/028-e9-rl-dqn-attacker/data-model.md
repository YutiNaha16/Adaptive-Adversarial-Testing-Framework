# Data Model: RL/DQN Attacker (F28)

## Module: `src/aatf/dqn_attacker.py`

---

### Constants

```python
ALL_ACTION_IDS: list[str] = sorted([a.action_id for a in REGISTRY.list_actions()])
# ['dns_exfil', 'dns_subdomain_enum', 'dns_zone_transfer', 'ftp_brute_force',
#  'http_basic_brute', 'http_dir_scan', 'http_exfil', 'http_sqli_probe',
#  'http_xss_probe', 'icmp_ping_sweep', 'ssh_brute_force', 'ssh_user_enum',
#  'ssh_version_probe', 'tcp_port_scan', 'udp_sweep']
# N_ACTIONS = 15
```

---

### 1. Transition (namedtuple)

```python
Transition = collections.namedtuple(
    'Transition', ['state', 'action_idx', 'reward', 'next_state']
)
```

| Field | Type | Description |
|-------|------|-------------|
| state | np.ndarray (50,) float32 | Context vector at time of action |
| action_idx | int [0, 14] | Index into ALL_ACTION_IDS |
| reward | float | Shaped reward (already includes anomaly penalty) |
| next_state | np.ndarray (50,) float32 | Context vector after action executed |

---

### 2. QNetwork (nn.Module)

**Architecture**: `Linear(50→64) → ReLU → Linear(64→64) → ReLU → Linear(64→15)`

```python
class QNetwork(nn.Module):
    def __init__(self, state_dim: int = 50, n_actions: int = 15) -> None: ...
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # input: (batch, state_dim) or (state_dim,)
        # output: (batch, n_actions) or (n_actions,)
```

**Parameters**: ~7k (50×64 + 64 + 64×64 + 64 + 64×15 + 15 = 7,311)

---

### 3. ReplayBuffer

```python
class ReplayBuffer:
    def __init__(self, capacity: int = 2000) -> None:
        self._buffer: collections.deque[Transition]  # maxlen=capacity

    def push(self, state, action_idx, reward, next_state) -> None: ...
    def sample(self, batch_size: int) -> list[Transition]: ...  # random.sample
    def __len__(self) -> int: ...
```

**State transitions**:
```
[empty] --push()×n--> [n transitions stored]
        --sample(k)-->  ValueError if len < k (guard in DQNModel)
```

---

### 4. DQNModel

```python
class DQNModel:
    def __init__(
        self,
        n_actions: int = 15,
        state_dim: int = 50,
        seed: int = 42,
        lr: float = 1e-3,
        gamma: float = 0.95,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.1,
        epsilon_decay_steps: int = 500,
        buffer_capacity: int = 2000,
        batch_size: int = 32,
        target_update_freq: int = 10,
    ) -> None
```

**State**:
| Field | Type | Description |
|-------|------|-------------|
| online_net | QNetwork | Updated by gradient steps |
| target_net | QNetwork | Frozen copy; updated every target_update_freq grad steps |
| buffer | ReplayBuffer | Stores transitions |
| optimizer | Adam | lr=lr, params=online_net.parameters() |
| _step_count | int | Increments on every select_action call |
| _grad_step_count | int | Increments on every gradient update |
| epsilon | float | Current exploration rate |

**Methods**:

```python
def select_action(self, available_ids: list[str], state: np.ndarray) -> str:
    # 1. Convert state to tensor
    # 2. Q-values = online_net(state_tensor) with no_grad
    # 3. Mask unavailable actions to -inf
    # 4. Epsilon-greedy: random if uniform() < epsilon, else argmax
    # 5. Increment _step_count; update epsilon (linear decay)
    # 6. Return ALL_ACTION_IDS[chosen_idx]

def update(self, action_id: str, state: np.ndarray, reward: float,
           next_state: np.ndarray) -> None:
    # 1. Push Transition to buffer
    # 2. If len(buffer) < batch_size: return
    # 3. Sample batch of 32
    # 4. Compute TD targets: r + gamma * max(target_net(next_states))
    # 5. Loss = MSE(online_net(states)[action_idxs], targets.detach())
    # 6. optimizer.zero_grad(); loss.backward(); optimizer.step()
    # 7. Increment _grad_step_count
    # 8. If _grad_step_count % target_update_freq == 0: hard copy online→target
```

**Epsilon schedule** (linear decay):
```
epsilon(t) = max(epsilon_end, epsilon_start - t * (epsilon_start - epsilon_end) / epsilon_decay_steps)
```

---

### 5. DQNAttacker (implements Attacker ABC)

```python
class DQNAttacker(Attacker):
    def __init__(self, model: DQNModel) -> None:
        self._model = model
        self._last_state: np.ndarray | None = None
        self._last_action_id: str | None = None

    def choose_action(self, available: list[str], context: np.ndarray) -> str:
        self._last_state = context.copy()
        action_id = self._model.select_action(available, context)
        self._last_action_id = action_id
        return action_id

    def observe(self, action_id: str, context: np.ndarray, reward: float) -> None:
        if self._last_state is None:
            raise RuntimeError("observe() called before choose_action()")
        self._model.update(self._last_action_id, self._last_state, reward,
                           next_state=context)
        self._last_state = context.copy()
        self._last_action_id = action_id
```

**Call-order constraint**: `choose_action` MUST precede `observe`. First `observe` without
preceding `choose_action` raises `RuntimeError`.

**Note on `action_id` arg to `observe()`**: The Attacker interface passes the action_id
that was actually executed (same as what `choose_action` returned, since the loop executes
it immediately). DQNAttacker uses `self._last_action_id` for the buffer push, then
overwrites it with the incoming `action_id` for the next step. In practice these are the
same value within one step, but the update is kept for correctness in edge cases.

---

## Changes to Existing Modules

### `src/aatf/episode.py` — StepRecord

Add `anomaly_score: float = 0.0` field (backward-compatible default):

```python
@dataclass(frozen=True)
class StepRecord:
    action_id: str
    detected: bool
    stage_progress: bool
    reward: float
    anomaly_score: float = 0.0  # NEW: from DetectionResult.anomaly_score
```

Episode loop populates it:
```python
steps.append(StepRecord(
    action_id=action_id,
    detected=result.detected,
    stage_progress=result.stage_progress,
    reward=reward,
    anomaly_score=detection.anomaly_score,  # NEW
))
```

### `src/aatf/config.py` — ExperimentConfig

Add `anomaly_lambda: float = 0.0` (backward-compatible default):

```python
class ExperimentConfig(BaseModel):
    ...
    attacker_class: str = "RandomAttacker"
    anomaly_lambda: float = Field(ge=0.0, default=0.0)  # NEW
```

### `src/aatf/metrics.py` — cumulative_anomaly_exposure

```python
def cumulative_anomaly_exposure(records: list[EpisodeRecord]) -> float:
    if not records:
        return 0.0
    return sum(
        sum(s.anomaly_score for s in r.steps) for r in records
    ) / len(records)
```

### `src/run_experiment.py` — DQN factory + shaping + CAE output

```python
# In _ATTACKER_REGISTRY:
"DQNAttacker": lambda seed, ctx_dim, n_actions: DQNAttacker(
    DQNModel(n_actions=n_actions, state_dim=ctx_dim, seed=seed)
),

# In episode post-processing loop:
for step, ctx in zip(result.steps, step_contexts, strict=False):
    shaped = step.reward - config.anomaly_lambda * step.anomaly_score
    attacker.observe(step.action_id, ctx, shaped)

# In summary print block:
cae = cumulative_anomaly_exposure(records)
print(f"Cumul. Anomaly Exp: {cae:.4f}")
```

---

## Data Flow

```
EpisodeState (50-dim context)
    │
    ├──choose_action()──> DQNAttacker
    │                         │
    │                    DQNModel.select_action()
    │                         │ epsilon-greedy on masked Q-values
    │                         ▼
    │                    action_id (str)
    │
    ├──execute_fn()──> (defanged traffic)
    │
    ├──defence.observe()──> DetectionResult
    │                           ├── .alerted → StepRecord.detected
    │                           └── .anomaly_score → StepRecord.anomaly_score
    │
    ├──compute_reward()──> StepRecord.reward
    │
    └──(after episode)
           shaped_reward = step.reward - λ × step.anomaly_score
           DQNAttacker.observe(action_id, ctx, shaped_reward)
               │
           DQNModel.update() → push to ReplayBuffer → sample batch → TD update
               │
           QNetwork weights updated (online_net)
               │ every 10 grad steps
           target_net ← online_net (hard copy)
```
