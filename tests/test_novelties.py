"""Tests for Novelty 1 (ParameterizedDQNAttacker) and Novelty 2 (auto_remediate)."""

from __future__ import annotations

import numpy as np
import pytest

from aatf.action_intensity import INTENSITY_LEVELS, get_params_for_intensity
from aatf.action_library import REGISTRY
from aatf.dqn_attacker import ParameterizedDQNAttacker, ParameterizedDQNModel
from aatf.episode import StepRecord
from aatf.metrics import EpisodeRecord
from aatf.ml_defence import ActionFeatureEncoder, MLAnomalyDefence, auto_remediate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALL_IDS = sorted(a.action_id for a in REGISTRY.list_actions())
_N = len(_ALL_IDS)
_DIM = 50


def _make_model(seed: int = 0) -> ParameterizedDQNModel:
    return ParameterizedDQNModel(n_actions=_N, state_dim=_DIM, seed=seed)


def _make_attacker(seed: int = 0) -> ParameterizedDQNAttacker:
    return ParameterizedDQNAttacker(_make_model(seed))


def _ctx() -> np.ndarray:
    return np.zeros(_DIM, dtype=np.float32)


def _ep(steps: list[StepRecord]) -> EpisodeRecord:
    return EpisodeRecord(
        attacker_class="ParameterizedDQNAttacker",
        seed=42,
        total_reward=sum(s.reward for s in steps),
        steps=steps,
        completed=True,
        episode_index=0,
    )


def _step(action_id: str, detected: bool, anomaly_score: float) -> StepRecord:
    return StepRecord(
        action_id=action_id,
        detected=detected,
        stage_progress=False,
        reward=-1.0 if detected else -0.1,
        anomaly_score=anomaly_score,
    )


# ---------------------------------------------------------------------------
# Novelty 1: action_intensity
# ---------------------------------------------------------------------------


class TestActionIntensity:
    def test_intensity_levels_constant(self):
        assert INTENSITY_LEVELS == 3

    def test_low_intensity_has_fewer_attempts_than_high(self):
        low = get_params_for_intensity("ssh_brute_force", 0, {})
        high = get_params_for_intensity("ssh_brute_force", 2, {})
        assert low["attempts"] < high["attempts"]

    def test_low_wordlist_smaller_than_high(self):
        low = get_params_for_intensity("http_dir_scan", 0, {})
        high = get_params_for_intensity("http_dir_scan", 2, {})
        assert low["wordlist_size"] < high["wordlist_size"]

    def test_unknown_action_returns_defaults(self):
        defaults = {"foo": 1}
        result = get_params_for_intensity("unknown_action_xyz", 0, defaults)
        assert result == defaults

    def test_clamps_intensity_above_max(self):
        high = get_params_for_intensity("ssh_brute_force", 2, {})
        clamped = get_params_for_intensity("ssh_brute_force", 99, {})
        assert high == clamped

    def test_clamps_intensity_below_zero(self):
        low = get_params_for_intensity("ssh_brute_force", 0, {})
        clamped = get_params_for_intensity("ssh_brute_force", -5, {})
        assert low == clamped

    def test_low_intensity_ml_score_below_high(self):
        """Low-intensity ssh_brute_force should get a lower ML score than high-intensity."""
        from datetime import UTC, datetime

        from aatf.contracts import Action

        encoder = ActionFeatureEncoder()
        action_def = REGISTRY.get_action("ssh_brute_force")

        low_params = get_params_for_intensity("ssh_brute_force", 0, action_def.default_parameters)
        high_params = get_params_for_intensity("ssh_brute_force", 2, action_def.default_parameters)

        ts = datetime.now(UTC)
        feat_low = encoder.encode(
            Action(
                action_id="ssh_brute_force", category="brute", parameters=low_params, timestamp=ts
            )
        )
        feat_high = encoder.encode(
            Action(
                action_id="ssh_brute_force", category="brute", parameters=high_params, timestamp=ts
            )
        )
        # attempts dimension (feat[4]): low should be smaller than high
        assert feat_low[4] < feat_high[4]


# ---------------------------------------------------------------------------
# Novelty 1: ParameterizedDQNAttacker
# ---------------------------------------------------------------------------


