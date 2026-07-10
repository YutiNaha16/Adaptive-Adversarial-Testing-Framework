# Data Model: Episode Loop (F16)

**Date**: 2026-07-10
**Feature**: 016-e4-episode-loop

## New Entities

### StepRecord

Immutable record of a single step within an episode.

| Field         | Type   | Constraints       | Description                                     |
|---------------|--------|-------------------|-------------------------------------------------|
| action_id     | str    | non-empty         | The action_id from REGISTRY that was executed   |
| detected      | bool   | —                 | Whether the defence alerted on this action      |
| stage_progress| bool   | —                 | Whether the action unlocked new reachable actions|
| reward        | float  | one of {-1.0, +1.0, -0.1} | Scalar reward from compute_reward()   |

Implementation: `@dataclass(frozen=True)` in `src/aatf/episode.py`.

### EpisodeResult

Immutable summary of a completed episode.

| Field          | Type              | Constraints    | Description                                           |
|----------------|-------------------|----------------|-------------------------------------------------------|
| episode_state  | EpisodeState      | mutated in-place | Final episode state (caller's reference, mutated)   |
| steps          | list[StepRecord]  | ordered        | One StepRecord per step, in execution order           |
| total_reward   | float             | —              | Arithmetic sum of all step rewards; 0.0 if no steps  |
| completed      | bool              | —              | True if all available actions exhausted; False if step limit hit |

Implementation: `@dataclass(frozen=True)` in `src/aatf/episode.py`.

## Reused Entities

### EpisodeState (from F13 — `src/aatf/context_vector.py`)

Mutable. Passed in by the caller; mutated in-place during the episode. Returned inside `EpisodeResult.episode_state` (same object reference). Fields relevant to F16:

- `completed_actions: set[str]` — used to compute `available` each step
- `step: int` — used for the step-limit check; equals `len(steps)` after episode

### Action (from F03 — `src/aatf/contracts.py`)

Pydantic frozen model. Constructed by F16 each step from `ActionDefinition` before calling `Defence.observe()`. Not persisted by F16.

### DetectionResult (from F03 — `src/aatf/contracts.py`)

Pydantic frozen model returned by `Defence.observe()`. F16 consumes only `alerted: bool`; `rule_ids`, `anomaly_score`, `coverage` are ignored at this layer.

### FeedbackResult (from F15 — `src/aatf/feedback.py`)

Frozen dataclass returned by `collect_feedback()`. F16 consumes `detected: bool` and `stage_progress: bool` to populate `StepRecord` and call `compute_reward()`.

## Relationships

```
run_episode(episode_state, action_selector, execute_fn, defence, *, attack_graph, max_steps)
    │
    ├── per step:
    │     ├── REGISTRY.get_action(action_id)  → ActionDefinition
    │     ├── Action(action_id, category, parameters, timestamp)  [constructed inline]
    │     ├── defence.observe(action)          → DetectionResult  (alerted: bool used)
    │     ├── collect_feedback(episode_state, action_id, alert_fired, category=...)
    │     │                                    → FeedbackResult   (detected, stage_progress used)
    │     ├── compute_reward(detected, stage_progress)  → float
    │     └── StepRecord(action_id, detected, stage_progress, reward)  [appended to steps]
    │
    └── returns EpisodeResult(episode_state, steps, total_reward, completed)
```

## State Transitions

```
Episode start
    → available = filter(reachable \ completed_actions)
    → if empty  → EpisodeResult(completed=True,  steps=[])
    → if step >= max_steps  → EpisodeResult(completed=False, steps=[])
    [per-step loop]
    → append StepRecord
    → recheck available
    → if empty  → EpisodeResult(completed=True,  steps=[...])
    → if step >= max_steps  → EpisodeResult(completed=False, steps=[...])
Episode end
```

`completed=True` (no available actions) takes priority over `completed=False` (step limit) when both are simultaneously true.
