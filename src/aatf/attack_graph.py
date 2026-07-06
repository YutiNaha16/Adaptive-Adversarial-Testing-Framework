"""Attack graph — models which actions become available after prior actions succeed."""

from __future__ import annotations

from dataclasses import dataclass

from aatf.action_library import REGISTRY


@dataclass(frozen=True)
class AttackGraph:
    """Directed graph of action unlock relationships."""

    entry_points: frozenset[str]
    edges: dict[str, frozenset[str]]

    def __post_init__(self) -> None:
        registry_ids = {d.action_id for d in REGISTRY.list_actions()}

        # All ids referenced in the graph must exist in REGISTRY
        all_referenced = set(self.entry_points)
        for successors in self.edges.values():
            all_referenced |= successors
        for action_id in all_referenced:
            if action_id not in registry_ids:
                raise ValueError(f"unknown action_id in attack graph: {action_id!r}")

        # Every REGISTRY action_id must be reachable (entry point or successor)
        reachable = set(self.entry_points)
        for successors in self.edges.values():
            reachable |= successors
        for action_id in registry_ids:
            if action_id not in reachable:
                raise ValueError(
                    f"action_id {action_id!r} is in REGISTRY but unreachable in attack graph"
                )

    def available_actions(self, completed: set[str]) -> list[str]:
        """Return sorted list of action_ids available given the completed set."""
        reachable = set(self.entry_points)
        for action_id in completed:
            reachable |= self.edges.get(action_id, frozenset())
        return sorted(reachable)


ATTACK_GRAPH = AttackGraph(
    entry_points=frozenset({"tcp_port_scan", "udp_sweep", "icmp_ping_sweep", "dns_subdomain_enum"}),
    edges={
        "tcp_port_scan": frozenset(
            {"ssh_brute_force", "ftp_brute_force", "http_dir_scan", "ssh_user_enum"}
        ),
        "udp_sweep": frozenset({"dns_zone_transfer"}),
        "icmp_ping_sweep": frozenset({"ssh_version_probe"}),
        "dns_subdomain_enum": frozenset({"dns_zone_transfer"}),
        "ssh_brute_force": frozenset({"ssh_version_probe"}),
        "http_dir_scan": frozenset({"http_sqli_probe", "http_xss_probe", "http_basic_brute"}),
        "http_sqli_probe": frozenset({"http_exfil"}),
        "dns_zone_transfer": frozenset({"dns_exfil"}),
    },
)
