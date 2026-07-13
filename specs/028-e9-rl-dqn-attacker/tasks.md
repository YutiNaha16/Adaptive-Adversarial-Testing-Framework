# Tasks: RL/DQN Attacker (F28)

**Input**: Design documents from `specs/028-e9-rl-dqn-attacker/`
**Branch**: `028-e9-rl-dqn-attacker`
**Date**: 2026-07-13

**TDD approach**: Write ALL 10 tests FIRST (red), then implement (green).
**Baseline**: 335 passed → **Target**: ≥345 passed (+10)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label [US1], [US2], [US3]
- Setup/Foundational/Polish phases: no story label

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Record baseline, install PyTorch, update tooling for CPU-wheel compilation.

- [ ] T001 Record baseline test count: `cd src && pytest --tb=no -q 2>&1 | tail -5` — confirm 335 passed
- [ ] T002 Add `torch>=2.2` to `requirements.in` (after `scikit-learn>=1.4` line)
- [ ] T003 Update Makefile `lock` target to include `--extra-index-url https://download.pytorch.org/whl/cpu` in the `pip-compile` call
- [ ] T004 Run `make lock` (or equivalent pip-compile command) to recompile `requirements.txt` with torch CPU wheels and generate hashes — confirm torch appears in requirements.txt
- [ ] T005 Install updated requirements: `pip install --require-hashes -r requirements.txt` in .venv

**Checkpoint**: `python -c "import torch; print(torch.__version__)"` prints `2.x.x`

---

## Phase 2: Foundational (Red Phase — Tests First)

**Purpose**: Write all 10 contract tests so they fail with `ImportError` (red state). This is the TDD gate — no implementation until all tests are written and confirmed failing.

**⚠️ CRITICAL**: Do NOT implement `dqn_attacker.py` until T006 is complete and T007 confirms red state.

- [ ] T006 Create `tests/test_dqn_attacker.py` with ALL 10 contracts C-001..C-010 (exact content below):

