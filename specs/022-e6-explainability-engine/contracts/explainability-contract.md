# Contracts: Explainability Engine (F23)

**Phase**: 1 — Design  
**Date**: 2026-07-11  
**Feature**: 022-e6-explainability-engine  
**Total contracts**: 12 (C-001..C-012)

Contracts map directly to test cases in `tests/test_explainability.py`. Each contract
is independently verifiable with hand-crafted fixtures.

---

## Helpers (shared across contracts)

```python
# minimal StepRecord constructor
def _step(action_id: str, detected: bool) -> StepRecord:
    return StepRecord(action_id=action_id, detected=detected,
                      stage_progress=0, reward=0.0)

# minimal EpisodeRecord constructor
def _ep(*steps: StepRecord) -> EpisodeRecord:
    return EpisodeRecord(attacker_class="test", seed=0, steps=list(steps),
                         total_reward=0.0, completed=False, episode_index=0)
```

A stub `ActionRegistry` is built by constructing `ActionDefinition` objects directly and
wrapping them in a minimal registry. The real `REGISTRY` constant from `action_library.py`
is used for integration-style contracts (C-009, C-010, C-011) where real action metadata
is needed.

---

## US1 — ActionExplanation container

### C-001: Construction and field access

**Story**: US1  
**FR**: FR-001  

```
GIVEN  ActionExplanation constructed with:
         action_id="ssh_brute_force", suricata_category="ET BRUTE_FORCE",
         description="SSH brute-force probe", evasion_count=3, total_count=4,
         evasion_rate=0.75, remediation="tune thresholds",
         false_positive_risk="medium"
WHEN   each field is accessed
THEN   it equals the value provided at construction
```

**Test**: Assert all 8 fields equal their constructor values.

---

### C-002: Immutability

**Story**: US1  
**FR**: FR-001  

```
GIVEN  an ActionExplanation instance
WHEN   any field assignment is attempted (e.g. obj.evasion_count = 99)
THEN   dataclasses.FrozenInstanceError is raised
```

**Test**: `pytest.raises(FrozenInstanceError, ...)` on field assignment.

---

### C-003: Importability

**Story**: US1  
**FR**: FR-009  

```
GIVEN  the aatf.explainability module
WHEN   `from aatf.explainability import ActionExplanation, explain_evasions` is executed
THEN   both names are available with no ImportError
```

**Test**: Import statement at module level of the test file; no assertion body needed.

---

## US2 — Evasion analysis

### C-004: Ranking by evasion_rate descending

**Story**: US2  
**FR**: FR-007, FR-003  

```
GIVEN  records = [
         _ep(_step("scan_tcp", False), _step("scan_tcp", False),
              _step("scan_tcp", False), _step("scan_tcp", True)),   # 3/4 evaded = 0.75
         _ep(_step("dns_recon", False), _step("dns_recon", True),
              _step("dns_recon", True), _step("dns_recon", True)),  # 1/4 evaded = 0.25
       ]
       registry = stub containing scan_tcp (ET SCAN) and dns_recon (ET DNS)
WHEN   explain_evasions(records, registry) is called
THEN   result[0].action_id == "scan_tcp"
       result[1].action_id == "dns_recon"
       result[0].evasion_rate == pytest.approx(0.75)
       result[0].evasion_count == 3
       result[0].total_count == 4
```

**Test**: Full structural assertion on the two-element result list.

---

### C-005: Tie-breaking by action_id ascending

**Story**: US2  
**FR**: FR-007  

```
GIVEN  records = [
         _ep(_step("zzz_action", False), _step("zzz_action", True)),  # 0.5 evaded
         _ep(_step("aaa_action", False), _step("aaa_action", True)),  # 0.5 evaded
       ]
       registry = stub containing both actions (same suricata_category)
WHEN   explain_evasions(records, registry) is called
THEN   result[0].action_id == "aaa_action"  # lexicographic tie-break
       result[1].action_id == "zzz_action"
```

**Test**: Assert ordering of first two elements by action_id.

---

### C-006: Fully-detected action excluded

**Story**: US2  
**FR**: FR-006  