class TestParameterizedDQNAttacker:
    def test_choose_action_returns_valid_id(self):
        attacker = _make_attacker()
        available = ["tcp_port_scan", "ssh_brute_force"]
        result = attacker.choose_action(available, _ctx())
        assert result in available

    def test_get_last_intensity_in_range(self):
        attacker = _make_attacker()
        attacker.choose_action(["tcp_port_scan"], _ctx())
        assert 0 <= attacker.get_last_intensity() < INTENSITY_LEVELS

    def test_observe_does_not_raise(self):
        attacker = _make_attacker()
        ctx = _ctx()
        attacker.choose_action(["tcp_port_scan"], ctx)
        attacker.observe("tcp_port_scan", _ctx(), 1.0)

    def test_observe_before_choose_raises(self):
        attacker = _make_attacker()
        with pytest.raises(RuntimeError):
            attacker.observe("tcp_port_scan", _ctx(), 1.0)

    def test_respects_available_actions(self):
        attacker = _make_attacker()
        available = ["dns_exfil", "http_exfil"]
        for _ in range(20):
            result = attacker.choose_action(available, _ctx())
            assert result in available

    def test_n_outputs_is_actions_times_intensities(self):
        model = _make_model()
        assert model._n_outputs == _N * INTENSITY_LEVELS

    def test_selects_all_intensities_during_exploration(self):
        """With epsilon=1 (start), should sample all 3 intensities across enough trials."""
        attacker = _make_attacker()
        seen_intensities = set()
        for _ in range(100):
            attacker.choose_action(["tcp_port_scan"], _ctx())
            seen_intensities.add(attacker.get_last_intensity())
        assert len(seen_intensities) == INTENSITY_LEVELS


# ---------------------------------------------------------------------------
# Novelty 2: auto_remediate
# ---------------------------------------------------------------------------


class TestAutoRemediate:
    def _defence(self) -> MLAnomalyDefence:
        return MLAnomalyDefence(threshold=0.6, seed=42, n_baseline=200)

    def test_no_evaded_steps_returns_empty_report(self):
        defence = self._defence()
        # All steps detected — no double blind spots
        records = [_ep([_step("tcp_port_scan", detected=True, anomaly_score=0.8)])]
        _, report = auto_remediate(defence, records)
        assert report.total_evaded == 0
        assert report.gaps_closed == 0

    def test_evaded_steps_below_threshold_are_found(self):
        defence = self._defence()
        # Step that evaded Suricata AND got low ML score
        records = [_ep([_step("ssh_brute_force", detected=False, anomaly_score=0.1)])]
        _, report = auto_remediate(defence, records, evasion_threshold=0.3)
        assert report.total_evaded >= 1
        assert "ssh_brute_force" in report.remediated_action_ids

    def test_score_improves_after_remediation(self):
        defence = self._defence()
        records = [_ep([_step("http_dir_scan", detected=False, anomaly_score=0.05)])]
        _, report = auto_remediate(defence, records, evasion_threshold=0.3)
        if report.total_evaded > 0:
            assert report.avg_score_after >= report.avg_score_before

    def test_evasive_cache_populated(self):
        defence = self._defence()
        assert len(defence._evasive_cache) == 0
        records = [_ep([_step("dns_exfil", detected=False, anomaly_score=0.05)])]
        new_defence, _ = auto_remediate(defence, records, evasion_threshold=0.3)
        assert len(new_defence._evasive_cache) > 0

    def test_original_defence_unchanged(self):
        """auto_remediate must not mutate the original defence."""
        defence = self._defence()
        records = [_ep([_step("tcp_port_scan", detected=False, anomaly_score=0.05)])]
        _, _ = auto_remediate(defence, records)
        assert len(defence._evasive_cache) == 0

    def test_steps_above_threshold_not_remediated(self):
        """Steps with anomaly_score >= evasion_threshold are NOT double blind spots."""
        defence = self._defence()
        # anomaly_score = 0.5 >= threshold 0.3 → already flagged by ML → not a gap
        records = [_ep([_step("tcp_port_scan", detected=False, anomaly_score=0.5)])]
        _, report = auto_remediate(defence, records, evasion_threshold=0.3)
        assert report.total_evaded == 0

    def test_remediation_report_improvement_property(self):
        defence = self._defence()
        records = [_ep([_step("ftp_brute_force", detected=False, anomaly_score=0.05)])]
        _, report = auto_remediate(defence, records, evasion_threshold=0.3)
        if report.total_evaded > 0:
            assert report.improvement == pytest.approx(
                report.avg_score_after - report.avg_score_before
            )