```python
"""Contract tests C-001..C-010 for F28 RL/DQN Attacker."""
from __future__ import annotations

import collections
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# C-001: imports
# ---------------------------------------------------------------------------

def test_c001_imports():
    """C-001: All public symbols import without error."""
    from aatf.dqn_attacker import DQNAttacker, QNetwork, ReplayBuffer, DQNModel  # noqa: F401


# ---------------------------------------------------------------------------
# C-002: QNetwork forward pass
# ---------------------------------------------------------------------------

def test_c002_qnetwork_forward():
    """C-002: QNetwork maps (50,) → (15,) and (4,50) → (4,15)."""
    import torch
    from aatf.dqn_attacker import QNetwork

    net = QNetwork(state_dim=50, n_actions=15)
    x1 = torch.zeros(50)
    out1 = net(x1)
    assert out1.shape == torch.Size([15])

    x2 = torch.zeros(4, 50)
    out2 = net(x2)
    assert out2.shape == torch.Size([4, 15])


# ---------------------------------------------------------------------------
# C-003: ReplayBuffer push / len / sample
# ---------------------------------------------------------------------------

def test_c003_replay_buffer():
    """C-003: push 5 transitions, len==5, sample(3) returns 3 Transitions."""
    from aatf.dqn_attacker import ReplayBuffer, Transition

    buf = ReplayBuffer(capacity=2000)
    state = np.zeros(50, dtype=np.float32)
    for i in range(5):
        buf.push(state, i, 0.0, state)
    assert len(buf) == 5

    batch = buf.sample(3)
    assert len(batch) == 3
    assert all(isinstance(t, Transition) for t in batch)


# ---------------------------------------------------------------------------
# C-004: select_action returns valid action_id
# ---------------------------------------------------------------------------

def test_c004_select_action_valid():
    """C-004: select_action returns a str that is in available_ids."""
    from aatf.dqn_attacker import DQNModel

    model = DQNModel(seed=42)
    available = ["tcp_port_scan", "ssh_brute_force", "dns_exfil"]
    ctx = np.zeros(50, dtype=np.float32)
    result = model.select_action(available, ctx)
    assert isinstance(result, str)
    assert result in available


# ---------------------------------------------------------------------------
# C-005: action mask — unavailable actions never selected
# ---------------------------------------------------------------------------

def test_c005_action_mask():
    """C-005: select_action never returns an unavailable action across 50 calls."""
    from aatf.dqn_attacker import DQNModel

    model = DQNModel(seed=0, epsilon_end=0.0, epsilon_start=0.0)  # greedy
    available = ["tcp_port_scan", "icmp_ping_sweep"]
    ctx = np.zeros(50, dtype=np.float32)
    for _ in range(50):
        a = model.select_action(available, ctx)
        assert a in available


# ---------------------------------------------------------------------------
# C-006: observe before choose_action raises RuntimeError
# ---------------------------------------------------------------------------

def test_c006_observe_before_choose_raises():
    """C-006: DQNAttacker.observe() before choose_action() raises RuntimeError."""
    from aatf.dqn_attacker import DQNAttacker, DQNModel

    attacker = DQNAttacker(DQNModel(seed=42))
    ctx = np.zeros(50, dtype=np.float32)
    with pytest.raises(RuntimeError):
        attacker.observe("tcp_port_scan", ctx, 0.0)


# ---------------------------------------------------------------------------
# C-007: full step (choose_action → observe) completes without error
# ---------------------------------------------------------------------------

def test_c007_full_step():
    """C-007: choose_action then observe runs without error."""
    from aatf.dqn_attacker import DQNAttacker, DQNModel

    model = DQNModel(seed=42)
    attacker = DQNAttacker(model)
    ctx = np.zeros(50, dtype=np.float32)
    available = ["tcp_port_scan", "ssh_brute_force"]

    action = attacker.choose_action(available, ctx)
    assert action in available
    ctx2 = np.ones(50, dtype=np.float32) * 0.5
    attacker.observe(action, ctx2, 0.3)  # no error


# ---------------------------------------------------------------------------
# C-008: update() runs without error after buffer has ≥32 samples
# ---------------------------------------------------------------------------

def test_c008_train_step():
    """C-008: DQNModel.update() runs without error once buffer has ≥32 transitions."""
    from aatf.dqn_attacker import DQNModel

    model = DQNModel(seed=42, batch_size=32)
    state = np.zeros(50, dtype=np.float32)
    next_state = np.ones(50, dtype=np.float32) * 0.1
    available = ["tcp_port_scan"]

    for _ in range(33):
        model.update("tcp_port_scan", state, 0.5, next_state)


# ---------------------------------------------------------------------------
# C-009: cumulative_anomaly_exposure metric
# ---------------------------------------------------------------------------

def test_c009_cae_metric():
    """C-009: cumulative_anomaly_exposure([]) == 0.0; non-empty returns correct mean."""
    from aatf.metrics import cumulative_anomaly_exposure, EpisodeRecord
    from aatf.episode import StepRecord

    assert cumulative_anomaly_exposure([]) == 0.0

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
    assert abs(cae - 1.0) < 1e-9  # (0.3 + 0.7) / 1 = 1.0


# ---------------------------------------------------------------------------
# C-010: reproducibility — same seed → same action sequence
# ---------------------------------------------------------------------------

def test_c010_reproducibility():
    """C-010: Two DQNModel instances with same seed produce identical 10-action sequence."""
    from aatf.dqn_attacker import DQNModel

    available = ["tcp_port_scan", "ssh_brute_force", "dns_exfil"]
    ctx = np.zeros(50, dtype=np.float32)

    def run(seed):
        model = DQNModel(seed=seed)
        return [model.select_action(available, ctx) for _ in range(10)]

    assert run(42) == run(42)
    assert run(7) == run(7)
```

