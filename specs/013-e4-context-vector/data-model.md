# Data Model: Context Vector Builder (F13)

## Entities

### EpisodeState

Plain mutable dataclass — snapshot of all observable episode data at one step.

| Field | Type | Validation | Description |
|-------|------|------------|-------------|
| `completed_actions` | `set[str]` | all ids in REGISTRY | Actions that have been executed and succeeded this episode |
| `detection_history` | `dict[str, list[bool]]` | keys in REGISTRY | Per-action execution log; True=detected, False=undetected |
| `alert_history` | `list[bool]` | — | Step-level rolling log; True=any alert fired that step |
| `step` | `int` | >= 0 | Current step index within the episode |
| `start_time` | `float` | — | Unix timestamp of episode start (from `time.time()`) |
| `fired_categories` | `set[str]` | — | Suricata ET Open rule categories that have fired this episode |

**Validation** (in `__post_init__`):
- `step >= 0` — raises `ValueError("step must be non-negative")`
- every id in `completed_actions` must be in `{d.action_id for d in REGISTRY.list_actions()}` — raises `ValueError(f"unknown action_id: {id!r}")`

**Lifecycle**: Created at episode start (all collections empty, step=0, start_time=time.time()); fields appended/updated after each step by the episode loop (F16). Passed read-only to `build_context`.

---

### ContextVector

`np.ndarray(shape=(CONTEXT_DIM,), dtype=np.float32)` — the RL attacker's observation input.

Not a named class; the return type of `build_context`. Downstream code references `CONTEXT_DIM` for the shape.

---

## Vector Layout

`CONTEXT_DIM = 50`

| Slice | Indices | Family | Width | Description |
|-------|---------|--------|-------|-------------|
| `vec[0:10]` | 0–9 | alert_history | 10 | Last 10 step-level detection results; 1.0=detected, 0.0=undetected; slot 0=oldest, slot 9=most recent; zero-padded left |
| `vec[10:25]` | 10–24 | attack_progress | 15 | Binary flags per action in sorted order; 1.0 if in completed_actions |
| `vec[25:40]` | 25–39 | technique_history | 15 | Lifetime detection rate per action; 0.0 if never executed |
| `vec[40:42]` | 40–41 | timing | 2 | [step/100 clipped to [0,1], elapsed/3600 clipped to [0,1]] |
| `vec[42:50]` | 42–49 | rule_category_fired | 8 | Binary flags for 8 ET Open categories (see below) |

---

## Action Slot Ordering (attack_progress & technique_history)

Lexicographic sort of all 15 REGISTRY action_ids:

| Slot offset | action_id |
|-------------|-----------|
| 0 | dns_exfil |
| 1 | dns_subdomain_enum |
| 2 | dns_zone_transfer |
| 3 | ftp_brute_force |
| 4 | http_basic_brute |
| 5 | http_dir_scan |
| 6 | http_exfil |
| 7 | http_sqli_probe |
| 8 | http_xss_probe |
| 9 | icmp_ping_sweep |
| 10 | ssh_brute_force |
| 11 | ssh_user_enum |
| 12 | ssh_version_probe |
| 13 | tcp_port_scan |
| 14 | udp_sweep |

---

## Rule Category Slot Ordering (rule_category_fired)

Fixed ordered list (indices 42–49):

| Slot offset | Category string |
|-------------|-----------------|
| 0 | ET SCAN |
| 1 | ET EXPLOIT |
| 2 | ET BRUTE_FORCE |
| 3 | ET WEB_SPECIFIC_APPS |
| 4 | ET DNS |
| 5 | ET POLICY |
| 6 | ET TROJAN |
| 7 | ET INFO |

---

## Constants

| Name | Value | Location |
|------|-------|----------|
| `CONTEXT_DIM` | 50 | `src/aatf/context_vector.py` |
| `ALERT_WINDOW` | 10 | `src/aatf/context_vector.py` |
| `MAX_STEPS` | 100 | `src/aatf/context_vector.py` |
| `MAX_EPISODE_SECONDS` | 3600 | `src/aatf/context_vector.py` |
| `ET_CATEGORIES` | list of 8 strings | `src/aatf/context_vector.py` |
