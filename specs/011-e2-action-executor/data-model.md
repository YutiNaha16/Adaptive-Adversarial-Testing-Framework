# Data Model: Action Executor (F08)

## Entities

### ExecutionResult

Returned by `ActionExecutor.execute()` for every call.

| Field | Type | Description |
|---|---|---|
| `action_id` | `str` | Mirrors `Action.action_id` |
| `category` | `str` | Mirrors `Action.category` |
| `success` | `bool` | True if all probes emitted without unhandled error |
| `emitted_count` | `int` | Number of probes/packets/requests actually sent (≥ 0) |
| `error` | `str \| None` | Error message if `success=False`; None on success |

**Invariants**:
- `emitted_count >= 1` on success (rate=0 is promoted to 1)
- `emitted_count == 0` only when `success=False` and no probes were sent (e.g. guard raised or unknown handler)
- `error is None` iff `success=True`

---

### ExternalTargetError

Raised by `ActionExecutor.execute()` before any traffic when `target_ip` is outside `172.28.0.0/16`.

| Field | Type | Description |
|---|---|---|
| message | `str` | Human-readable: `"target_ip {ip!r} is outside lab network 172.28.0.0/16"` |

Inherits from `ValueError`.

---

### ActionExecutor

The main executor class.

| Attribute | Type | Description |
|---|---|---|
| `_rng` | `random.Random` | Seeded RNG instance; same seed = same jitter sequence |
| `_send_fn` | `SendFn` | Injectable network primitive `(host, port, payload) -> None` |
| `_sleep_fn` | `SleepFn` | Injectable sleep primitive `(seconds: float) -> None` |
| `_handlers` | `dict[str, HandlerFn]` | Maps `action_id → handler function` |

**Constructor**: `ActionExecutor(seed: int, send_fn: SendFn | None = None, sleep_fn: SleepFn | None = None)`
- If `send_fn` is None, uses the real socket-based implementation.
- If `sleep_fn` is None, uses `time.sleep`.

**Method**: `execute(action: Action) -> ExecutionResult`
1. Extract `target_ip = action.parameters.get("target_ip", "172.28.0.2")`
2. Validate `target_ip` against `172.28.0.0/16` — raise `ExternalTargetError` if outside
3. Look up handler by `action.action_id` — return failure result if unknown
4. Call handler; catch exceptions; return `ExecutionResult`

---

### Type Aliases

```
SendFn   = Callable[[str, int, bytes], None]   # (host, port, payload)
SleepFn  = Callable[[float], None]             # (seconds)
HandlerFn = Callable[[Action, random.Random, SendFn, SleepFn], int]
           # returns emitted_count
```

---

## Handler Registry (15 entries)

| `action_id` | Port(s) | Probe type | ET Open target |
|---|---|---|---|
| `tcp_port_scan` | parsed from `port_range` | TCP SYN (connect) | ET SCAN |
| `udp_sweep` | parsed from `port_range` | UDP send | ET SCAN |
| `icmp_ping_sweep` | 7 (echo) | TCP connect | ET SCAN |
| `ssh_brute_force` | 22 | TCP connect × `attempts` | ET BRUTE_FORCE |
| `ftp_brute_force` | 21 | TCP connect × `attempts` | ET BRUTE_FORCE |
| `http_basic_brute` | `target_port` | HTTP GET with Auth header × `attempts` | ET BRUTE_FORCE |
| `ssh_user_enum` | 22 | TCP connect + read banner per username | ET SCAN |
| `ssh_version_probe` | `target_port` (22) | TCP connect + read banner | ET EXPLOIT |
| `http_dir_scan` | `target_port` | HTTP GET /path × `wordlist_size` | ET WEB_SERVER |
| `http_sqli_probe` | `target_port` | HTTP GET `/?q=1+UNION+SELECT+1--` × `rate_rps` | ET WEB_SERVER |
| `http_xss_probe` | `target_port` | HTTP GET `/?q=<script>alert(1)</script>` | ET WEB_CLIENT |
| `dns_zone_transfer` | 53 | DNS AXFR query bytes | ET DNS |
| `dns_subdomain_enum` | 53 | DNS A query bytes × `wordlist_size` | ET DNS |
| `dns_exfil` | 53 | DNS query with encoded data bytes × `chunk_size` | ET POLICY |
| `http_exfil` | `target_port` | HTTP POST with payload body | ET TROJAN |

---

## Relationships

```
Action (F03) ──[execute()]──> ActionExecutor
                                  │
                                  ├── ExternalTargetError (raised on bad target)
                                  │
                                  └── ExecutionResult (returned on success/failure)

ActionExecutor
  ├── _rng: random.Random (seeded)
  ├── _send_fn: SendFn (injectable)
  ├── _sleep_fn: SleepFn (injectable)
  └── _handlers: dict[action_id → HandlerFn]
```
