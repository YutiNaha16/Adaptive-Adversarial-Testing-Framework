# Quickstart: Ground-Truth Validation Harness (F22)

**Date**: 2026-07-11  
**Module**: `aatf.ground_truth`

## Minimal usage

```python
from aatf.ground_truth import validate_blind_spots, SURICATA_SID_CATEGORIES
from aatf.explainability import explain_evasions, ActionExplanation
from aatf.action_library import REGISTRY

# After running an experiment with known disabled SIDs
explanations = explain_evasions(records, REGISTRY)

# SIDs that were deliberately disabled in Suricata config before the run
disabled_sids = {"2001219", "2002087"}  # ET SCAN + ET BRUTE_FORCE

result = validate_blind_spots(explanations, disabled_sids)

print(f"Blind-Spot Precision: {result.blind_spot_precision:.2%}")
print(f"True positives:  {result.true_positives}")
print(f"False positives: {result.false_positives}")
print(f"Gate passes:     {result.meets_gate}")  # True if >= 0.8
```

---

## Checking the Phase 1 gate

```python
if result.meets_gate:
    print("Phase 1 gate PASSED — Blind-Spot Precision >= 0.8")
else:
    print(f"Phase 1 gate FAILED — Precision {result.blind_spot_precision:.2%} < 80%")
```

---

## Using SURICATA_SID_CATEGORIES

```python
from aatf.ground_truth import SURICATA_SID_CATEGORIES

# Look up what category a SID belongs to
sid = "2001219"
if sid in SURICATA_SID_CATEGORIES:
    print(f"SID {sid} → {SURICATA_SID_CATEGORIES[sid]}")
# Output: SID 2001219 → ET SCAN

# List all covered categories
all_categories = set(SURICATA_SID_CATEGORIES.values())
print(all_categories)
# {'ET SCAN', 'ET BRUTE_FORCE', 'ET EXPLOIT', 'ET DNS',
#  'ET POLICY', 'ET TROJAN', 'ET WEB_CLIENT', 'ET WEB_SERVER'}
```

---

## Edge cases

```python
# Empty explanations — no error, precision = 0.0
r = validate_blind_spots([], {"2001219"})
assert r.blind_spot_precision == 0.0
assert r.total_reported == 0

# Empty disabled_sids — no matches possible
r = validate_blind_spots(explanations, set())
assert r.blind_spot_precision == 0.0
assert r.false_positives == len(explanations)

# Unknown SID — silently ignored
r = validate_blind_spots(explanations, {"9999999"})
assert r.true_positives == 0  # unknown SID matches nothing
```

---

## Running the tests

```bash
cd /home/yuti/Adaptive-Adversarial-Testing-Framework
source .venv/bin/activate
cd src && pytest ../tests/test_ground_truth.py -v
```

Target: 12 new tests (C-001..C-012) all green, overall suite ≥298 passed.
