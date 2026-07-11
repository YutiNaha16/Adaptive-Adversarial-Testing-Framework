# Research: Ground-Truth Validation Harness (F22)

**Phase**: 0 — Pre-design research  
**Date**: 2026-07-11  
**Feature**: 024-e6-ground-truth-validation

## Summary

No external research required. All design decisions resolved from the existing codebase
and spec. The algorithm is trivially simple: set intersection between `suricata_category`
values of reported explanations and categories derived from disabled SIDs. No new deps.

---

## Decision 1: Algorithm for matching explanations to disabled SIDs

**Decision**: Derive `disabled_categories` as a set from `disabled_sids` via
`SURICATA_SID_CATEGORIES`, then classify each explanation by whether its
`suricata_category` is in `disabled_categories`.

```python
disabled_categories = {SURICATA_SID_CATEGORIES[s] for s in disabled_sids
                       if s in SURICATA_SID_CATEGORIES}
tp = sum(1 for e in explanations if e.suricata_category in disabled_categories)
fp = len(explanations) - tp
```

**Rationale**: Simple O(n) algorithm. Precomputing `disabled_categories` avoids
redundant lookups. Category-level matching is the right granularity — the harness
validates category coverage, not individual SID-to-action mapping.

**Alternatives considered**:
- SID-to-action_id direct matching: too fine-grained; the report works at category
  level (suricata_category), not SID level. Rejected.
- Fuzzy/regex matching on category strings: unnecessary complexity for exact-match
  string comparison. Rejected.

---

## Decision 2: Placement of SURICATA_SID_CATEGORIES

**Decision**: Module-level constant in `ground_truth.py`, not a separate constants
file.

**Rationale**: The constant is small (~10 entries for Phase 1 coverage) and only
consumed by this module. Splitting to a separate file adds indirection with no benefit
at this scale.

**Alternatives considered**:
- `src/aatf/constants.py`: would force another import chain; not needed until multiple
  modules share constants. Rejected.
- External YAML: adds I/O, breaks the "pure function" guarantee. Rejected.

---

## Decision 3: meets_gate implementation

**Decision**: Python `@property` on the frozen dataclass, not a module-level function.

```python
@property
def meets_gate(self) -> bool:
    return self.blind_spot_precision >= 0.8
```

**Rationale**: Attaches the gate logic to the result object where callers expect it
(result.meets_gate). Threshold is a constitution constant (Principle VII) so hardcoding
0.8 here is correct — it's not a tunable.

**Alternatives considered**:
- Free function `gate_passes(result)`: forces callers to import an extra name. Rejected.
- Threshold as a module-level constant `GATE_THRESHOLD = 0.8`: adds flexibility that
  isn't needed — the constitution fixes this at 0.8. Rejected.

---

## Decision 4: Precision when total_reported == 0

**Decision**: Return `0.0` (not NaN, not raise).

**Rationale**: An empty blind-spot list means "nothing to validate"; precision of 0.0 is
semantically correct (zero true positives / zero denominator → no evidence of coverage).
Consistent with `detection_rate` and `robustness_score` behaviour on empty inputs.

---

## Decision 5: Unknown SIDs in disabled_sids

**Decision**: Silently ignore SIDs not present in `SURICATA_SID_CATEGORIES`.

**Rationale**: The caller is the lab operator who disabled SIDs — they may disable SIDs
outside Phase 1 scope. The harness only validates Phase 1 categories. Raising an error
would be too strict and break legitimate usage. Documented in spec (A3).

---

## Integration contracts confirmed

| Symbol | Location | Used for |
|---|---|---|
| `ActionExplanation` | `aatf.explainability` | input list type; only `.suricata_category` accessed |

---

## Representative SID table (Phase 1)

| SID | Category | Source |
|---|---|---|
| "2001219" | ET SCAN | ET Open network scan detection |
| "2008581" | ET SCAN | ET Open horizontal port scan |
| "2002087" | ET BRUTE_FORCE | ET Open SSH brute force |
| "2019284" | ET BRUTE_FORCE | ET Open HTTP brute force |
| "2012648" | ET EXPLOIT | ET Open shellcode exploit attempt |
| "2016778" | ET DNS | ET Open DNS zone transfer |
| "2013028" | ET POLICY | ET Open outbound data transfer policy |
| "2014726" | ET TROJAN | ET Open generic trojan callback |
| "2010935" | ET WEB_CLIENT | ET Open XSS attack attempt |
| "2009714" | ET WEB_SERVER | ET Open web server directory traversal |
