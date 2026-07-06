from __future__ import annotations

import importlib
import socket
import subprocess
from datetime import UTC, datetime

import pytest

from aatf.action_library import (
    REGISTRY,
    ActionDefinition,
    ActionRegistry,
    safety_guard,
)
from aatf.contracts import Action

# ---------------------------------------------------------------------------
# Phase 3 — US1: Action Registry (C-001 to C-004, C-013, C-014)
# ---------------------------------------------------------------------------


def test_registry_has_at_least_15_actions() -> None:  # C-001
    assert len(REGISTRY.list_actions()) >= 15


def test_all_action_ids_are_unique() -> None:  # C-002
    actions = REGISTRY.list_actions()
    assert len({a.action_id for a in actions}) == len(actions)


def test_all_six_categories_present() -> None:  # C-003
    for cat in ("scan", "brute", "ssh", "web", "dns", "exfil"):
        assert len(REGISTRY.actions_by_category(cat)) >= 1, f"No actions for category {cat!r}"


def test_get_action_round_trips() -> None:  # C-004
    for a in REGISTRY.list_actions():
        assert REGISTRY.get_action(a.action_id) == a


def test_get_action_raises_key_error_on_unknown_id() -> None:  # C-013
    with pytest.raises(KeyError):
        REGISTRY.get_action("nonexistent_id")


def test_actions_by_category_unknown_returns_empty_list() -> None:  # C-014
    assert REGISTRY.actions_by_category("nonexistent_cat") == []


# ---------------------------------------------------------------------------
# Phase 4 — US2: Parameterised Behaviour Descriptions (C-005 to C-009)
# ---------------------------------------------------------------------------


def test_all_actions_have_non_empty_parameters() -> None:  # C-005
    for a in REGISTRY.list_actions():
        assert a.default_parameters != {}, f"{a.action_id} has empty parameters"


def test_all_actions_have_non_empty_description() -> None:  # C-006
    for a in REGISTRY.list_actions():
        assert a.description.strip() != "", f"{a.action_id} has empty description"


def test_all_actions_have_suricata_category() -> None:  # C-007
    for a in REGISTRY.list_actions():
        assert a.suricata_category.strip() != "", f"{a.action_id} has empty suricata_category"


def test_to_action_produces_valid_action() -> None:  # C-008
    a = REGISTRY.list_actions()[0]
    ts = datetime.now(UTC)
    action = a.to_action(ts)
    Action.model_validate(action.model_dump())


def test_to_action_preserves_fields() -> None:  # C-009
    a = REGISTRY.list_actions()[0]
    ts = datetime.now(UTC)
    action = a.to_action(ts)
    assert action.action_id == a.action_id
    assert action.category == a.category
    assert action.parameters == a.default_parameters


# ---------------------------------------------------------------------------
# Phase 5 — US3: Safety Guard (C-010 to C-012, C-015)
# ---------------------------------------------------------------------------


def test_safety_guard_clean_on_registered_library() -> None:  # C-010
    assert safety_guard(REGISTRY) == []


def test_safety_guard_flags_external_ip() -> None:  # C-011
    bad = ActionDefinition(
        action_id="bad_external",
        category="scan",
        description="test",
        default_parameters={"target": "8.8.8.8"},
        suricata_category="ET SCAN",
    )
    bad_registry = ActionRegistry([bad])
    violations = safety_guard(bad_registry)
    assert len(violations) >= 1
    assert any(v.action_id == "bad_external" for v in violations)


def test_safety_guard_flags_empty_parameters() -> None:  # C-012
    empty = ActionDefinition(
        action_id="empty_params",
        category="scan",
        description="test",
        default_parameters={},
        suricata_category="ET SCAN",
    )
    empty_registry = ActionRegistry([empty])
    violations = safety_guard(empty_registry)
    assert len(violations) >= 1
    assert any(v.action_id == "empty_params" for v in violations)


def test_no_io_at_import(monkeypatch: pytest.MonkeyPatch) -> None:  # C-015
    import aatf.action_library as mod

    def _no_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("socket.socket called at import time")

    def _no_popen(*args: object, **kwargs: object) -> None:
        raise AssertionError("subprocess.Popen called at import time")

    monkeypatch.setattr(socket, "socket", _no_socket)
    monkeypatch.setattr(subprocess, "Popen", _no_popen)
    importlib.reload(mod)
