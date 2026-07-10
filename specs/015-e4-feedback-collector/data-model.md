# Data Model: Feedback Collector (F15)

**Feature**: `015-e4-feedback-collector` | **Date**: 2026-07-10

## New Entity: FeedbackResult

**Module**: `src/aatf/feedback.py`

| Field          | Type  | Description                                                                  |
|----------------|-------|------------------------------------------------------------------------------|
| `detected`     | bool  | True if the action triggered an IDS alert (mirrors `alert_fired` input)      |
| `stage_progress` | bool | True if completing this action unlocked ≥1 new reachable action in the graph |

**Constraints**:
- Immutable (frozen): callers cannot modify fields after creation
- No validation needed: both fields are booleans with no invalid states
- No methods beyond field access

**Consumed by**: `compute_reward(detected, stage_progress)` in F14 (`reward.py`)

---

## Existing Entity: EpisodeState (mutated in-place)

**Defined in**: `src/aatf/context_vector.py` (F13)

| Field                | Type                      | Mutation by collect_feedback                        |
|----------------------|---------------------------|-----------------------------------------------------|
| `alert_history`      | `list[bool]`              | `append(alert_fired)` — grows by 1 per call         |
| `detection_history`  | `dict[str, list[bool]]`   | `setdefault(action_id, []).append(alert_fired)`      |
| `completed_actions`  | `set[str]`                | `add(action_id)` — idempotent, set semantics        |
| `step`               | `int`                     | `+= 1` — unconditional increment                    |
| `fired_categories`   | `set[str]`                | `add(category)` only if `alert_fired and category is not None` |
| `start_time`         | `float`                   | **NOT mutated** — set at episode creation           |

**Mutation order (FR-009)**:
1. `alert_history.append(alert_fired)`
2. `detection_history.setdefault(action_id, []).append(alert_fired)`
3. `completed_actions.add(action_id)`
4. `step += 1`
5. `if alert_fired and category is not None: fired_categories.add(category)`

*Note: before_actions snapshot is taken before step 3. stage_progress computed after step 3.*

---

## Existing Entity: AttackGraph (read-only)

**Defined in**: `src/aatf/attack_graph.py` (F09)

| Method / Field    | Usage in collect_feedback                                              |
|-------------------|------------------------------------------------------------------------|
| `available_actions(completed: set[str]) -> list[str]` | Called twice: before and after `completed_actions.add(action_id)` |

**Default instance**: `ATTACK_GRAPH` — canonical singleton imported from `aatf.attack_graph`

---

## Relationships

```text
collect_feedback(episode_state, action_id, alert_fired, *, attack_graph, category)
        │
        ├── reads  → AttackGraph.available_actions() [before + after mutation]
        ├── mutates → EpisodeState [5 fields]
        └── returns → FeedbackResult(detected, stage_progress)
                              │
                              └── consumed by → compute_reward(detected, stage_progress) [F14]
```