```
GIVEN  records = [_ep(_step("scan_tcp", True), _step("scan_tcp", True))]
       (all steps detected — evasion_rate == 0.0)
       registry = stub containing scan_tcp
WHEN   explain_evasions(records, registry) is called
THEN   result == []
```

**Test**: Assert result is empty list.

---

### C-007: Empty records list

**Story**: US2  
**FR**: FR-008  

```
GIVEN  records = []
WHEN   explain_evasions([], registry) is called (registry can be any stub)
THEN   result == []   and no exception is raised
```

**Test**: Assert result == [] with no pytest.raises needed.

---

### C-008: All steps detected across multiple episodes

**Story**: US2  
**FR**: FR-006, FR-008  

```
GIVEN  records = [
         _ep(_step("scan_tcp", True), _step("dns_recon", True)),
         _ep(_step("scan_tcp", True), _step("dns_recon", True)),
       ]
WHEN   explain_evasions(records, registry) is called
THEN   result == []
```

**Test**: Assert result is empty list.

---

### C-009: Registry lookup populates suricata_category and description

**Story**: US2  
**FR**: FR-004  

```
GIVEN  a real action_id from REGISTRY (e.g. "ssh_brute_force_slow")
       records = [_ep(_step("ssh_brute_force_slow", False))]
       registry = the real REGISTRY from aatf.action_library
WHEN   explain_evasions(records, registry) is called
THEN   result[0].suricata_category == REGISTRY.get_action("ssh_brute_force_slow").suricata_category
       result[0].description == REGISTRY.get_action("ssh_brute_force_slow").description
```

**Test**: Use real REGISTRY; assert field values match ActionDefinition.

---

## US3 — Remediation and risk hints

### C-010: Known category gives non-empty remediation strings

**Story**: US3  
**FR**: FR-005  

```
GIVEN  a stub action with suricata_category="ET SCAN" (a known table key)
       records = [_ep(_step("some_scan_action", False))]
WHEN   explain_evasions(records, registry) is called
THEN   len(result[0].remediation) > 0
       len(result[0].false_positive_risk) > 0
```

**Test**: Assert both strings are non-empty for each known category.  
*Run this check for all 8 known suricata_category values in a parametrize loop.*

---

### C-011: Unknown category gives non-empty generic fallback

**Story**: US3  
**FR**: FR-005  

```
GIVEN  a stub action with suricata_category="ET CUSTOM_UNKNOWN" (not in table)
       records = [_ep(_step("custom_action", False))]
WHEN   explain_evasions(records, registry) is called
THEN   result is non-empty list (no KeyError)
       len(result[0].remediation) > 0
       len(result[0].false_positive_risk) > 0
```

**Test**: Assert non-error return with non-empty fallback strings.

---

### C-012: Same category yields identical strings

**Story**: US3  
**FR**: FR-005  

```
GIVEN  two stub actions ("action_a", "action_b") with the same suricata_category
       records = [_ep(_step("action_a", False), _step("action_b", False))]
WHEN   explain_evasions(records, registry) is called
THEN   result[0].remediation == result[1].remediation
       result[0].false_positive_risk == result[1].false_positive_risk
```

**Test**: Assert string equality between the two explanations' hint fields.

---

## Contract-to-story mapping

| Contract | Story | FR | Description |
|---|---|---|---|
| C-001 | US1 | FR-001 | ActionExplanation field access |
| C-002 | US1 | FR-001 | Immutability |
| C-003 | US1 | FR-009 | Importability |
| C-004 | US2 | FR-003, FR-007 | Ranking by evasion_rate |
| C-005 | US2 | FR-007 | Tie-break by action_id |
| C-006 | US2 | FR-006 | evasion_rate=0 excluded |
| C-007 | US2 | FR-008 | Empty records → empty list |
| C-008 | US2 | FR-006, FR-008 | All-detected → empty list |
| C-009 | US2 | FR-004 | Registry lookup |
| C-010 | US3 | FR-005 | Known category strings |
| C-011 | US3 | FR-005 | Fallback strings |
| C-012 | US3 | FR-005 | Same category same strings |
