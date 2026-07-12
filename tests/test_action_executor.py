"""Tests for ActionExecutor (F08) — covers C-001 through C-015."""

from __future__ import annotations

import dataclasses
import socket
import subprocess
from datetime import UTC, datetime

import pytest

from aatf.action_executor import (
    ActionExecutor,
    ExecutionResult,
    ExternalTargetError,
)
from aatf.action_library import REGISTRY
from aatf.contracts import Action

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_action(
    action_id: str,
    category: str = "scan",
    target_ip: str = "172.28.0.2",
    extra: dict | None = None,
) -> Action:
    params: dict = {"target_ip": target_ip}
    if extra:
        params.update(extra)
    return Action(
        action_id=action_id,
        category=category,
        parameters=params,
        timestamp=datetime.now(UTC),
    )


def _recording_executor(seed: int = 42) -> tuple[ActionExecutor, list]:
    calls: list[tuple] = []
    ex = ActionExecutor(
        seed=seed,
        send_fn=lambda h, p, d: calls.append((h, p, d)),
        sleep_fn=lambda _: None,
    )
    return ex, calls


# ---------------------------------------------------------------------------
# US2 — Internal-Target Guard (C-003, C-004, C-005, C-014)
# ---------------------------------------------------------------------------


def test_external_ip_raises():
    """C-003: ExternalTargetError raised for external IP."""
    executor, _ = _recording_executor()
    action = _make_action(
        "tcp_port_scan",
        target_ip="8.8.8.8",
        extra={"port_range": "80-80", "rate_pps": 1, "timing_ms": 0},
    )
    with pytest.raises(ExternalTargetError):
        executor.execute(action)


def test_no_traffic_before_external_error():
    """C-004: No traffic emitted before ExternalTargetError."""
    executor, calls = _recording_executor()
    action = _make_action(
        "tcp_port_scan",
        target_ip="8.8.8.8",
        extra={"port_range": "80-80", "rate_pps": 1, "timing_ms": 0},
    )
    with pytest.raises(ExternalTargetError):
        executor.execute(action)
    assert len(calls) == 0


def test_private_non_lab_ip_raises():
    """C-005: Private non-lab IP also raises ExternalTargetError."""
    executor, _ = _recording_executor()
    action = _make_action(
        "tcp_port_scan",
        target_ip="192.168.1.1",
        extra={"port_range": "80-80", "rate_pps": 1, "timing_ms": 0},
    )
    with pytest.raises(ExternalTargetError):
        executor.execute(action)


def test_external_target_error_is_value_error():
    """C-014: ExternalTargetError is a subclass of ValueError."""
    assert issubclass(ExternalTargetError, ValueError)


# ---------------------------------------------------------------------------
# US1 — Traffic Emission (C-001, C-002, C-007, C-008, C-009, C-010, C-011, C-012, C-013)
# ---------------------------------------------------------------------------


def test_execute_returns_execution_result_for_all_actions():
    """C-001: execute() returns ExecutionResult for every registered action."""
    executor, _ = _recording_executor()
    for defn in REGISTRY.list_actions():
        action = defn.to_action(datetime.now(UTC))
        result = executor.execute(action)
        assert isinstance(result, ExecutionResult), (
            f"{defn.action_id} did not return ExecutionResult"
        )


def test_success_and_emitted_count_for_lab_action():
    """C-002: success=True and emitted_count>=1 for valid lab-internal action."""
    executor, calls = _recording_executor()
    action = _make_action(
        "tcp_port_scan",
        category="scan",
        extra={"port_range": "80-80", "rate_pps": 1, "timing_ms": 0},
    )
    result = executor.execute(action)
    assert result.success is True
    assert result.emitted_count >= 1
    assert len(calls) >= 1


def test_execution_result_fields_match_action():
    """C-007: ExecutionResult.action_id and category mirror Action."""
    executor, _ = _recording_executor()
    action = _make_action("ssh_version_probe", category="ssh", extra={"target_port": 22})
    result = executor.execute(action)
    assert result.action_id == action.action_id
    assert result.category == action.category


def test_error_is_none_on_success():
    """C-008: error is None on success."""
    executor, _ = _recording_executor()
    action = _make_action("ssh_version_probe", category="ssh", extra={"target_port": 22})
    result = executor.execute(action)
    assert result.success is True
    assert result.error is None