- [ ] T007 Run `pytest tests/test_dqn_attacker.py --tb=short -q` and confirm ALL 10 tests fail with `ImportError: cannot import name … from 'aatf.dqn_attacker'` (module does not exist yet)

**Checkpoint**: Red state confirmed. All 10 tests fail at import. No implementation written.

---

## Phase 3: User Story 1 — Adaptive DQN Action Selection (Priority: P1) 🎯 MVP

**Goal**: `DQNAttacker` behind the `Attacker` interface learns to select less-detectable actions using Q-learning.

**Independent Test**: `pytest tests/test_dqn_attacker.py::test_c001_imports tests/test_dqn_attacker.py::test_c002_qnetwork_forward tests/test_dqn_attacker.py::test_c003_replay_buffer tests/test_dqn_attacker.py::test_c004_select_action_valid tests/test_dqn_attacker.py::test_c005_action_mask tests/test_dqn_attacker.py::test_c006_observe_before_choose_raises tests/test_dqn_attacker.py::test_c007_full_step tests/test_dqn_attacker.py::test_c008_train_step tests/test_dqn_attacker.py::test_c010_reproducibility` → all PASS

### Implementation for User Story 1

- [ ] T008 [US1] Add `anomaly_score: float = 0.0` field to `StepRecord` dataclass in `src/aatf/episode.py` (after `reward: float` field; backward-compatible default). Then update the `StepRecord(...)` constructor call in the episode loop to pass `anomaly_score=detection.anomaly_score`.

  Exact change in episode.py — StepRecord definition becomes:
  ```python
  @dataclass(frozen=True)
  class StepRecord:
      action_id: str
      detected: bool
      stage_progress: bool
      reward: float
      anomaly_score: float = 0.0
  ```
  And the StepRecord construction in run_episode becomes:
  ```python
  steps.append(StepRecord(
      action_id=action_id,
      detected=detection.alerted,
      stage_progress=stage_progress,
      reward=reward,
      anomaly_score=detection.anomaly_score,
  ))
  ```

- [ ] T009 [US1] Add `anomaly_lambda: float = Field(ge=0.0, default=0.0)` to `ExperimentConfig` in `src/aatf/config.py` (after `attacker_class` field). Import `Field` from pydantic if not already imported.

