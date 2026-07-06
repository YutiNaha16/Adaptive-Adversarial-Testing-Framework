from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from aatf.contracts import Action


@dataclass(frozen=True)
class ActionDefinition:
    action_id: str
    category: str
    description: str
    default_parameters: dict[str, Any]
    suricata_category: str

    def to_action(self, timestamp: datetime) -> Action:
        return Action(
            action_id=self.action_id,
            category=self.category,
            parameters=self.default_parameters,
            timestamp=timestamp,
        )


@dataclass
class SafetyViolation:
    action_id: str
    field: str
    reason: str


class ActionRegistry:
    def __init__(self, definitions: list[ActionDefinition]) -> None:
        self._store: dict[str, ActionDefinition] = {}
        for defn in definitions:
            if defn.action_id in self._store:
                raise ValueError(f"Duplicate action_id: {defn.action_id!r}")
            self._store[defn.action_id] = defn

    def list_actions(self) -> list[ActionDefinition]:
        return list(self._store.values())

    def get_action(self, action_id: str) -> ActionDefinition:
        return self._store[action_id]

    def actions_by_category(self, category: str) -> list[ActionDefinition]:
        return [a for a in self._store.values() if a.category == category]


def safety_guard(registry: ActionRegistry) -> list[SafetyViolation]:
    violations: list[SafetyViolation] = []
    for action in registry.list_actions():
        if not action.default_parameters:
            violations.append(
                SafetyViolation(
                    action_id=action.action_id,
                    field="default_parameters",
                    reason="empty parameters dict — no tunables defined",
                )
            )
            continue
        for key, value in action.default_parameters.items():
            if not isinstance(value, str):
                continue
            try:
                addr = ipaddress.ip_address(value)
            except ValueError:
                continue
            if addr.is_global:
                violations.append(
                    SafetyViolation(
                        action_id=action.action_id,
                        field=f"default_parameters[{key!r}]",
                        reason=(
                            f"publicly routable IP address {value!r} — only 172.28.0.0/16 permitted"
                        ),
                    )
                )
    return violations


_LAB_IP = "172.28.0.2"

