"""AutoencoderDefence — PyTorch reconstruction-error anomaly detector.

Drop-in replacement for MLAnomalyDefence. Uses the same 7-dim feature
space and ActionFeatureEncoder so results are directly comparable.
"""

from __future__ import annotations

import math

import numpy as np
import torch
import torch.nn as nn

from aatf.contracts import Action, DetectionResult
from aatf.defence import Defence
from aatf.ml_defence import ActionFeatureEncoder, collect_normal_baseline
from aatf.seeding import seed_everything

FEATURE_DIM: int = 7
_EPOCHS: int = 500
_LR: float = 1e-3
_HIDDEN: int = 4
_LATENT: int = 2


class _AEModel(nn.Module):
    def __init__(
        self, input_dim: int = FEATURE_DIM, hidden: int = _HIDDEN, latent: int = _LATENT
    ) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, latent),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent, hidden),
            nn.ReLU(),
            nn.Linear(hidden, input_dim),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))


class AutoencoderDetector:
    """Train on normal-traffic vectors; score = normalised reconstruction MSE."""

    def __init__(self, seed: int = 42) -> None:
        seed_everything(seed)
        self._model = _AEModel()
        self._fitted = False
        self._scale: float = 1.0  # 95th-percentile MSE on training data

    def fit(self, X: np.ndarray) -> None:
        X_t = torch.tensor(X, dtype=torch.float32)
        opt = torch.optim.Adam(self._model.parameters(), lr=_LR)
        self._model.train()
        for _ in range(_EPOCHS):
            opt.zero_grad()
            loss = nn.functional.mse_loss(self._model(X_t), X_t)
            loss.backward()
            opt.step()
        # Calibrate: mean and std of training reconstruction errors for z-score scoring
        self._model.eval()
        with torch.no_grad():
            recon = self._model(X_t)
            mse_per_sample = ((recon - X_t) ** 2).mean(dim=1).numpy()
        self._mse_mean = float(np.mean(mse_per_sample))
        self._mse_std = float(np.std(mse_per_sample)) + 1e-9
        self._fitted = True

    def score(self, x: np.ndarray) -> float:
        if not self._fitted:
            raise RuntimeError("AutoencoderDetector not fitted — call fit() first")
        self._model.eval()
        x_t = torch.tensor(x, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            recon = self._model(x_t)
            mse = float(nn.functional.mse_loss(recon, x_t).item())
        # z-score: how many stds above the normal reconstruction error?
        z = (mse - self._mse_mean) / self._mse_std
        return float(1.0 / (1.0 + math.exp(-z)))


class AEAnomalyDefence(Defence):
    """Autoencoder-based anomaly defence — same interface as MLAnomalyDefence."""

    def __init__(
        self,
        threshold: float = 0.6,
        seed: int = 42,
        n_baseline: int = 500,
    ) -> None:
        self._encoder = ActionFeatureEncoder()
        self._threshold = threshold
        self._seed = seed
        self._detector = AutoencoderDetector(seed=seed)
        X_normal = collect_normal_baseline(n_baseline, seed)
        self._detector.fit(X_normal)
        self._evasive_cache: list[np.ndarray] = []

    def observe(self, action: Action) -> DetectionResult:
        x = self._encoder.encode(action)
        base_score = self._detector.score(x)
        boost = self._similarity_boost(x)
        score = min(1.0, base_score + boost)
        return DetectionResult(
            alerted=score >= self._threshold,
            rule_ids=[],
            anomaly_score=score,
            coverage="covered",
        )

    def _similarity_boost(self, feat: np.ndarray) -> float:
        if not self._evasive_cache:
            return 0.0
        nf = np.linalg.norm(feat)
        if nf == 0:
            return 0.0
        max_sim = max(
            float(np.dot(feat, ev) / (nf * (np.linalg.norm(ev) + 1e-9)))
            for ev in self._evasive_cache
        )
        return max(0.0, (max_sim - 0.9) * 5.0) * (1.0 - self._detector.score(feat))
