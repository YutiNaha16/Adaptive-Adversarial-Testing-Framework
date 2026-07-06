"""Tests for AttackGraph (F09) — covers C-001 through C-012."""

from __future__ import annotations

import pytest

from aatf.action_library import REGISTRY
from aatf.attack_graph import ATTACK_GRAPH, AttackGraph

_ENTRY_POINTS = frozenset({"tcp_port_scan", "udp_sweep", "icmp_ping_sweep", "dns_subdomain_enum"})

# ---------------------------------------------------------------------------
# US1 — Entry-Point Actions Always Available (C-001, C-002, C-011, C-012)
# ---------------------------------------------------------------------------


def test_empty_completed_returns_entry_points():
    """C-001: available_actions(set()) returns exactly the 4 entry-point ids."""
    assert set(ATTACK_GRAPH.available_actions(set())) == _ENTRY_POINTS


def test_empty_completed_returns_only_entry_points():
    """C-002: No non-entry-point appears in available_actions(set())."""
    result = set(ATTACK_GRAPH.available_actions(set()))
    assert "ssh_brute_force" not in result
    assert "http_exfil" not in result
    assert "dns_exfil" not in result
    assert result == _ENTRY_POINTS


def test_available_actions_is_sorted():
    """C-011: available_actions result is in ascending lexicographic order."""
    result = ATTACK_GRAPH.available_actions(set())
    assert result == sorted(result)


def test_attack_graph_is_module_level_constant():
    """C-012: ATTACK_GRAPH is accessible as a module-level constant."""
    assert isinstance(ATTACK_GRAPH, AttackGraph)


# ---------------------------------------------------------------------------
# US2 — Completing Actions Unlocks Successors (C-003, C-004, C-005, C-006, C-008, C-010)
# ---------------------------------------------------------------------------


def test_tcp_port_scan_unlocks_successors():
    """C-003: Completing tcp_port_scan unlocks its 4 direct successors."""
    result = set(ATTACK_GRAPH.available_actions({"tcp_port_scan"}))
    assert {"ssh_brute_force", "ftp_brute_force", "http_dir_scan", "ssh_user_enum"} <= result


def test_dns_subdomain_enum_unlocks_dns_zone_transfer():
    """C-004: Completing dns_subdomain_enum unlocks dns_zone_transfer."""
    assert "dns_zone_transfer" in ATTACK_GRAPH.available_actions({"dns_subdomain_enum"})


def test_http_sqli_probe_unlocks_http_exfil():
    """C-005: Completing http_sqli_probe unlocks http_exfil."""
    assert "http_exfil" in ATTACK_GRAPH.available_actions({"http_sqli_probe"})


def test_dns_zone_transfer_unlocks_dns_exfil():
    """C-006: Completing dns_zone_transfer unlocks dns_exfil."""
    assert "dns_exfil" in ATTACK_GRAPH.available_actions({"dns_zone_transfer"})


def test_unknown_completed_id_ignored():
    """C-008: Unknown action_id in completed is silently ignored — no exception, same as empty."""
    result_unknown = ATTACK_GRAPH.available_actions({"nonexistent_xyz"})
    result_empty = ATTACK_GRAPH.available_actions(set())
    assert result_unknown == result_empty


def test_available_actions_is_non_destructive():
    """C-010: Calling available_actions twice returns identical results."""
    first = ATTACK_GRAPH.available_actions({"tcp_port_scan"})
    second = ATTACK_GRAPH.available_actions({"tcp_port_scan"})
    assert first == second


# ---------------------------------------------------------------------------
# US3 — Full Graph Coverage (C-007, C-009)
# ---------------------------------------------------------------------------


def test_all_15_actions_available_when_all_completed():
    """C-007: All 15 action_ids returned when all 15 completed."""
    all_ids = {d.action_id for d in REGISTRY.list_actions()}
    assert set(ATTACK_GRAPH.available_actions(all_ids)) == all_ids


def test_invalid_action_id_raises_at_construction():
    """C-009: Constructing AttackGraph with unknown action_id raises ValueError."""
    with pytest.raises(ValueError, match="unknown action_id"):
        AttackGraph(entry_points=frozenset({"nonexistent_id"}), edges={})
