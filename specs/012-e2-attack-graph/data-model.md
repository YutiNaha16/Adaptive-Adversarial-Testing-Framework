# Data Model: Attack Graph Staging (F09)

## Entities

### AttackGraph

The sole data structure. Immutable after construction; validated against `REGISTRY` at construction time.

| Field | Type | Description |
|---|---|---|
| `entry_points` | `frozenset[str]` | action_ids that are always available regardless of completed set |
| `edges` | `dict[str, frozenset[str]]` | Maps each source action_id to the set of action_ids it unlocks |

**Invariants**:
- Every action_id in `entry_points` exists in `REGISTRY` (validated at construction)
- Every action_id in every `edges` value exists in `REGISTRY` (validated at construction)
- Every action_id in every `edges` key need not be in `REGISTRY` — but in practice all keys are entry_points or successors, so they are validated transitively
- Every action_id in `REGISTRY` is reachable from `entry_points` by following edges (validated at construction)

**Constructor**: `AttackGraph(entry_points: frozenset[str], edges: dict[str, frozenset[str]])`
- Validates all ids against `REGISTRY`; raises `ValueError(f"unknown action_id in attack graph: {id!r}")` on first unknown
- Validates reachability: every REGISTRY id must appear in entry_points or in at least one edges value

**Method**: `available_actions(completed: set[str]) -> list[str]`
- Returns `sorted(entry_points | {s for aid in completed for s in edges.get(aid, frozenset())})`
- `completed` may contain any strings; unknown ids are silently ignored
- Pure function — no side effects, no mutation

---

### ATTACK_GRAPH (module-level constant)

Module-level instance of `AttackGraph` constructed at import time with the canonical v1 topology.

**Canonical v1 topology** — covers all 15 F07 actions, no islands:

```
Entry points (no prerequisites):
  tcp_port_scan, udp_sweep, icmp_ping_sweep, dns_subdomain_enum

Unlock edges:
  tcp_port_scan     → ssh_brute_force, ftp_brute_force, http_dir_scan, ssh_user_enum
  udp_sweep         → dns_zone_transfer
  icmp_ping_sweep   → ssh_version_probe
  dns_subdomain_enum → dns_zone_transfer
  ssh_brute_force   → ssh_version_probe
  http_dir_scan     → http_sqli_probe, http_xss_probe, http_basic_brute
  http_sqli_probe   → http_exfil
  dns_zone_transfer → dns_exfil
```

**Reachability trace** (verifying no islands):

| action_id | How it becomes available |
|---|---|
| `tcp_port_scan` | entry point |
| `udp_sweep` | entry point |
| `icmp_ping_sweep` | entry point |
| `dns_subdomain_enum` | entry point |
| `ssh_brute_force` | via tcp_port_scan |
| `ftp_brute_force` | via tcp_port_scan |
| `http_dir_scan` | via tcp_port_scan |
| `ssh_user_enum` | via tcp_port_scan |
| `dns_zone_transfer` | via udp_sweep or dns_subdomain_enum |
| `ssh_version_probe` | via icmp_ping_sweep or ssh_brute_force |
| `http_sqli_probe` | via http_dir_scan |
| `http_xss_probe` | via http_dir_scan |
| `http_basic_brute` | via http_dir_scan |
| `http_exfil` | via http_sqli_probe |
| `dns_exfil` | via dns_zone_transfer |

All 15 ✓

---

## Relationships

```
REGISTRY (F07)
  └── ActionDefinition.action_id strings
        └── validated by AttackGraph.__post_init__

ATTACK_GRAPH: AttackGraph
  ├── entry_points: frozenset[str]  (4 ids)
  └── edges: dict[str, frozenset[str]]  (8 source nodes → successors)
        └── available_actions(completed) → list[str]
```

**No dependency on F08 (ActionExecutor) or any Defence class** — pure topology.
