"""Tests for episode loop (F16) — C-001 to C-012."""

from __future__ import annotations

from aatf.action_library import REGISTRY
from aatf.context_vector import EpisodeState
from aatf.contracts import Action, DetectionResult
from aatf.defence import Defence
from aatf.episode import run_episode

_ALL_IDS: frozenset[str] = frozenset(a.action_id for a in REGISTRY.list_actions())
_SELECTOR = lambda available, state: available[0]  # noqa: E731
_EXECUTE = lambda action_id: None  # noqa: E731


class StubDefence(Defence):
    def __init__(self, alert: bool = False) -> None:
        self._alert = alert

    def observe(self, action: Action) -> DetectionResult:
        return DetectionResult(
            alerted=self._alert, rule_ids=[], anomaly_score=0.0, coverage="unknown"
        )


# ---------------------------------------------------------------------------
# US1 — Single Step Execution
# ---------------------------------------------------------------------------


def test_c001_step_record_action_id() -> None:
    state = EpisodeState()
    result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=1)
    assert len(result.steps) == 1
    entry_points = {"dns_subdomain_enum", "icmp_ping_sweep", "tcp_port_scan", "udp_sweep"}
    assert result.steps[0].action_id in entry_points


def test_c002_no_alert_terminal_reward() -> None:
    # ssh_version_probe: terminal node (no outgoing edges), reachable via icmp_ping_sweep
    state = EpisodeState(completed_actions=set(_ALL_IDS - {"ssh_version_probe"}))
    result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=1)
    step = result.steps[0]
    assert step.action_id == "ssh_version_probe"
    assert step.detected is False
    assert step.stage_progress is False
    assert step.reward == -0.1


def test_c003_alert_detected_reward() -> None:
    state = EpisodeState(completed_actions=set(_ALL_IDS - {"ssh_version_probe"}))
    result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=True), max_steps=1)
    step = result.steps[0]
    assert step.detected is True
    assert step.reward == -1.0


def test_c004_stage_progress_true_entry_point() -> None:
    state = EpisodeState()
    selector = lambda available, s: "tcp_port_scan"  # noqa: E731
    result = run_episode(state, selector, _EXECUTE, StubDefence(alert=False), max_steps=1)
    assert result.steps[0].stage_progress is True
    assert result.steps[0].reward == 1.0


def test_c005_episode_state_mutated() -> None:
    state = EpisodeState()
    assert state.step == 0
    run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=1)
    assert state.step == 1
    assert len(state.alert_history) == 1
    assert len(state.completed_actions) == 1


# ---------------------------------------------------------------------------
# US2 — Episode Termination: Actions Exhausted
# ---------------------------------------------------------------------------


def test_c006_completed_true_terminal_exhausted() -> None:
    state = EpisodeState(completed_actions=set(_ALL_IDS - {"ssh_version_probe"}))
    result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False))
    assert result.completed is True
    assert len(result.steps) == 1


def test_c007_completed_true_zero_steps_preloaded() -> None:
    state = EpisodeState(completed_actions=set(_ALL_IDS))
    result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False))
    assert result.completed is True
    assert result.steps == []
    assert result.total_reward == 0.0


# ---------------------------------------------------------------------------
# US3 — Episode Termination: Step Limit Reached
# ---------------------------------------------------------------------------


def test_c008_completed_false_step_limit() -> None:
    state = EpisodeState()
    result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=3)
    assert result.completed is False
    assert len(result.steps) == 3


def test_c009_fr003_no_actions_wins_over_step_limit() -> None:
    # Both conditions true: available=[] AND step(5) >= max_steps(5)
    state = EpisodeState(completed_actions=set(_ALL_IDS), step=5)
    result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=5)
    assert result.completed is True  # no-actions wins → True, not False
    assert result.steps == []


def test_c010_max_steps_zero() -> None:
    state = EpisodeState()
    result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=0)
    assert result.completed is False
    assert result.steps == []
    assert result.total_reward == 0.0


# ---------------------------------------------------------------------------
# US4 — Cumulative Episode Result
# ---------------------------------------------------------------------------


def test_c011_total_reward_arithmetic_sum() -> None:
    state = EpisodeState()
    steps_order = ["tcp_port_scan", "dns_subdomain_enum", "icmp_ping_sweep"]
    idx = 0

    def seq_selector(available: list[str], s: EpisodeState) -> str:
        nonlocal idx
        choice = steps_order[idx]
        idx += 1
        return choice

    call_count = 0

    class FirstAlertDefence(Defence):
        def observe(self, action: Action) -> DetectionResult:
            nonlocal call_count
            call_count += 1
            alerted = call_count == 1
            return DetectionResult(
                alerted=alerted, rule_ids=[], anomaly_score=0.0, coverage="unknown"
            )

    result = run_episode(state, seq_selector, _EXECUTE, FirstAlertDefence(), max_steps=3)
    assert len(result.steps) == 3
    # step1: detected=True → -1.0; step2,3: no alert + progress (entry points) → +1.0 each
    assert abs(result.total_reward - (-1.0 + 1.0 + 1.0)) < 1e-9


def test_c012_state_step_equals_steps_length() -> None:
    state = EpisodeState()
    result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=4)
    assert state.step == len(result.steps)


# ---------------------------------------------------------------------------
# C-013: parameterize_fn is called and overrides default params
# ---------------------------------------------------------------------------


def test_c013_parameterize_fn_overrides_params() -> None:
    """C-013: parameterize_fn return value reaches defence.observe() instead of defaults."""
    from aatf.contracts import DetectionResult
    from aatf.defence import Defence

    observed_params: list[dict] = []

    class RecordingDefence(Defence):
        def observe(self, action: Action) -> DetectionResult:
            observed_params.append(dict(action.parameters))
            return DetectionResult(
                alerted=False, rule_ids=[], anomaly_score=0.0, coverage="unknown"
            )

    sentinel = {"custom_key": "sentinel_value"}

    def parameterize_fn(action_id: str) -> dict:
        return sentinel

    state = EpisodeState()
    run_episode(
        state, _SELECTOR, _EXECUTE, RecordingDefence(), max_steps=1, parameterize_fn=parameterize_fn
    )

    assert len(observed_params) == 1
    assert observed_params[0] == sentinel
