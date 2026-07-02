from __future__ import annotations

import ipaddress
import pathlib
import subprocess

import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_COMPOSE_FILE = pathlib.Path("lab/docker-compose.yml")


def _load_compose() -> dict:
    return yaml.safe_load(_COMPOSE_FILE.read_text())


# ---------------------------------------------------------------------------
# US1: Structural isolation tests (Docker-free)
# ---------------------------------------------------------------------------


def test_lab_config_declares_internal() -> None:
    """C-012: lab network must declare internal: true."""
    cfg = _load_compose()
    assert cfg["networks"]["lab"]["internal"] is True, (
        "lab network must declare 'internal: true' — isolation NOT enforced"
    )


def test_lab_config_network_name() -> None:
    """C-013: lab network name must be aatf-lab."""
    cfg = _load_compose()
    assert cfg["networks"]["lab"]["name"] == "aatf-lab"


def test_no_host_ports_on_experiment_containers() -> None:
    """C-014: no experiment container may publish host ports."""
    cfg = _load_compose()
    for role in ("attacker", "defender", "environment"):
        svc = cfg["services"][role]
        assert "ports" not in svc, f"Service '{role}' must not publish host ports"


def test_lab_subnet_is_nonroutable() -> None:
    """C-015: lab subnet must be RFC1918 or link-local (not publicly routable)."""
    cfg = _load_compose()
    subnet_str = cfg["networks"]["lab"]["ipam"]["config"][0]["subnet"]
    network = ipaddress.ip_network(subnet_str, strict=False)
    assert network.is_private, (
        f"Lab subnet {subnet_str} is publicly routable — must be RFC1918 or link-local"
    )


# ---------------------------------------------------------------------------
# US2: Fail-closed external target guard tests (Docker-free)
# ---------------------------------------------------------------------------
from aatf.isolation import ExternalTargetError, assert_lab_internal  # noqa: E402


def test_external_target_error_is_value_error() -> None:
    """C-001: ExternalTargetError must be a ValueError subclass."""
    err = ExternalTargetError("8.8.8.8", "publicly routable")
    assert isinstance(err, ValueError)
    assert err.target == "8.8.8.8"
    assert err.reason == "publicly routable"


def test_guard_rejects_public_ip() -> None:
    """C-002: public IPv4 must be rejected."""
    with pytest.raises(ExternalTargetError):
        assert_lab_internal("8.8.8.8")


def test_guard_rejects_public_ipv6() -> None:
    """C-003: public IPv6 must be rejected."""
    with pytest.raises(ExternalTargetError):
        assert_lab_internal("2001:4860:4860::8888")


def test_guard_rejects_rfc1918_outside_lab_subnet() -> None:
    """C-004: RFC1918 address outside the lab subnet must be rejected."""
    with pytest.raises(ExternalTargetError):
        assert_lab_internal("192.168.1.1")


def test_guard_passes_lab_internal_ip() -> None:
    """C-005: address inside lab subnet must pass."""
    assert assert_lab_internal("172.28.0.5") is None


def test_guard_passes_loopback_ip() -> None:
    """C-006: loopback IPv4 must pass."""
    assert assert_lab_internal("127.0.0.1") is None


def test_guard_passes_localhost_hostname() -> None:
    """C-007: localhost hostname must pass (resolves to loopback)."""
    assert assert_lab_internal("localhost") is None


def test_guard_custom_allowed_networks_pass() -> None:
    """C-008: address in custom allowed_networks must pass."""
    assert assert_lab_internal("10.0.0.5", allowed_networks=["10.0.0.0/8"]) is None


def test_guard_custom_allowed_networks_reject() -> None:
    """C-009: address outside custom allowed_networks must be rejected."""
    with pytest.raises(ExternalTargetError):
        assert_lab_internal("172.28.0.5", allowed_networks=["10.0.0.0/8"])


def test_guard_subnet_boundary_address_passes() -> None:
    """C-010: network address of lab subnet must pass."""
    assert assert_lab_internal("172.28.0.0") is None


def test_guard_address_just_outside_subnet_rejected() -> None:
    """C-011: address just outside lab subnet must be rejected."""
    with pytest.raises(ExternalTargetError):
        assert_lab_internal("172.29.0.1")


# ---------------------------------------------------------------------------
# US3: Live egress probe (Docker-dependent — skips when lab is not running)
# ---------------------------------------------------------------------------


def _lab_is_running() -> bool:
    result = subprocess.run(
        ["docker", "inspect", "aatf-attacker"],
        capture_output=True,
    )
    return result.returncode == 0


@pytest.mark.docker
def test_live_egress_blocked() -> None:
    """C-016/C-017: outbound connection from lab network must be blocked.
    Skips when lab is not running (C-017).
    """
    if not _lab_is_running():
        pytest.skip("lab not running — run 'make lab-up' first")
    result = subprocess.run(
        ["bash", "lab/scripts/check-isolation.sh"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Isolation BREACH detected!\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "ISOLATED" in result.stdout
