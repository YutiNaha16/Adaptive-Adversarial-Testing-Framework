# Data Model: Suricata Defence Adapter (F11)

No new persistent entities. This feature adds one concrete class behind the Defence interface
and uses the existing F03 data contracts as input/output.

---

## Entities (new)

### SuricataDefence *(concrete Defence implementation)*

**File**: `src/aatf/suricata_defence.py`

| Attribute | Kind | Type | Description |
|-----------|------|------|-------------|
| `_eve_path` | instance | `pathlib.Path` | Path to eve.json file |
| `_cursor` | instance | `int` | Byte offset of last read position (0 = start of file) |
| `observe` | method | `(Action) → DetectionResult` | Read new alerts since `_cursor`, return result |

**State transitions**:
```
Initial state: _cursor = 0
After each observe() call: _cursor = new EOF position
On file truncation detected: _cursor reset to 0, re-read from start
```

**Construction**: `SuricataDefence(eve_path: str | pathlib.Path)`

---

### EveAlert *(internal parse result — not a public entity)*

Represents one parsed alert line from eve.json. Lives only inside `observe()` — never
exposed to callers.

| Field | Type | Source in eve.json |
|-------|------|--------------------|
| `signature_id` | `int` | `alert.signature_id` |
| `event_type` | `str` | `event_type` (must equal `"alert"`) |

Lines where `event_type != "alert"` (e.g., stats, flow) are skipped entirely.

---

## Entities (unchanged)

### DetectionResult *(F03, tightened in F10)*

Output of `observe()`. Fields relevant to F11:

| Field | Value for SuricataDefence |
|-------|--------------------------|
| `alerted` | `True` if ≥1 alert found, else `False` |
| `rule_ids` | List of `str(signature_id)` for all alerts found |
| `anomaly_score` | Always `0.0` |
| `coverage` | `"covered"` / `"uncovered"` / `"unknown"` |

### Action *(F03)*

Input to `observe()`. SuricataDefence does not use any Action fields directly — it reads
all new eve.json lines since the last cursor position, regardless of action category or
parameters. The Action is accepted to satisfy the Defence interface contract.

---

## Relationships

```
Defence (abstract, F10)
  └── SuricataDefence       ← this feature
        │
        ├── reads ──────────► eve.json (file on aatf-eve volume, F05)
        │                      (JSONL: one dict per line)
        │
        └── returns ────────► DetectionResult (F03)
                                alerted, rule_ids, anomaly_score=0.0, coverage
```

---

## File truncation state diagram

```
_cursor = 50                     (normal)
        │
        ▼
os.path.getsize(path) = 30       (file rotated — size < cursor)
        │
        ▼
_cursor = 0                      (reset — read whole new file)
        │
        ▼
read lines 0..EOF, advance _cursor
```
