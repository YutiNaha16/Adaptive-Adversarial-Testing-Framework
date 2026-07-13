"""Contract tests C-001..C-010 for F28 RL/DQN Attacker."""

from __future__ import annotations

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# C-001: imports
# ---------------------------------------------------------------------------


def test_c001_imports():
    """C-001: All public symbols import without error."""
    from aatf.dqn_attacker import DQNAttacker, DQNModel, QNetwork, ReplayBuffer  # noqa: F401


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

    for _ in range(33):
        model.update("tcp_port_scan", state, 0.5, next_state)


# ---------------------------------------------------------------------------
# C-009: cumulative_anomaly_exposure metric
# ---------------------------------------------------------------------------


def test_c009_cae_metric():
    """C-009: cumulative_anomaly_exposure([]) == 0.0; non-empty returns correct mean."""
    from aatf.episode import StepRecord
    from aatf.metrics import EpisodeRecord, cumulative_anomaly_exposure

    assert cumulative_anomaly_exposure([]) == 0.0

    steps = [
        StepRecord(
            action_id="tcp_port_scan",
            detected=False,
            stage_progress=True,
            reward=0.5,
            anomaly_score=0.3,
        ),
        StepRecord(
            action_id="ssh_brute_force",
            detected=True,
            stage_progress=False,
            reward=-0.5,
            anomaly_score=0.7,
        ),
    ]
    record = EpisodeRecord(
        attacker_class="DQNAttacker",
        seed=42,
        steps=steps,
        total_reward=0.0,
        completed=False,
        episode_index=0,
    )
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
