# Data Model: Ground-Truth Validation Harness (F22)

**Phase**: 1 — Design  
**Date**: 2026-07-11  
**Feature**: 024-e6-ground-truth-validation

## Entities

### ValidationResult

Immutable result of a `validate_blind_spots` call.

```python
@dataclass(frozen=True)
class ValidationResult:
    blind_spot_precision: float   # true_positives / total_reported; 0.0 when total_reported == 0
    true_positives: int            # explanations whose suricata_category in disabled_categories
    false_positives: int           # explanations whose suricata_category NOT in disabled_categories
    total_reported: int            # len(explanations) — invariant: tp + fp == total_reported
    disabled_sid_count: int        # len(disabled_sids)

    @property
    def meets_gate(self) -> bool:
        return self.blind_spot_precision >= 0.8
```

**Invariants**:
- `0.0 <= blind_spot_precision <= 1.0`
- `true_positives + false_positives == total_reported`
- `blind_spot_precision == true_positives / total_reported` (or 0.0 when total_reported == 0)
- Immutable: all fields set at construction, no mutation permitted

---

### SURICATA_SID_CATEGORIES

Module-level constant in `ground_truth.py`.

```python
SURICATA_SID_CATEGORIES: dict[str, str] = {
    "2001219": "ET SCAN",
    "2008581": "ET SCAN",
    "2002087": "ET BRUTE_FORCE",
    "2019284": "ET BRUTE_FORCE",
    "2012648": "ET EXPLOIT",
    "2016778": "ET DNS",
    "2013028": "ET POLICY",
    "2014726": "ET TROJAN",
    "2010935": "ET WEB_CLIENT",
    "2009714": "ET WEB_SERVER",
}
```

**Invariants**:
- Every value is one of the 8 Phase 1 `suricata_category` strings
- All 8 categories represented as at least one value
- Keys are SID strings (numeric strings, not ints)

---

### ActionExplanation (consumed, from F23)

Only field accessed: `.suricata_category: str`

---

## Files

```text
src/aatf/
└── ground_truth.py    # ~55 LOC (NEW)

tests/
└── test_ground_truth.py    # ~150 LOC, 12 contracts C-001..C-012 (NEW)
```

---

## Data flow

```
list[ActionExplanation]  +  set[str] disabled_sids
          │
          ▼ validate_blind_spots()
  disabled_categories = {SURICATA_SID_CATEGORIES[s] for s in disabled_sids
                          if s in SURICATA_SID_CATEGORIES}
          │
          ▼ classify each explanation
  tp = count(e for e in explanations if e.suricata_category in disabled_categories)
  fp = total_reported - tp
  precision = tp / total_reported  (or 0.0)
          │
          ▼
  ValidationResult(blind_spot_precision, true_positives, false_positives,
                   total_reported, disabled_sid_count)
```

---

## Module layout

```python
# src/aatf/ground_truth.py
from __future__ import annotations
from dataclasses import dataclass
from aatf.explainability import ActionExplanation

SURICATA_SID_CATEGORIES: dict[str, str] = { ... }

@dataclass(frozen=True)
class ValidationResult:
    blind_spot_precision: float
    true_positives: int
    false_positives: int
    total_reported: int
    disabled_sid_count: int

    @property
    def meets_gate(self) -> bool:
        return self.blind_spot_precision >= 0.8

def validate_blind_spots(
    explanations: list[ActionExplanation],
    disabled_sids: set[str],
) -> ValidationResult:
    ...
```
