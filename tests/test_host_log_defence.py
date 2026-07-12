from __future__ import annotations

import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aatf.contracts import Action
from aatf.defence import DefenceError
from aatf.host_log_defence import HostLogDefence
from tests.test_defence import check_defence_contract

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_FIXTURES = Path(__file__).parent / "fixtures" / "auth_log_samples"


@pytest.fixture
def action() -> Action:
    return Action(
        action_id="act-001",
        category="scan",
        parameters={"port": 22},
        timestamp=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Phase 3 — US1: Keyword pattern matching (C-001 to C-007, C-011, C-012)
# ---------------------------------------------------------------------------


def test_conformance_check_passes(action: Action) -> None:  # C-001
    defence = HostLogDefence(_FIXTURES / "empty.log", ["sshd"])
    check_defence_contract(defence, action)


def test_matching_line_produces_alerted_true(action: Action) -> None:  # C-002
    defence = HostLogDefence(_FIXTURES / "one_match.log", ["sshd"])
    result = defence.observe(action)
    assert result.alerted is True
    assert "sshd" in result.rule_ids
    assert result.coverage == "covered"
    assert result.anomaly_score == 0.0


def test_non_matching_lines_ignored(action: Action) -> None:  # C-003
    defence = HostLogDefence(_FIXTURES / "no_match.log", ["sshd"])
    result = defence.observe(action)
    assert result.alerted is False
    assert result.rule_ids == []
    assert result.coverage == "uncovered"


def test_empty_file_returns_uncovered(action: Action) -> None:  # C-004
    defence = HostLogDefence(_FIXTURES / "empty.log", ["sshd"])
    result = defence.observe(action)
    assert result.alerted is False
    assert result.rule_ids == []
    assert result.coverage == "uncovered"


def test_unreadable_path_raises_defence_error(action: Action) -> None:  # C-005
    defence = HostLogDefence("/nonexistent/auth.log", ["sshd"])
    with pytest.raises(DefenceError):
        defence.observe(action)


def test_multiple_patterns_match_one_line(action: Action) -> None:  # C-006
    defence = HostLogDefence(_FIXTURES / "two_patterns.log", ["sshd", "Failed password"])
    result = defence.observe(action)
    assert result.alerted is True
    assert "sshd" in result.rule_ids
    assert "Failed password" in result.rule_ids


def test_multiple_lines_accumulate_all_matches(action: Action) -> None:  # C-007
    defence = HostLogDefence(_FIXTURES / "multi_line.log", ["sshd", "Failed password"])
    result = defence.observe(action)
    assert result.alerted is True
    assert "sshd" in result.rule_ids
    assert "Failed password" in result.rule_ids


def test_anomaly_score_always_zero(action: Action) -> None:  # C-011
    matching = HostLogDefence(_FIXTURES / "one_match.log", ["sshd"]).observe(action)
    silent = HostLogDefence(_FIXTURES / "empty.log", ["sshd"]).observe(action)
    assert matching.anomaly_score == 0.0
    assert silent.anomaly_score == 0.0


def test_empty_pattern_list_never_alerts(action: Action) -> None:  # C-012
    defence = HostLogDefence(_FIXTURES / "one_match.log", [])
    result = defence.observe(action)
    assert result.alerted is False
    assert result.coverage == "uncovered"
    assert result.rule_ids == []


# ---------------------------------------------------------------------------
# Phase 4 — US2: Coverage states
# ---------------------------------------------------------------------------


def test_coverage_covered_when_match(action: Action) -> None:  # US2-covered
    result = HostLogDefence(_FIXTURES / "one_match.log", ["sshd"]).observe(action)
    assert result.coverage == "covered"


def test_coverage_uncovered_when_no_match(action: Action) -> None:  # US2-uncovered
    result = HostLogDefence(_FIXTURES / "empty.log", ["sshd"]).observe(action)
    assert result.coverage == "uncovered"


def test_coverage_unknown_raises_defence_error(action: Action) -> None:  # US2-unknown
    defence = HostLogDefence("/no/such/auth.log", ["sshd"])
    with pytest.raises(DefenceError) as exc_info:
        defence.observe(action)
    msg = str(exc_info.value).lower()
    assert "unreadable" in msg or "no/such" in msg or "auth.log" in msg


# ---------------------------------------------------------------------------
# Phase 5 — US3: Tail-read / cursor (C-008, C-009, C-010)
# ---------------------------------------------------------------------------


def test_second_call_no_new_lines_returns_not_alerted(
    action: Action, tmp_path: Path
) -> None:  # C-008
    log = tmp_path / "auth.log"
    log.write_text("Jul  6 10:00:00 host sshd[1]: Connection from 172.28.0.3\n")
    defence = HostLogDefence(log, ["sshd"])
    r1 = defence.observe(action)
    assert r1.alerted is True
    r2 = defence.observe(action)
    assert r2.alerted is False
    assert r2.rule_ids == []
    assert r2.coverage == "uncovered"


def test_new_line_between_calls_picked_up(action: Action, tmp_path: Path) -> None:  # C-009
    log = tmp_path / "auth.log"
    log.write_text("")
    defence = HostLogDefence(log, ["sshd"])
    r1 = defence.observe(action)
    assert r1.alerted is False
    with log.open("a") as fh:
        fh.write("Jul  6 10:00:01 host sshd[2]: Connection established\n")
    r2 = defence.observe(action)
    assert r2.alerted is True
    assert "sshd" in r2.rule_ids


def test_file_truncation_resets_cursor(action: Action, tmp_path: Path) -> None:  # C-010
    log = tmp_path / "auth.log"
    # Write 3 copies so cursor ends up well past 50 bytes
    line = "Jul  6 10:00:00 host sshd[1]: Connection from 172.28.0.3\n"
    log.write_text(line * 3)
    defence = HostLogDefence(log, ["sshd"])
    r1 = defence.observe(action)
    assert r1.alerted is True
    # Overwrite with shorter content — simulates log rotation
    log.write_text("Jul  6 10:00:10 host sshd[9]: Failed password for root\n")
    r2 = defence.observe(action)
    assert "sshd" in r2.rule_ids
    assert r2.alerted is True


# ---------------------------------------------------------------------------
# Phase 6 — Integration test (C-013): live lab SSH probe (auto-skip)
# ---------------------------------------------------------------------------


def _lab_running() -> bool:
    r = subprocess.run(
        ["docker", "inspect", "aatf-defender"],
        capture_output=True,
    )
    return r.returncode == 0


def test_live_lab_ssh_probe(action: Action, tmp_path: Path) -> None:  # C-013
    if not _lab_running():
        pytest.skip("lab not running — run 'make lab-up' first")
    # Trigger a Failed-password / connection line on the defender's sshd
    subprocess.run(
        [
            "docker",
            "exec",
            "aatf-attacker",
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=3",
            "root@aatf-defender",
        ],
        capture_output=True,
    )
    time.sleep(2)
    # Read auth log from defender container
    r = subprocess.run(
        ["docker", "exec", "aatf-defender", "cat", "/var/log/auth.log"],
        capture_output=True,
        text=True,
    )
    log_file = tmp_path / "auth.log"
    log_file.write_text(r.stdout)
    if not r.stdout.strip():
        pytest.skip("defender has no sshd — auth.log is empty (minimal lab image)")
    defence = HostLogDefence(log_file, ["Failed password", "sshd"])
    result = defence.observe(action)
    assert result.alerted is True
    assert result.coverage == "covered"
    # Either pattern may appear depending on sshd response
    assert "Failed password" in result.rule_ids or "sshd" in result.rule_ids
