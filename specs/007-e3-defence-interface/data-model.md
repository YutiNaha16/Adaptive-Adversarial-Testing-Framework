# Data Model: Pluggable Defence Interface (F10)

No new persistent entities. This feature defines an in-memory abstraction layer over the
existing F03 data contracts.

---

## Entities (modified)

### DetectionResult *(modified — F03)*

**File**: `src/aatf/contracts.py`

Existing fields (unchanged):

| Field | Type | Constraint |
|-------|------|------------|
| `alerted` | `bool` | — |
| `rule_ids` | `list[str]` | — |
| `anomaly_score` | `float` | 0.0 ≤ score ≤ 1.0 |
| `coverage` | `Literal["covered","uncovered","unknown"]` | — |

**New validator added**:
- `rule_ids` MUST be empty when `alerted = False`. Populated `rule_ids` with `alerted = False`
  raises `ValidationError`.

---

## Entities (new)

### Defence *(abstract class)*

**File**: `src/aatf/defence.py`

| Attribute | Kind | Description |
|-----------|------|-------------|
| `observe` | abstract method | `(action: Action) -> DetectionResult` |

Rules:
- Cannot be instantiated directly (abstract).
- Any subclass that does not implement `observe` raises `TypeError` at definition time.
- `observe` MUST NOT modify the action or any shared state.

---

### DefenceError *(exception)*

**File**: `src/aatf/defence.py`

Inherits from `Exception`. Raised by concrete Defence implementations on internal failure.

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Human-readable failure description |
| `cause` | `Exception \| None` | Underlying exception, if any |

---

### NullDefence *(concrete stub)*

**File**: `src/aatf/defence.py`

Implements `Defence`. Always returns "nothing detected":

| Field | Fixed value |
|-------|-------------|
| `alerted` | `False` |
| `rule_ids` | `[]` |
| `anomaly_score` | `0.0` |
| `coverage` | `"unknown"` |

Has no constructor parameters and no mutable state. Safe for concurrent use.

---

## Relationships

```
Defence (abstract)
  └── NullDefence          # shipped with interface, test double
  └── SuricataDefence      # F11 — NOT in this feature
  └── HostEventDefence     # F12 — NOT in this feature
  └── MLAnomalyDefence     # F27 (Phase 2) — NOT in this feature

Action ──────────────────► Defence.observe() ──► DetectionResult
         (F03 contract)                           (F03 contract, tightened here)
```

All arrows cross feature boundaries via the shared contracts module — no feature imports
another feature's concrete class.