def test_unknown_action_id_returns_failure():
    """C-009: Unknown action_id returns failure result (does not raise)."""
    executor, _ = _recording_executor()
    action = Action(
        action_id="unknown_action_xyz",
        category="scan",
        parameters={"target_ip": "172.28.0.2"},
        timestamp=datetime.now(UTC),
    )
    result = executor.execute(action)
    assert result.success is False
    assert result.emitted_count == 0
    assert result.error is not None


def test_rate_zero_promoted_to_one():
    """C-010: rate=0 promoted to at least 1 probe."""
    executor, calls = _recording_executor()
    action = _make_action(
        "ssh_brute_force",
        category="brute",
        extra={"target_port": 22, "attempts": 0, "timing_ms": 0},
    )
    result = executor.execute(action)
    assert result.emitted_count >= 1


def test_all_15_action_ids_have_handlers():
    """C-011: All 15 action_ids have handlers — none returns 'no handler' error."""
    executor, _ = _recording_executor()
    for defn in REGISTRY.list_actions():
        action = defn.to_action(datetime.now(UTC))
        result = executor.execute(action)
        no_handler = (
            result.success is False
            and result.error is not None
            and "no handler" in result.error.lower()
        )
        assert not no_handler, f"{defn.action_id} has no handler: {result.error}"


def test_no_real_socket_in_unit_tests(monkeypatch):
    """C-012: No real socket opened when recording send_fn is injected."""
    opened: list[str] = []

    original_socket = socket.socket

    def sentinel_socket(*args, **kwargs):
        opened.append(f"socket({args}, {kwargs})")
        return original_socket(*args, **kwargs)

    monkeypatch.setattr(socket, "socket", sentinel_socket)

    executor, calls = _recording_executor()
    action = _make_action("tcp_port_scan", extra={"port_range": "80-80", "timing_ms": 0})
    result = executor.execute(action)
    assert result.success is True
    assert len(calls) >= 1
    assert len(opened) == 0, f"Real socket was opened: {opened}"


def test_execution_result_is_dataclass_with_five_fields():
    """C-013: ExecutionResult is a dataclass with the 5 required fields."""
    field_names = {f.name for f in dataclasses.fields(ExecutionResult)}
    assert field_names == {"action_id", "category", "success", "emitted_count", "error"}


# ---------------------------------------------------------------------------
# US3 — Deterministic Execution Under Seed (C-006)
# ---------------------------------------------------------------------------


def test_same_seed_produces_identical_emitted_count():
    """C-006: Same seed → identical emitted_count for the same Action."""
    calls_a: list[tuple] = []
    calls_b: list[tuple] = []
    executor_a = ActionExecutor(
        seed=42,
        send_fn=lambda h, p, d: calls_a.append((h, p, d)),
        sleep_fn=lambda _: None,
    )
    executor_b = ActionExecutor(
        seed=42,
        send_fn=lambda h, p, d: calls_b.append((h, p, d)),
        sleep_fn=lambda _: None,
    )
    action = _make_action(
        "ssh_brute_force",
        category="brute",
        extra={"target_port": 22, "attempts": 5, "timing_ms": 100},
    )
    result_a = executor_a.execute(action)
    result_b = executor_b.execute(action)
    assert result_a.emitted_count == result_b.emitted_count
    assert len(calls_a) == len(calls_b)


# ---------------------------------------------------------------------------
# Integration — C-015 (auto-skip when lab not running)
# ---------------------------------------------------------------------------


_LAB_RUNNING = (
    subprocess.run(
        ["docker", "inspect", "aatf-attacker"],
        capture_output=True,
    ).returncode
    == 0
)


@pytest.mark.skipif(not _LAB_RUNNING, reason="lab not running — run 'make lab-up' first")
def test_scan_triggers_suricata_alert():
    """C-015: Integration — scan action triggers Suricata alert in eve.json."""
    import json
    import time
    from pathlib import Path

    executor = ActionExecutor(seed=0)
    action = _make_action("tcp_port_scan", extra={"port_range": "1-100", "timing_ms": 0})
    result = executor.execute(action)
    assert result.emitted_count >= 1

    time.sleep(2)

    eve_path = Path(__file__).parent.parent / "logs" / "suricata" / "eve.json"
    if not eve_path.exists():
        pytest.skip("eve.json not found at expected bind-mount path")
    alerts = [
        json.loads(line)
        for line in eve_path.read_text().splitlines()
        if line.strip()
        if json.loads(line).get("event_type") == "alert"
    ]
    assert len(alerts) >= 1
