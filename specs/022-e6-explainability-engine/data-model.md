# Data Model: Explainability Engine (F23)

**Phase**: 1 — Design  
**Date**: 2026-07-11  
**Feature**: 022-e6-explainability-engine

## Entities

### ActionExplanation (new — owned by this feature)

Immutable result record for one evaded action. Produced by `explain_evasions`;
consumed by F24 (report generator).

```python
@dataclass(frozen=True)
class ActionExplanation:
    action_id: str           # e.g. "ssh_brute_force_slow"
    suricata_category: str   # e.g. "ET BRUTE_FORCE" (from ActionRegistry)
    description: str         # human-readable action description (from ActionRegistry)
    evasion_count: int       # steps where detected=False for this action_id
    total_count: int         # all steps for this action_id across all episodes
    evasion_rate: float      # evasion_count / total_count  (∈ (0.0, 1.0])
    remediation: str         # canned fix hint from REMEDIATION_TABLE
    false_positive_risk: str # risk note from REMEDIATION_TABLE
```

**Invariants**:
- `evasion_count >= 1` (zero-evasion entries are filtered before construction)
- `total_count >= evasion_count`
- `evasion_rate == evasion_count / total_count`
- All string fields are non-empty

**Immutability**: `frozen=True` — assignment raises `dataclasses.FrozenInstanceError`.

---

### REMEDIATION_TABLE (module-level constant — not a class)

```python
REMEDIATION_TABLE: dict[str, tuple[str, str]] = {
    "ET SCAN":        (remediation_str, false_positive_risk_str),
    "ET BRUTE_FORCE": (...),
    "ET EXPLOIT":     (...),
    "ET DNS":         (...),
    "ET POLICY":      (...),
    "ET TROJAN":      (...),
    "ET WEB_CLIENT":  (...),
    "ET WEB_SERVER":  (...),
}

_FALLBACK: tuple[str, str] = (generic_remediation, generic_fpr)
```

- Keyed by `suricata_category` string (exact match).
- Lookup: `REMEDIATION_TABLE.get(category, _FALLBACK)`.
- Never raises — unknown categories silently get `_FALLBACK`.

---

## Consumed entities (read-only, not defined here)

### EpisodeRecord (from `aatf.metrics`, F20)

```python
@dataclass(frozen=True)
class EpisodeRecord:
    attacker_class: str
    seed: int
    steps: list[StepRecord]   # ← iterated by explain_evasions
    total_reward: float
    completed: bool
    episode_index: int
```

### StepRecord (from `aatf.episode`, F16)

```python
@dataclass(frozen=True)
class StepRecord:
    action_id: str    # ← tally key
    detected: bool    # ← evasion counter (not detected → evasion)
    stage_progress: ...
    reward: float
```

### ActionDefinition (from `aatf.action_library`, F10)

```python
@dataclass(frozen=True)
class ActionDefinition:
    action_id: str
    category: str
    description: str           # → ActionExplanation.description
    default_parameters: dict
    suricata_category: str     # → ActionExplanation.suricata_category + table key
```

---

## Data flow

```
list[EpisodeRecord]
    │
    ▼ walk .steps per record
dict[action_id → [evasion_count, total_count]]
    │
    ▼ filter evasion_count > 0
    │  + registry.get_action(action_id) → ActionDefinition
    │  + REMEDIATION_TABLE.get(suricata_category, _FALLBACK)
    ▼
list[ActionExplanation]  (unsorted)
    │
    ▼ sorted(key=(-evasion_rate, action_id))
list[ActionExplanation]  (ranked)
```

---

## Module layout

```text
src/aatf/explainability.py   # ~55 LOC
    _FALLBACK                # module-level tuple
    REMEDIATION_TABLE        # module-level dict
    ActionExplanation        # frozen dataclass
    explain_evasions()       # pure function

tests/test_explainability.py  # ~150 LOC, 12 contracts C-001..C-012
```

No new files. No new pip dependencies.
