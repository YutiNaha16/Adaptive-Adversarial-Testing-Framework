"""DQN attacker: QNetwork, ReplayBuffer, DQNModel, DQNAttacker (F28 / Epic E9)."""

from __future__ import annotations

import collections
import random

import numpy as np
import torch
import torch.nn as nn

from aatf.action_library import REGISTRY
from aatf.attacker import Attacker
from aatf.seeding import seed_everything

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

    def push(
        self, state: np.ndarray, action_idx: int, reward: float, next_state: np.ndarray
    ) -> None:
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
        seed_everything(seed)
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

    def update(
        self, action_id: str, state: np.ndarray, reward: float, next_state: np.ndarray
    ) -> None:
        action_idx = ALL_ACTION_IDS.index(action_id)
        self.buffer.push(
            state.astype(np.float32), action_idx, reward, next_state.astype(np.float32)
        )
        if len(self.buffer) < self._batch_size:
            return
        batch = self.buffer.sample(self._batch_size)
        states = torch.tensor(np.array([t.state for t in batch]), dtype=torch.float32)
        actions = torch.tensor([t.action_idx for t in batch], dtype=torch.long)
        rewards = torch.tensor([t.reward for t in batch], dtype=torch.float32)
        next_states = torch.tensor(np.array([t.next_state for t in batch]), dtype=torch.float32)
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


# ---------------------------------------------------------------------------
# Novelty 1: Parameterized DQN — action selection + intensity control
# ---------------------------------------------------------------------------


class ParameterizedDQNModel:
    """DQN whose output covers n_actions × n_intensities (action, intensity) pairs.

    Combined index = action_idx * n_intensities + intensity_idx.
    The network learns which (action, intensity) combination maximises shaped reward,
    where anomaly_lambda penalises high ML anomaly scores. At low intensity the
    feature encoder produces values closer to the normal baseline → lower anomaly
    score → smaller penalty → higher net reward.
    """

    def __init__(
        self,
        n_actions: int = 15,
        n_intensities: int = 3,
        state_dim: int = 50,
        seed: int = 42,
        lr: float = 1e-3,
        gamma: float = 0.95,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.1,
        epsilon_decay_steps: int = 1000,
        buffer_capacity: int = 4000,
        batch_size: int = 32,
        target_update_freq: int = 10,
    ) -> None:
        seed_everything(seed)
        self._n_actions = n_actions
        self._n_intensities = n_intensities
        self._n_outputs = n_actions * n_intensities
        self._gamma = gamma
        self._batch_size = batch_size
        self._target_update_freq = target_update_freq
        self._epsilon = epsilon_start
        self._epsilon_end = epsilon_end
        self._epsilon_decay = (epsilon_start - epsilon_end) / epsilon_decay_steps
        self.online_net = QNetwork(state_dim, self._n_outputs)
        self.target_net = QNetwork(state_dim, self._n_outputs)
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.target_net.eval()
        self.buffer = ReplayBuffer(buffer_capacity)
        self.optimizer = torch.optim.Adam(self.online_net.parameters(), lr=lr)
        self._step_count = 0
        self._grad_step_count = 0

    def _combined_idx(self, action_idx: int, intensity: int) -> int:
        return action_idx * self._n_intensities + intensity

    def select_action_with_intensity(
        self, available_ids: list[str], state: np.ndarray
    ) -> tuple[str, int]:
        """Return (action_id, intensity) for the given available actions."""
        x = torch.tensor(state, dtype=torch.float32)
        with torch.no_grad():
            q = self.online_net(x)

        mask = torch.full((self._n_outputs,), float("-inf"))
        avail_idxs = [ALL_ACTION_IDS.index(a) for a in available_ids if a in ALL_ACTION_IDS]
        for action_idx in avail_idxs:
            for intensity in range(self._n_intensities):
                cidx = self._combined_idx(action_idx, intensity)
                mask[cidx] = q[cidx]

        self._step_count += 1
        self._epsilon = max(self._epsilon_end, self._epsilon - self._epsilon_decay)

        if random.random() < self._epsilon:
            action_id = random.choice(available_ids)
            intensity = random.randint(0, self._n_intensities - 1)
            return action_id, intensity

        best_cidx = int(torch.argmax(mask).item())
        best_action_idx = best_cidx // self._n_intensities
        best_intensity = best_cidx % self._n_intensities
        return ALL_ACTION_IDS[best_action_idx], best_intensity

    def update_parameterized(
        self,
        action_id: str,
        intensity: int,
        state: np.ndarray,
        reward: float,
        next_state: np.ndarray,
    ) -> None:
        action_idx = ALL_ACTION_IDS.index(action_id)
        cidx = self._combined_idx(action_idx, intensity)
        self.buffer.push(state.astype(np.float32), cidx, reward, next_state.astype(np.float32))
        if len(self.buffer) < self._batch_size:
            return
        batch = self.buffer.sample(self._batch_size)
        states = torch.tensor(np.array([t.state for t in batch]), dtype=torch.float32)
        actions = torch.tensor([t.action_idx for t in batch], dtype=torch.long)
        rewards = torch.tensor([t.reward for t in batch], dtype=torch.float32)
        next_states = torch.tensor(np.array([t.next_state for t in batch]), dtype=torch.float32)
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


class ParameterizedDQNAttacker(Attacker):
    """DQN attacker that selects both the action and its execution intensity.

    Intensity 0 = low (stealthy parameters, near normal baseline).
    Intensity 1 = medium (default parameters).
    Intensity 2 = high (aggressive parameters, clearly anomalous).

    With anomaly_lambda > 0 in shaped reward, the network learns to prefer low
    intensity because it yields smaller ML anomaly scores and thus higher net reward.
    The last chosen intensity is exposed via get_last_intensity() so run_experiment.py
    can pass the correct parameters to the ActionExecutor.
    """

    def __init__(self, model: ParameterizedDQNModel) -> None:
        self._model = model
        self._last_state: np.ndarray | None = None
        self._last_action_id: str | None = None
        self._last_intensity: int = 1

    def get_last_intensity(self) -> int:
        return self._last_intensity

    def choose_action(self, available: list[str], context: np.ndarray) -> str:
        self._last_state = context.copy()
        action_id, intensity = self._model.select_action_with_intensity(available, context)
        self._last_action_id = action_id
        self._last_intensity = intensity
        return action_id

    def observe(self, action_id: str, context: np.ndarray, reward: float) -> None:
        if self._last_state is None:
            raise RuntimeError("observe() called before choose_action()")
        self._model.update_parameterized(
            self._last_action_id, self._last_intensity, self._last_state, reward, context
        )
        self._last_state = context.copy()
        self._last_action_id = action_id
