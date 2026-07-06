# Data Model: Defanged Action Library (F07)

## Entities

### ActionDefinition

A frozen dataclass describing one defanged technique at rest (no timestamps, no runtime state).

| Field | Type | Description |
|---|---|---|
| `action_id` | `str` | Globally unique slug, e.g. `"tcp_port_scan"` |
| `category` | `str` | One of `scan`, `brute`, `ssh`, `web`, `dns`, `exfil` |
| `description` | `str` | Human-readable behaviour + Suricata rule family targeted |
| `default_parameters` | `dict[str, Any]` | Non-empty dict of tunable name → default value |
| `suricata_category` | `str` | ET Open rule category this action exercises, e.g. `"ET SCAN"` |

**Constraints**:
- `action_id` must be unique across the registry (enforced at build time).
- `default_parameters` must be non-empty (enforced by safety guard).
- Any string value in `default_parameters` that parses as a globally-routable IP address is a safety violation.

**Method**:
- `to_action(timestamp: datetime) -> Action` — produces an `Action` (F03 contract) with `action_id`, `category`, `parameters=default_parameters`, `timestamp`.

---

### ActionRegistry

Module-level catalogue of all registered `ActionDefinition` objects.

| Attribute | Type | Description |
|---|---|---|
| `_store` | `dict[str, ActionDefinition]` | Internal mapping `action_id → ActionDefinition` |

**Methods**:

| Method | Signature | Behaviour |
|---|---|---|
| `list_actions()` | `() -> list[ActionDefinition]` | Returns all definitions, order stable |
| `get_action(action_id)` | `(str) -> ActionDefinition` | Returns definition or raises `KeyError` |
| `actions_by_category(category)` | `(str) -> list[ActionDefinition]` | Returns subset for that category |

**Invariants**:
- Built once at module import from a static list; raises `ValueError` on duplicate `action_id`.
- Read-only after construction; no mutation methods.

---

### SafetyViolation

A lightweight record emitted by `safety_guard()` for each detected problem.

| Field | Type | Description |
|---|---|---|
| `action_id` | `str` | Which action triggered the violation |
| `field` | `str` | Which field contained the problem (e.g. `"default_parameters"`) |
| `reason` | `str` | Human-readable description of the violation |

**Semantics**: `safety_guard() -> list[SafetyViolation]`. Empty list = all actions pass. Non-empty list = at least one action fails.

---

## Registered Actions (≥15)

| `action_id` | `category` | `suricata_category` | Key tunables |
|---|---|---|---|
| `tcp_port_scan` | `scan` | `ET SCAN` | `target_ip`, `port_range`, `rate_pps`, `timing_ms` |
| `udp_sweep` | `scan` | `ET SCAN` | `target_ip`, `port_range`, `rate_pps` |
| `icmp_ping_sweep` | `scan` | `ET SCAN` | `target_ip`, `count`, `interval_ms` |
| `ssh_brute_force` | `brute` | `ET BRUTE_FORCE` | `target_ip`, `attempts`, `interval_ms`, `username` |
| `ftp_brute_force` | `brute` | `ET BRUTE_FORCE` | `target_ip`, `attempts`, `interval_ms` |
| `http_basic_brute` | `brute` | `ET BRUTE_FORCE` | `target_ip`, `target_port`, `attempts`, `interval_ms` |
| `ssh_user_enum` | `ssh` | `ET SCAN` | `target_ip`, `usernames`, `interval_ms` |
| `ssh_version_probe` | `ssh` | `ET EXPLOIT` | `target_ip`, `target_port` |
| `http_dir_scan` | `web` | `ET WEB_SERVER` | `target_ip`, `target_port`, `wordlist_size`, `rate_rps` |
| `http_sqli_probe` | `web` | `ET WEB_SERVER` | `target_ip`, `target_port`, `payload_variant`, `rate_rps` |
| `http_xss_probe` | `web` | `ET WEB_CLIENT` | `target_ip`, `target_port`, `payload_variant` |
| `dns_zone_transfer` | `dns` | `ET DNS` | `target_ip`, `domain` |
| `dns_subdomain_enum` | `dns` | `ET DNS` | `target_ip`, `domain`, `wordlist_size`, `rate_rps` |
| `dns_exfil` | `exfil` | `ET POLICY` | `target_ip`, `chunk_size_bytes`, `interval_ms` |
| `http_exfil` | `exfil` | `ET TROJAN` | `target_ip`, `target_port`, `payload_size_bytes`, `interval_ms` |

All `target_ip` defaults are `"172.28.0.2"` (aatf-defender address in the lab network).

---

## Relationships

```
ActionDefinition --[to_action()]--> Action (F03 contracts.py)
ActionRegistry 1 --contains--> N ActionDefinition
safety_guard() --scans--> ActionRegistry --emits--> list[SafetyViolation]
```