- [ ] T010 [US1] Create `src/aatf/dqn_attacker.py` (~160 LOC) with exact content:

  ```python
  from __future__ import annotations

  import collections
  import random
  from typing import NamedTuple

  import numpy as np
  import torch
  import torch.nn as nn

  from aatf.action_library import REGISTRY
  from aatf.attacker import Attacker

  ALL_ACTION_IDS: list[str] = sorted([a.action_id for a in REGISTRY.list_actions()])

  Transition = collections.namedtuple("Transition", ["state", "action_idx", "reward", "next_state"])


  class QNetwork(nn.Module):
      def __init__(self, state_dim: int = 50, n_actions: int = 15) -> None:
          super().__init__()
          self.net = nn.Sequential(
              nn.Linear(state_dim, 64),
              nn.ReLU(),
              nn.Linear(64, 64),
              nn.ReLU(),
              nn.Linear(64, n_actions),
          )

      def forward(self, x: torch.Tensor) -> torch.Tensor:
          return self.net(x)


  class ReplayBuffer:
      def __init__(self, capacity: int = 2000) -> None:
          self._buffer: collections.deque = collections.deque(maxlen=capacity)

      def push(self, state: np.ndarray, action_idx: int, reward: float,
               next_state: np.ndarray) -> None:
          self._buffer.append(Transition(state, action_idx, reward, next_state))

      def sample(self, batch_size: int) -> list:
          return random.sample(self._buffer, batch_size)

      def __len__(self) -> int:
          return len(self._buffer)


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
      ) -> None:
          torch.manual_seed(seed)
          random.seed(seed)
          self._n_actions = n_actions
          self._gamma = gamma
          self._batch_size = batch_size
          self._target_update_freq = target_update_freq
          self._epsilon = epsilon_start
          self._epsilon_end = epsilon_end
          self._epsilon_decay = (epsilon_start - epsilon_end) / epsilon_decay_steps
          self.online_net = QNetwork(state_dim, n_actions)
          self.target_net = QNetwork(state_dim, n_actions)
          self.target_net.load_state_dict(self.online_net.state_dict())
          self.target_net.eval()
          self.buffer = ReplayBuffer(buffer_capacity)
          self.optimizer = torch.optim.Adam(self.online_net.parameters(), lr=lr)
          self._step_count = 0
          self._grad_step_count = 0

      def select_action(self, available_ids: list[str], state: np.ndarray) -> str:
          x = torch.tensor(state, dtype=torch.float32)
          with torch.no_grad():
              q = self.online_net(x)
          mask = torch.full((self._n_actions,), float("-inf"))
          avail_idxs = [ALL_ACTION_IDS.index(a) for a in available_ids if a in ALL_ACTION_IDS]
          for idx in avail_idxs:
              mask[idx] = q[idx]
          self._step_count += 1
          self._epsilon = max(self._epsilon_end, self._epsilon - self._epsilon_decay)
          if random.random() < self._epsilon:
              return random.choice(available_ids)
          return ALL_ACTION_IDS[int(torch.argmax(mask).item())]

      def update(self, action_id: str, state: np.ndarray, reward: float,
                 next_state: np.ndarray) -> None:
          action_idx = ALL_ACTION_IDS.index(action_id)
          self.buffer.push(state.astype(np.float32), action_idx, reward,
                           next_state.astype(np.float32))
          if len(self.buffer) < self._batch_size:
              return
          batch = self.buffer.sample(self._batch_size)
          states = torch.tensor(np.array([t.state for t in batch]), dtype=torch.float32)
          actions = torch.tensor([t.action_idx for t in batch], dtype=torch.long)
          rewards = torch.tensor([t.reward for t in batch], dtype=torch.float32)
          next_states = torch.tensor(
              np.array([t.next_state for t in batch]), dtype=torch.float32
          )
          with torch.no_grad():
              target_q = rewards + self._gamma * self.target_net(next_states).max(1).values
          current_q = self.online_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)
          loss = nn.functional.mse_loss(current_q, target_q)
          self.optimizer.zero_grad()
          loss.backward()
          self.optimizer.step()
          self._grad_step_count += 1
          if self._grad_step_count % self._target_update_freq == 0:
              self.target_net.load_state_dict(self.online_net.state_dict())


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
          self._model.update(self._last_action_id, self._last_state, reward, context)
          self._last_state = context.copy()
          self._last_action_id = action_id
  ```

- [ ] T011 [US1] Run US1 contracts: `pytest tests/test_dqn_attacker.py::test_c001_imports tests/test_dqn_attacker.py::test_c002_qnetwork_forward tests/test_dqn_attacker.py::test_c003_replay_buffer tests/test_dqn_attacker.py::test_c004_select_action_valid tests/test_dqn_attacker.py::test_c005_action_mask tests/test_dqn_attacker.py::test_c006_observe_before_choose_raises tests/test_dqn_attacker.py::test_c007_full_step tests/test_dqn_attacker.py::test_c008_train_step tests/test_dqn_attacker.py::test_c010_reproducibility -v` — confirm all 9 PASS

**Checkpoint**: C-001..C-008, C-010 green. DQNAttacker fully functional and reproducible.

---

## Phase 4: User Story 2 — CAE Stealth Metric (Priority: P2)

**Goal**: `cumulative_anomaly_exposure()` metric measures mean total anomaly score per episode, enabling empirical stealth comparison between DQN and Random attackers.

