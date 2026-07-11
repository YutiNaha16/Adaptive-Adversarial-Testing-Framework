# Contracts: Ground-Truth Validation Harness (F22)

**Phase**: 1 — Design  
**Date**: 2026-07-11  
**Feature**: 024-e6-ground-truth-validation  
**Total contracts**: 12 (C-001..C-012)

---

## Shared helpers

```python
from aatf.explainability import ActionExplanation

def _expl(action_id: str, suricata_category: str) -> ActionExplanation:
    return ActionExplanation(
        action_id=action_id,
        suricata_category=suricata_category,
        description="test",
        evasion_count=1,
        total_count=1,
        evasion_rate=1.0,
        remediation="fix it",
        false_positive_risk="low",
    )
```

---

## US1 — Core validation

### C-001: Importability

```
GIVEN  the aatf.ground_truth module
WHEN   `from aatf.ground_truth import validate_blind_spots, ValidationResult, SURICATA_SID_CATEGORIES`
THEN   all three names are importable with no error
```

### C-002: ValidationResult field types

```
GIVEN  a ValidationResult(blind_spot_precision=0.5, true_positives=1, false_positives=1,
                           total_reported=2, disabled_sid_count=1)
WHEN   fields are accessed
THEN   isinstance(r.blind_spot_precision, float) and isinstance(r.true_positives, int) etc.
```

### C-003: ValidationResult immutable

```
GIVEN  a ValidationResult instance r
WHEN   r.blind_spot_precision = 0.9 is attempted
THEN   FrozenInstanceError (or AttributeError) is raised
```

### C-007: Both explanations confirmed → precision=1.0

```
GIVEN  explanations = [_expl("a", "ET SCAN"), _expl("b", "ET BRUTE_FORCE")]
       disabled_sids = {"2001219", "2002087"}  # one SID per category
WHEN   validate_blind_spots(explanations, disabled_sids) is called
THEN   result.true_positives == 2
       result.false_positives == 0
       result.blind_spot_precision == pytest.approx(1.0)
       result.total_reported == 2
       result.disabled_sid_count == 2
```

### C-008: One confirmed, one not → precision=0.5

```
GIVEN  explanations = [_expl("a", "ET SCAN"), _expl("b", "ET EXPLOIT")]
       disabled_sids = {"2001219"}   # only ET SCAN SID
WHEN   validate_blind_spots(explanations, disabled_sids)
THEN   result.true_positives == 1
       result.false_positives == 1
       result.blind_spot_precision == pytest.approx(0.5)
```

### C-009: Empty explanations → no error, precision=0.0

```
GIVEN  explanations = []
       disabled_sids = {"2001219"}
WHEN   validate_blind_spots([], disabled_sids)
THEN   no exception raised
       result.blind_spot_precision == 0.0
       result.true_positives == 0
       result.false_positives == 0
       result.total_reported == 0
       result.disabled_sid_count == 1
```

### C-010: Empty disabled_sids → precision=0.0, all fp

```
GIVEN  explanations = [_expl("a", "ET SCAN")]
       disabled_sids = set()
WHEN   validate_blind_spots(explanations, set())
THEN   result.blind_spot_precision == 0.0
       result.true_positives == 0
       result.false_positives == 1
       result.disabled_sid_count == 0
```

### C-011: Unknown SID → ignored (no match)

```
GIVEN  explanations = [_expl("a", "ET SCAN")]
       disabled_sids = {"9999999"}   # not in SURICATA_SID_CATEGORIES
WHEN   validate_blind_spots(explanations, disabled_sids)
THEN   no exception raised
       result.true_positives == 0
       result.false_positives == 1
       result.blind_spot_precision == 0.0
```

---

## US2 — SID-to-category lookup

### C-012: SURICATA_SID_CATEGORIES covers all 8 Phase 1 categories

```
GIVEN  SURICATA_SID_CATEGORIES constant
WHEN   set of all values is computed
THEN   {"ET SCAN", "ET BRUTE_FORCE", "ET EXPLOIT", "ET DNS",
        "ET POLICY", "ET TROJAN", "ET WEB_CLIENT", "ET WEB_SERVER"} ⊆ values
```

---

## US3 — Gate assessment

### C-004: meets_gate True when precision >= 0.8

```
GIVEN  ValidationResult(blind_spot_precision=0.85, ...)
WHEN   result.meets_gate is accessed
THEN   True
```

### C-005: meets_gate False when precision < 0.8

```
GIVEN  ValidationResult(blind_spot_precision=0.75, ...)
WHEN   result.meets_gate is accessed
THEN   False
```

### C-006: meets_gate True when precision == 0.8 exactly

```
GIVEN  ValidationResult(blind_spot_precision=0.8, ...)
WHEN   result.meets_gate is accessed
THEN   True  (boundary inclusive)
```

---

## Contract-to-story mapping

| Contract | Story | FR | Description |
|---|---|---|---|
| C-001 | US1 | FR-009 | Importability |
| C-002 | US1 | FR-002 | Field types |
| C-003 | US1 | FR-002 | Immutability |
| C-004 | US3 | FR-008 | meets_gate True (high precision) |
| C-005 | US3 | FR-008 | meets_gate False (low precision) |
| C-006 | US3 | FR-008 | meets_gate True at boundary |
| C-007 | US1 | FR-003, FR-004 | 2/2 confirmed |
| C-008 | US1 | FR-003, FR-004 | 1/2 confirmed |
| C-009 | US1 | FR-005 | Empty explanations |
| C-010 | US1 | FR-006 | Empty disabled_sids |
| C-011 | US1 | FR-007 | Unknown SID ignored |
| C-012 | US2 | FR-007 | All 8 categories covered |
