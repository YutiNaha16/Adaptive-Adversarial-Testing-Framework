"""Action intensity levels — parameter variation for the parameterized DQN attacker.

Each action supports three execution intensities:
  0 = low   (stealthy: few attempts, small wordlists — near the normal baseline)
  1 = medium (default parameters)
  2 = high   (aggressive: many attempts, large wordlists — clearly anomalous)

Only parameters that affect the ML feature encoder (attempts, wordlist_size, timing_ms,
port_range_start, port_range_end) are varied. Other parameters keep their defaults.
"""

from __future__ import annotations

from typing import Any

INTENSITY_LEVELS: int = 3
INTENSITY_LABELS: list[str] = ["low", "medium", "high"]

_LAB_IP = "172.28.0.2"

# Maps action_id → [low_params, medium_params, high_params]
# Only actions with ML-relevant variable parameters are listed.
# Actions absent from this dict use default_parameters for all intensities.
_OVERRIDES: dict[str, list[dict[str, Any]]] = {
    "ssh_brute_force": [
        {"target_ip": _LAB_IP, "attempts": 2, "interval_ms": 2000, "username": "root"},
        {"target_ip": _LAB_IP, "attempts": 10, "interval_ms": 500, "username": "root"},
        {"target_ip": _LAB_IP, "attempts": 100, "interval_ms": 100, "username": "root"},
    ],
    "ftp_brute_force": [
        {"target_ip": _LAB_IP, "attempts": 2, "interval_ms": 2000},
        {"target_ip": _LAB_IP, "attempts": 8, "interval_ms": 600},
        {"target_ip": _LAB_IP, "attempts": 50, "interval_ms": 100},
    ],
    "http_basic_brute": [
        {"target_ip": _LAB_IP, "target_port": 80, "attempts": 2, "interval_ms": 2000},
        {"target_ip": _LAB_IP, "target_port": 80, "attempts": 12, "interval_ms": 300},
        {"target_ip": _LAB_IP, "target_port": 80, "attempts": 50, "interval_ms": 100},
    ],
    "http_dir_scan": [
        {"target_ip": _LAB_IP, "target_port": 80, "wordlist_size": 3, "rate_rps": 1},
        {"target_ip": _LAB_IP, "target_port": 80, "wordlist_size": 50, "rate_rps": 5},
        {"target_ip": _LAB_IP, "target_port": 80, "wordlist_size": 100, "rate_rps": 10},
    ],
    "dns_subdomain_enum": [
        {"target_ip": _LAB_IP, "domain": "lab.internal", "wordlist_size": 3, "rate_rps": 1},
        {"target_ip": _LAB_IP, "domain": "lab.internal", "wordlist_size": 20, "rate_rps": 3},
        {"target_ip": _LAB_IP, "domain": "lab.internal", "wordlist_size": 100, "rate_rps": 10},
    ],
    "tcp_port_scan": [
        {"target_ip": _LAB_IP, "port_range": "1-100", "rate_pps": 2, "timing_ms": 100},
        {"target_ip": _LAB_IP, "port_range": "1-1024", "rate_pps": 10, "timing_ms": 100},
        {"target_ip": _LAB_IP, "port_range": "1-1024", "rate_pps": 100, "timing_ms": 10},
    ],
}


def get_params_for_intensity(
    action_id: str,
    intensity: int,
    default_parameters: dict[str, Any],
    target_ip: str | None = None,
) -> dict[str, Any]:
    """Return execution parameters for the action at the given intensity level.

    Falls back to default_parameters for actions without intensity overrides.
    target_ip overrides the compiled-in _LAB_IP when provided (e.g. from ExperimentConfig).
    """
    if action_id not in _OVERRIDES:
        return default_parameters
    levels = _OVERRIDES[action_id]
    clamped = max(0, min(intensity, len(levels) - 1))
    params = dict(levels[clamped])
    if target_ip is not None and "target_ip" in params:
        params["target_ip"] = target_ip
    return params
