"""Tests for action_intensity module — intensity levels and target_ip override."""

from __future__ import annotations

from aatf.action_intensity import INTENSITY_LEVELS, get_params_for_intensity


def test_intensity_levels_constant():
    assert INTENSITY_LEVELS == 3


def test_returns_default_for_unknown_action():
    defaults = {"foo": "bar"}
    assert get_params_for_intensity("nonexistent_action", 1, defaults) is defaults


def test_low_intensity_fewer_attempts():
    low = get_params_for_intensity("ssh_brute_force", 0, {})
    high = get_params_for_intensity("ssh_brute_force", 2, {})
    assert low["attempts"] < high["attempts"]


def test_target_ip_override_replaces_lab_ip():
    params = get_params_for_intensity("ssh_brute_force", 1, {}, target_ip="10.9.8.7")
    assert params["target_ip"] == "10.9.8.7"


def test_target_ip_none_keeps_compiled_ip():
    params_no_override = get_params_for_intensity("ssh_brute_force", 1, {}, target_ip=None)
    params_default = get_params_for_intensity("ssh_brute_force", 1, {})
    assert params_no_override["target_ip"] == params_default["target_ip"]


def test_intensity_clamped_above_max():
    params_2 = get_params_for_intensity("ssh_brute_force", 2, {})
    params_99 = get_params_for_intensity("ssh_brute_force", 99, {})
    assert params_2 == params_99


def test_intensity_clamped_below_min():
    params_0 = get_params_for_intensity("ssh_brute_force", 0, {})
    params_neg = get_params_for_intensity("ssh_brute_force", -5, {})
    assert params_0 == params_neg