**Independent Test**: `pytest tests/test_dqn_attacker.py::test_c009_cae_metric -v` → PASS

### Implementation for User Story 2

- [ ] T012 [US2] Add `cumulative_anomaly_exposure(records: list[EpisodeRecord]) -> float` to `src/aatf/metrics.py`:

  Add at the end of the file (after `robustness_score`):
  ```python
  def cumulative_anomaly_exposure(records: list[EpisodeRecord]) -> float:
      if not records:
          return 0.0
      return sum(sum(s.anomaly_score for s in r.steps) for r in records) / len(records)
  ```

  Also add `cumulative_anomaly_exposure` to the module's `__all__` list if one exists.

- [ ] T013 [US2] Run CAE contract: `pytest tests/test_dqn_attacker.py::test_c009_cae_metric -v` — confirm PASS

**Checkpoint**: All 10 contracts C-001..C-010 now pass.

---

## Phase 5: User Story 3 — Drop-in Attacker Swap via Config (Priority: P3)

**Goal**: `DQNAttacker` is selectable via `attacker_class: DQNAttacker` in YAML config, with reward shaping applied automatically and CAE printed in the experiment summary.

**Independent Test**: `python src/run_experiment.py --config config_dqn.yaml` completes without error and prints `Cumul. Anomaly Exp:` line.

### Implementation for User Story 3

- [ ] T014 [US3] Modify `src/run_experiment.py` — add DQN imports, factory entry, reward shaping, and CAE output:

  **Step A — imports** (add after existing attacker imports):
  ```python
  from aatf.dqn_attacker import DQNAttacker, DQNModel
  ```
  And extend the metrics import to include `cumulative_anomaly_exposure`.

  **Step B — add DQNAttacker to `_ATTACKER_REGISTRY`**:
  ```python
  "DQNAttacker": lambda seed, ctx_dim, n_actions: DQNAttacker(
      DQNModel(n_actions=n_actions, state_dim=ctx_dim, seed=seed)
  ),
  ```

  **Step C — reward shaping in post-episode attacker.observe() loop**:
  Replace the existing `attacker.observe(step.action_id, ctx, step.reward)` call with:
  ```python
  for step, ctx in zip(result.steps, step_contexts, strict=False):
      shaped = step.reward - config.anomaly_lambda * step.anomaly_score
      attacker.observe(step.action_id, ctx, shaped)
  ```

  **Step D — print CAE in summary block** (add after the existing Detection Rate / Robustness Score prints):
  ```python
  cae = cumulative_anomaly_exposure(records)
  print(f"Cumul. Anomaly Exp: {cae:.4f}")
  ```

- [ ] T015 [US3] Create `config_dqn.yaml` at repo root with exact content:
  ```yaml
  episodes: 200
  seed: 42
  output_dir: outputs/dqn_run_001
  ruleset_path: /etc/suricata/rules
  detection_threshold: 0.5
  attacker_class: DQNAttacker
  anomaly_lambda: 1.0
  ```

- [ ] T016 [US3] Run smoke test: `python src/run_experiment.py --config config_dqn.yaml 2>&1 | head -20` — verify no ImportError and `DQNAttacker` appears in the header

**Checkpoint**: All 3 user stories fully implemented and independently passing.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Lint, full suite validation, commit, merge, push.

- [ ] T017 Run ruff on all modified/new files: `ruff check src/aatf/dqn_attacker.py tests/test_dqn_attacker.py src/aatf/episode.py src/aatf/config.py src/aatf/metrics.py src/run_experiment.py --fix` — fix any lint errors
- [ ] T018 Run full test suite: `cd src && pytest --tb=short -q` — confirm ≥345 passed (baseline 335 + 10 new contracts)
- [ ] T019 Run ruff on entire src tree: `cd src && ruff check .` — confirm 0 errors
- [ ] T020 Commit all changes with message: `feat(F28): add DQNAttacker with replay buffer, epsilon-greedy, CAE metric`
- [ ] T021 Merge `028-e9-rl-dqn-attacker` into `main` and push to origin

