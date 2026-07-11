# Research: Explainability Engine (F23)

**Phase**: 0 — Pre-design research  
**Date**: 2026-07-11  
**Feature**: 022-e6-explainability-engine

## Summary

No external research required. All design questions resolved from existing codebase
(F10, F16, F20) and the spec. Findings below establish the integration contracts and
confirm no new dependencies are needed.

---

## Decision 1: Aggregation over steps vs. over episodes

**Decision**: Aggregate at step level across all episodes for a flat per-action_id tally.

**Rationale**: `StepRecord` (in `aatf.episode`) is the atomic unit that carries `action_id`
and `detected`. Aggregating at episode level would lose multi-step frequency information
within an episode. The spec requires `total_count = all steps for that action_id` — this
maps directly to iterating `record.steps` for every `record` in `records`.

**Alternatives considered**:
- Per-episode evasion flags: loses intra-episode granularity; rejected.
- Grouping by episode then averaging: adds complexity without spec requirement; rejected.

---

## Decision 2: Data types for tally accumulator

**Decision**: Use `dict[str, list[int]]` → `{action_id: [evasion_count, total_count]}`.

**Rationale**: Two counters per action_id suffice. `defaultdict(lambda: [0, 0])` keeps the
update one-liner: `counts[action_id][1] += 1; if not step.detected: counts[action_id][0] += 1`.
Frozen EpisodeRecord/StepRecord means no mutation risk.

**Alternatives considered**:
- Separate dicts for evaded/total: more lines, same semantics; rejected.
- Counter + set: insufficient (need total count too); rejected.

---

## Decision 3: REMEDIATION_TABLE data source and coverage

**Decision**: Module-level constant covering all 8 `suricata_category` values found in F10
`REGISTRY`, plus a generic fallback. Categories confirmed by reading `action_library.py`:

| suricata_category | Present in REGISTRY |
|---|---|
| ET SCAN | ✅ |
| ET BRUTE_FORCE | ✅ |
| ET EXPLOIT | ✅ |
| ET DNS | ✅ |
| ET POLICY | ✅ |
| ET TROJAN | ✅ |
| ET WEB_CLIENT | ✅ |
| ET WEB_SERVER | ✅ |

Generic fallback is used for any category not in the table (A1 in spec).

**Alternatives considered**:
- YAML file for table: adds I/O, violates FR-010 (pure); rejected.
- Caller-configurable table via argument: Phase 2 scope (A4); rejected for Phase 1.

---

## Decision 4: Sort stability and tie-breaking

**Decision**: `sorted(result, key=lambda x: (-x.evasion_rate, x.action_id))`.

**Rationale**: Python's `sorted` is stable and this compound key satisfies FR-007 exactly:
primary sort = evasion_rate descending (negate for ascending `sorted`); tie-break =
action_id ascending (lexicographic). Deterministic for identical inputs.

**Alternatives considered**:
- Sort only by evasion_rate, rely on insertion order for ties: non-deterministic; rejected.
- Sort by evasion_count instead of evasion_rate: ignores relative frequency; rejected.

---

## Decision 5: KeyError propagation for missing action_id

**Decision**: Let `registry.get_action(action_id)` propagate `KeyError` naturally (A2).

**Rationale**: The spec explicitly states "caller is responsible for supplying a registry
that matches the experiment's action set." Adding a try/catch would silently swallow data
errors. The raw `KeyError` from `ActionRegistry.get_action` carries the missing key in its
message, which is the most informative behaviour.

**Alternatives considered**:
- Catch and return None: loses the action silently; rejected.
- Wrap in a custom exception: unnecessary indirection for Phase 1; rejected.

---

## Integration contracts confirmed

| Symbol | Location | Fields used |
|---|---|---|
| `EpisodeRecord` | `aatf.metrics` | `.steps: list[StepRecord]` |
| `StepRecord` | `aatf.episode` | `.action_id: str`, `.detected: bool` |
| `ActionRegistry` | `aatf.action_library` | `.get_action(action_id) -> ActionDefinition` |
| `ActionDefinition` | `aatf.action_library` | `.suricata_category: str`, `.description: str` |

All modules are on `main`. No new pip dependencies required.

---

## Test ground truths

| Contract | Setup | Expected |
|---|---|---|
| C-004 | A: 3/4 evaded, B: 1/4 evaded | A before B |
| C-005 | Same evasion_rate, action_id "b" vs "a" | "a" before "b" |
| C-006 | action_id="scan_tcp", all detected | absent from result |
| C-007 | records=[] | result=[] |
| C-008 | all steps detected across 2 records | result=[] |
| C-010 | known category "ET SCAN" → tuple from table | len > 0 for both |
| C-011 | unknown category "ET CUSTOM" | generic fallback non-empty |
| C-012 | 3 evaded / 4 total | same strings for both actions |

Baseline: 257 passed, 4 skipped, 6 failed (pre-existing). Target: ≥269 (+12 new tests).