_DEFINITIONS: list[ActionDefinition] = [
    # --- scan (3) ---
    ActionDefinition(
        action_id="tcp_port_scan",
        category="scan",
        description=(
            "Simulates a TCP SYN port scan against a target host across a configurable "
            "port range at a given packet rate. Exercises ET SCAN rules."
        ),
        default_parameters={
            "target_ip": _LAB_IP,
            "port_range": "1-1024",
            "rate_pps": 10,
            "timing_ms": 100,
        },
        suricata_category="ET SCAN",
    ),
    ActionDefinition(
        action_id="udp_sweep",
        category="scan",
        description=(
            "Sends UDP probes to a range of ports to enumerate open UDP services. "
            "Exercises ET SCAN rules."
        ),
        default_parameters={
            "target_ip": _LAB_IP,
            "port_range": "53-161",
            "rate_pps": 5,
        },
        suricata_category="ET SCAN",
    ),
    ActionDefinition(
        action_id="icmp_ping_sweep",
        category="scan",
        description=(
            "Sends ICMP echo requests to discover live hosts on the lab subnet. "
            "Exercises ET SCAN rules."
        ),
        default_parameters={
            "target_ip": _LAB_IP,
            "count": 10,
            "interval_ms": 200,
        },
        suricata_category="ET SCAN",
    ),
    # --- brute (3) ---
    ActionDefinition(
        action_id="ssh_brute_force",
        category="brute",
        description=(
            "Simulates repeated SSH authentication attempts at a configurable rate "
            "to test brute-force detection thresholds. Exercises ET BRUTE_FORCE rules."
        ),
        default_parameters={
            "target_ip": _LAB_IP,
            "attempts": 10,
            "interval_ms": 500,
            "username": "root",
        },
        suricata_category="ET BRUTE_FORCE",
    ),
    ActionDefinition(
        action_id="ftp_brute_force",
        category="brute",
        description=(
            "Simulates repeated FTP login attempts to exercise FTP brute-force "
            "detection. Exercises ET BRUTE_FORCE rules."
        ),
        default_parameters={
            "target_ip": _LAB_IP,
            "attempts": 8,
            "interval_ms": 600,
        },
        suricata_category="ET BRUTE_FORCE",
    ),
    ActionDefinition(
        action_id="http_basic_brute",
        category="brute",
        description=(
            "Simulates repeated HTTP Basic Auth login attempts against a web endpoint "
            "to test credential-stuffing detection. Exercises ET BRUTE_FORCE rules."
        ),
        default_parameters={
            "target_ip": _LAB_IP,
            "target_port": 80,
            "attempts": 12,
            "interval_ms": 300,
        },
        suricata_category="ET BRUTE_FORCE",
    ),
    # --- ssh (2) ---
    ActionDefinition(
        action_id="ssh_user_enum",
        category="ssh",
        description=(
            "Probes SSH username validity by timing authentication failures for "
            "a list of candidate usernames. Exercises ET SCAN rules."
        ),
        default_parameters={
            "target_ip": _LAB_IP,
            "usernames": ["root", "admin", "ubuntu"],
            "interval_ms": 400,
        },
        suricata_category="ET SCAN",
    ),
    ActionDefinition(
        action_id="ssh_version_probe",
        category="ssh",
        description=(
            "Connects to SSH port and reads the server banner to identify software "
            "version for fingerprinting. Exercises ET EXPLOIT rules."
        ),
        default_parameters={
            "target_ip": _LAB_IP,
            "target_port": 22,
        },
        suricata_category="ET EXPLOIT",
    ),
    # --- web (3) ---
    ActionDefinition(
        action_id="http_dir_scan",
        category="web",
        description=(
            "Sends HTTP GET requests for common directory paths to discover hidden "
            "resources. Exercises ET WEB_SERVER rules."
        ),
        default_parameters={
            "target_ip": _LAB_IP,
            "target_port": 80,
            "wordlist_size": 50,
            "rate_rps": 5,
        },
        suricata_category="ET WEB_SERVER",
    ),
    ActionDefinition(
        action_id="http_sqli_probe",
        category="web",
        description=(
            "Sends HTTP requests containing SQL injection pattern strings to test "
            "whether WAF or IDS rules fire. Exercises ET WEB_SERVER rules."
        ),
        default_parameters={
            "target_ip": _LAB_IP,
            "target_port": 80,
            "payload_variant": "single_quote",
            "rate_rps": 2,
        },
        suricata_category="ET WEB_SERVER",
    ),
    ActionDefinition(
        action_id="http_xss_probe",
        category="web",
        description=(
            "Sends HTTP requests containing cross-site scripting pattern strings to "
            "trigger client-side attack detection rules. Exercises ET WEB_CLIENT rules."
        ),
        default_parameters={
            "target_ip": _LAB_IP,
            "target_port": 80,
            "payload_variant": "script_tag",
        },
        suricata_category="ET WEB_CLIENT",
    ),
    # --- dns (2) ---
    ActionDefinition(
        action_id="dns_zone_transfer",
        category="dns",
        description=(
            "Sends a DNS AXFR (zone transfer) request to enumerate all DNS records "
            "for a domain. Exercises ET DNS rules."
        ),
        default_parameters={
            "target_ip": _LAB_IP,
            "domain": "lab.internal",
        },
        suricata_category="ET DNS",
    ),
    ActionDefinition(
        action_id="dns_subdomain_enum",
        category="dns",
        description=(
            "Sends DNS A record queries for a wordlist of subdomains to discover "
            "internal hostnames. Exercises ET DNS rules."
        ),
        default_parameters={
            "target_ip": _LAB_IP,
            "domain": "lab.internal",
            "wordlist_size": 20,
            "rate_rps": 3,
        },
        suricata_category="ET DNS",
    ),
    # --- exfil (2) ---
    ActionDefinition(
        action_id="dns_exfil",
        category="exfil",
        description=(
            "Encodes data in DNS query labels to simulate DNS-tunnelling exfiltration. "
            "Exercises ET POLICY rules."
        ),
        default_parameters={
            "target_ip": _LAB_IP,
            "chunk_size_bytes": 32,
            "interval_ms": 500,
        },
        suricata_category="ET POLICY",
    ),
    ActionDefinition(
        action_id="http_exfil",
        category="exfil",
        description=(
            "Sends HTTP POST requests carrying a payload that resembles outbound "
            "data exfiltration over HTTP. Exercises ET TROJAN rules."
        ),
        default_parameters={
            "target_ip": _LAB_IP,
            "target_port": 80,
            "payload_size_bytes": 256,
            "interval_ms": 1000,
        },
        suricata_category="ET TROJAN",
    ),
]

REGISTRY: ActionRegistry = ActionRegistry(_DEFINITIONS)