**Checkpoint**: CI passes, ≥345 tests green, F28 merged and pushed.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational Red (Phase 2)**: Depends on Phase 1 complete (torch installed)
- **US1 (Phase 3)**: Depends on Phase 2 complete (all tests written, red confirmed)
- **US2 (Phase 4)**: Can start in parallel with US1 (touches only `metrics.py`) — but test C-009 needs `StepRecord.anomaly_score` from T008
- **US3 (Phase 5)**: Depends on US1 complete (dqn_attacker.py must exist), and US2 complete (CAE must exist)
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Blocked only by red phase (T006, T007) — no story dependencies
- **US2 (P2)**: Requires `StepRecord.anomaly_score` from T008 (US1 first step) for C-009 test to pass
- **US3 (P3)**: Requires US1 (DQNAttacker) and US2 (cumulative_anomaly_exposure) both complete

### Within Phase 3 (US1) — Sequential Order

1. T008 — episode.py (StepRecord change — prerequisite for C-009 to compile correctly)
2. T009 — config.py (anomaly_lambda field — prerequisite for T014)
3. T010 — dqn_attacker.py (core implementation — all C-001..C-008, C-010 go green)
4. T011 — verify 9/10 contracts green

### Parallel Opportunities

- T008 [episode.py] and T009 [config.py] can run in parallel (different files)
- T012 [metrics.py] can run in parallel with T010 [dqn_attacker.py] (different files)
- T017 [ruff] and T018 [pytest] are sequential (fix lint first, then verify suite)

---

## Parallel Example: Phase 3 (US1)

```bash
# These two tasks can run simultaneously:
Task T008: Add anomaly_score to StepRecord in src/aatf/episode.py
Task T009: Add anomaly_lambda to ExperimentConfig in src/aatf/config.py

# Then T010 depends on T008 completing first (references anomaly_score field):
Task T010: Create src/aatf/dqn_attacker.py

# T012 can run in parallel with T010 (different file):
Task T012: Add cumulative_anomaly_exposure to src/aatf/metrics.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (torch installed)
2. Complete Phase 2: Red phase (10 tests written, all failing)
3. Complete Phase 3: US1 (T008–T011) → C-001..C-008, C-010 green
4. **STOP and VALIDATE**: 9 contracts pass, DQNAttacker learning correctly
5. Then add US2 + US3

### Incremental Delivery

1. Phase 1 → torch in venv
2. Phase 2 → red state confirmed (TDD gate)
3. Phase 3 (US1) → DQNAttacker core works, 9 contracts green
4. Phase 4 (US2) → CAE metric works, 10/10 contracts green
5. Phase 5 (US3) → run_experiment.py wired up, smoke test passes
6. Phase 6 → full suite ≥345, merged

---

## Notes

- **Constitution I**: dqn_attacker.py only selects action IDs — no payloads. ActionExecutor handles defanging.
- **Constitution II**: `torch.manual_seed(seed)` + `random.seed(seed)` called in `DQNModel.__init__` — C-010 validates this.
- **Constitution III**: `DQNAttacker` behind `Attacker` ABC — zero DQN coupling in episode loop.
- **StepRecord change** is backward-compatible: `anomaly_score: float = 0.0` default preserves all 335 existing tests.
- **ExperimentConfig change** is backward-compatible: `anomaly_lambda: float = 0.0` default means existing `config.yaml` needs no changes.
- Do NOT import `torch` at module level in files that don't need it — keep the import isolated to `dqn_attacker.py`.
- If `make lock` fails due to torch wheel resolution, run manually: `pip-compile --generate-hashes --allow-unsafe --extra-index-url https://download.pytorch.org/whl/cpu --output-file=requirements.txt requirements.in`
