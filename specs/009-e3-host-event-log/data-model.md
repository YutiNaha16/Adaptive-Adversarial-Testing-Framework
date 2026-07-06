# Data Model: Host Event Log Signal (F12)

No new persistent entities. This feature adds one concrete class behind the Defence
interface and reuses the existing F03 data contracts as input/output.

---

## Entities (new)

### HostLogDefence *(concrete Defence implementation)*

**File**: `src/aatf/host_log_defence.py`

| Attribute    | Kind     | Type              | Description |
|--------------|----------|-------------------|-------------|
| `_log_path`  | instance | `pathlib.Path`    | Path to the host log file |
| `_patterns`  | instance | `list[str]`       | Keyword strings to match against each log line |
| `_cursor`    | instance | `int`             | Byte offset of last read position (0 = start of file) |
| `observe`    | method   | `(Action) → DetectionResult` | Read new lines since `_cursor`, match patterns, return result |

**State transitions**:
```
Initial state: _cursor = 0
After each observe() call: _cursor = new EOF position
On file truncation detected: _cursor reset to 0, re-read from start
```

**Construction**: `HostLogDefence(log_path: str | pathlib.Path, patterns: list[str])`

**Pattern matching rule**: For each decoded log line, for each pattern in `_patterns`,
if `pattern in line` then pattern is appended to the match list. A pattern may appear
multiple times if it matches multiple lines.

---

## Entities (unchanged)

### DetectionResult *(F03, tightened in F10)*

Output of `observe()`. Fields relevant to F12:

| Field          | Value for HostLogDefence |
|----------------|--------------------------|
| `alerted`      | `True` if ≥1 pattern matched a new line, else `False` |
| `rule_ids`     | List of matched pattern strings (one entry per match, not deduplicated) |
| `anomaly_score`| Always `0.0` |
| `coverage`     | `"covered"` / `"uncovered"` / `"unknown"` |

### Action *(F03)*

Input to `observe()`. HostLogDefence does not use any Action fields directly — it reads
all new log lines since the last cursor position, regardless of action category.

---

## Relationships

```
Defence (abstract, F10)
  └── HostLogDefence       ← this feature
        │
        ├── reads ─────────► host log file (plaintext, one event per line)
        │                     e.g. /var/log/auth.log on aatf-defender
        │
        ├── matches against► _patterns: list[str]  (substring search)
        │
        └── returns ───────► DetectionResult (F03)
                               alerted, rule_ids (matched patterns),
                               anomaly_score=0.0, coverage
```

---

## File truncation state diagram

```
_cursor = 200                    (normal)
        │
        ▼
os.path.getsize(path) = 50       (file rotated — size < cursor)
        │
        ▼
_cursor = 0                      (reset — read whole new file)
        │
        ▼
read lines 0..EOF, match patterns, advance _cursor
```

---

## Comparison with SuricataDefence (F11)

| Aspect | SuricataDefence (F11) | HostLogDefence (F12) |
|--------|----------------------|----------------------|
| Input format | JSONL (eve.json) | Plaintext (one event/line) |
| Match logic | `event_type=="alert"` + `alert.signature_id` | `pattern in line` for each pattern |
| rule_ids content | SID strings (`"2001219"`) | Matched pattern strings (`"sshd"`) |
| Constructor args | `(eve_path)` | `(log_path, patterns)` |
| Cursor semantics | Identical | Identical |
| Coverage states | Identical | Identical |
| anomaly_score | 0.0 always | 0.0 always |
