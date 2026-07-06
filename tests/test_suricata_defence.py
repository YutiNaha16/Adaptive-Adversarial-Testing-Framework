from __future__ import annotations

import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aatf.contracts import Action
from aatf.defence import DefenceError
from aatf.suricata_defence import SuricataDefence
from tests.test_defence import check_defence_contract

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_FIXTURES = Path(__file__).parent / "fixtures" / "eve_samples"


@pytest.fixture
def action() -> Action:
    return Action(
        action_id="act-001",
        category="scan",
        parameters={"port": 22},
        timestamp=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Phase 3 — US1: Alert parsing (C-001 to C-007, C-011)
# ---------------------------------------------------------------------------


def test_conformance_check_passes(action: Action) -> None:  # C-001
    defence = SuricataDefence(_FIXTURES / "empty.json")
    check_defence_contract(defence, action)


def test_alert_line_produces_alerted_true(action: Action) -> None:  # C-002
    defence = SuricataDefence(_FIXTURES / "one_alert.json")
    result = defence.observe(action)
    assert result.alerted is True
    assert "2001219" in result.rule_ids
    assert result.coverage == "covered"
    assert result.anomaly_score == 0.0


def test_non_alert_lines_ignored(action: Action) -> None:  # C-003
    defence = SuricataDefence(_FIXTURES / "stats_only.json")
    result = defence.observe(action)
    assert result.alerted is False
    assert result.rule_ids == []
    assert result.coverage == "uncovered"


def test_empty_file_returns_uncovered(action: Action) -> None:  # C-004
    defence = SuricataDefence(_FIXTURES / "empty.json")
    result = defence.observe(action)
    assert result.alerted is False
    assert result.rule_ids == []
    assert result.coverage == "uncovered"


def test_unreadable_path_raises_defence_error(action: Action) -> None:  # C-005
    defence = SuricataDefence("/nonexistent/eve.json")
    with pytest.raises(DefenceError):
        defence.observe(action)


def test_multiple_alerts_all_sids_returned(action: Action) -> None:  # C-006
    defence = SuricataDefence(_FIXTURES / "two_alerts.json")
    result = defence.observe(action)
    assert result.alerted is True
    assert "2001219" in result.rule_ids
    assert "2034660" in result.rule_ids


def test_malformed_line_skipped(action: Action) -> None:  # C-007
    defence = SuricataDefence(_FIXTURES / "malformed.json")
    result = defence.observe(action)
    assert result.alerted is True
    assert result.rule_ids == ["9999"]


def test_anomaly_score_always_zero(action: Action) -> None:  # C-011
    alerted_result = SuricataDefence(_FIXTURES / "one_alert.json").observe(action)
    silent_result = SuricataDefence(_FIXTURES / "empty.json").observe(action)
    assert alerted_result.anomaly_score == 0.0
    assert silent_result.anomaly_score == 0.0


# ---------------------------------------------------------------------------
# Phase 4 — US2: Coverage states (US2-covered, US2-uncovered, US2-unknown)
# ---------------------------------------------------------------------------


def test_coverage_covered_when_alert(action: Action) -> None:  # US2-covered
    result = SuricataDefence(_FIXTURES / "one_alert.json").observe(action)
    assert result.coverage == "covered"


def test_coverage_uncovered_when_no_alert(action: Action) -> None:  # US2-uncovered
    result = SuricataDefence(_FIXTURES / "empty.json").observe(action)
    assert result.coverage == "uncovered"


def test_coverage_unknown_raises_defence_error(action: Action) -> None:  # US2-unknown
    defence = SuricataDefence("/no/such/file.json")
    with pytest.raises(DefenceError) as exc_info:
        defence.observe(action)
    msg = str(exc_info.value).lower()
    assert "unreadable" in msg or "eve.json" in msg or "no/such" in msg


# ---------------------------------------------------------------------------
# Phase 5 — US3: Tail-read / cursor (C-008, C-009, C-010)
# ---------------------------------------------------------------------------


def test_second_call_no_new_lines_returns_not_alerted(
    action: Action, tmp_path: Path
) -> None:  # C-008
    eve = tmp_path / "eve.json"
    eve.write_text(
        '{"event_type":"alert","alert":{"signature_id":2001219}}\n'
    )
    defence = SuricataDefence(eve)
    r1 = defence.observe(action)
    assert r1.alerted is True
    r2 = defence.observe(action)
    assert r2.alerted is False
    assert r2.rule_ids == []
    assert r2.coverage == "uncovered"


def test_new_line_between_calls_picked_up(
    action: Action, tmp_path: Path
) -> None:  # C-009
    eve = tmp_path / "eve.json"
    eve.write_text("")
    defence = SuricataDefence(eve)
    r1 = defence.observe(action)
    assert r1.alerted is False
    with eve.open("a") as fh:
        fh.write('{"event_type":"alert","alert":{"signature_id":7777}}\n')
    r2 = defence.observe(action)
    assert r2.alerted is True
    assert "7777" in r2.rule_ids


def test_file_truncation_resets_cursor(
    action: Action, tmp_path: Path
) -> None:  # C-010
    eve = tmp_path / "eve.json"
    # Write 3 copies of the alert line so the cursor ends up well past 52 bytes
    alert_line = '{"event_type":"alert","alert":{"signature_id":1111}}\n'
    eve.write_text(alert_line * 3)
    defence = SuricataDefence(eve)
    r1 = defence.observe(action)
    assert r1.alerted is True
    assert "1111" in r1.rule_ids
    # Overwrite with a single shorter line — simulates log rotation.
    # cursor (~156) > new file size (~52), so the adapter must reset to 0.
    eve.write_text('{"event_type":"alert","alert":{"signature_id":2222}}\n')
    r2 = defence.observe(action)
    assert "2222" in r2.rule_ids
    assert "1111" not in r2.rule_ids


# ---------------------------------------------------------------------------
# Phase 6 — Integration test (C-012): live lab probe (auto-skip)
# ---------------------------------------------------------------------------


def _lab_running() -> bool:
    r = subprocess.run(
        ["docker", "inspect", "aatf-suricata"],
        capture_output=True,
    )
    return r.returncode == 0


def test_live_lab_probe(action: Action) -> None:  # C-012
    if not _lab_running():
        pytest.skip("lab not running — run 'make lab-up' first")
    subprocess.run(
        [
            "docker",
            "exec",
            "aatf-attacker",
            "nmap",
            "-sS",
            "-p",
            "22",
            "--min-rate",
            "1000",
            "aatf-defender",
        ],
        check=True,
    )
    time.sleep(2)
    eve_host_path = "/var/lib/docker/volumes/aatf-eve/_data/eve.json"
    defence = SuricataDefence(eve_host_path)
    result = defence.observe(action)
    assert result.alerted is True
    assert "2001219" in result.rule_ids
    assert result.coverage == "covered"
