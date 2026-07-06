from __future__ import annotations

import ast
import pathlib
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from aatf.contracts import Action, DetectionResult
from aatf.defence import Defence, DefenceError, NullDefence

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def action() -> Action:
    return Action(
        action_id="t-001",
        category="scan",
        parameters={"port": 22},
        timestamp=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Conformance helper — reusable by F11, F12, and future adapter tests
# ---------------------------------------------------------------------------


def check_defence_contract(defence: Defence, action: Action) -> None:
    result = defence.observe(action)
    assert isinstance(result, DetectionResult)
    assert isinstance(result.alerted, bool)
    assert isinstance(result.rule_ids, list)
    assert 0.0 <= result.anomaly_score <= 1.0
    assert result.coverage in ("covered", "uncovered", "unknown")
    if not result.alerted:
        assert result.rule_ids == []


# ---------------------------------------------------------------------------
# US1 — Define and invoke Defence uniformly
# ---------------------------------------------------------------------------


def test_null_defence_returns_detection_result(action):
    """C-001: observe() returns a valid DetectionResult."""
    result = NullDefence().observe(action)
    assert isinstance(result, DetectionResult)


def test_null_defence_not_detected(action):
    """C-002: NullDefence always returns not-detected."""
    result = NullDefence().observe(action)
    assert result.alerted is False
    assert result.rule_ids == []
    assert result.anomaly_score == 0.0
    assert result.coverage == "unknown"


def test_failing_defence_raises_defence_error(action):
    """C-003: DefenceError raised on internal failure."""

    class FailingDefence(Defence):
        def observe(self, action: Action) -> DetectionResult:
            raise DefenceError("connection lost", cause=OSError("file not found"))

    with pytest.raises(DefenceError):
        FailingDefence().observe(action)


def test_detection_result_is_immutable(action):
    """C-006: DetectionResult returned by Defence is frozen."""
    result = NullDefence().observe(action)
    with pytest.raises((ValidationError, TypeError)):
        result.alerted = True  # type: ignore[misc]


def test_defence_cannot_be_instantiated():
    """C-007: Defence ABC cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Defence()  # type: ignore[abstract]


def test_unimplemented_observe_raises_type_error():
    """C-008: Subclass without observe() raises TypeError at instantiation."""

    class EmptyDefence(Defence):
        pass

    with pytest.raises(TypeError):
        EmptyDefence()


# ---------------------------------------------------------------------------
# US2 — Swap detectors without touching consumers
# ---------------------------------------------------------------------------


def test_defence_module_has_no_concrete_imports():
    """C-005: defence.py must not import any concrete detector."""
    source = pathlib.Path("src/aatf/defence.py").read_text()
    tree = ast.parse(source)
    imported_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_names.append(node.module)
    forbidden = ["suricata", "eve", "auditd", "sklearn", "torch", "tensorflow"]
    for name in imported_names:
        for f in forbidden:
            assert f not in name.lower(), f"Forbidden import '{name}' found in defence.py"


def test_null_defence_repeated_calls_equal(action):
    """C-009: NullDefence is safe for repeated calls."""
    defence = NullDefence()
    results = [defence.observe(action) for _ in range(3)]
    assert results[0] == results[1] == results[2]


def test_null_defence_accepts_any_action_category():
    """C-010: observe() accepts any valid Action category."""
    ts = datetime.now(UTC)
    for category in ("scan", "exfil", "brute"):
        act = Action(
            action_id=f"t-{category}",
            category=category,
            parameters={},
            timestamp=ts,
        )
        result = NullDefence().observe(act)
        assert isinstance(result, DetectionResult)


# ---------------------------------------------------------------------------
# US3 — Stub the detector in unit tests
# ---------------------------------------------------------------------------


def test_check_defence_contract_helper_passes_for_null(action):
    """C-011: check_defence_contract() helper works with NullDefence."""
    result = check_defence_contract(NullDefence(), action)
    assert result is None
