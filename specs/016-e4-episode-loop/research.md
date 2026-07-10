# Research: Episode Loop (F16)

**Date**: 2026-07-10
**Feature**: 016-e4-episode-loop

## Decision 1: Defence Interface — real API differs from spec assumption

**Decision**: Use `Defence.observe(action: Action) -> DetectionResult`, NOT `defence.detect(action_id: str) -> (bool, str|None)`.

The spec (line 122) assumed `detect(action_id: str) -> tuple[bool, str | None]`. Inspection of `src/aatf/defence.py` reveals the actual abstract method is:

```python
class Defence(ABC):
    @abstractmethod
    def observe(self, action: Action) -> DetectionResult: ...
```

`DetectionResult` (from `src/aatf/contracts.py`) has `alerted: bool`, `rule_ids: list[str]`, `anomaly_score: float`, `coverage: Literal["covered", "uncovered", "unknown"]`. There is no `category` field — the episode loop must source the IDS category from the `ActionDefinition` in `REGISTRY`.

**Rationale**: The real interface is richer (Principle III: Pluggable Defence Interface). `observe()` accepts a full `Action` so the defence can inspect all action metadata. The spec assumption was a simplified placeholder.

**Impact on F16**:
- Before calling `observe()`, F16 must construct an `Action` object using `REGISTRY.get_action(action_id)`.
- `alert_fired = detection.alerted`
- `category = action_def.suricata_category if alert_fired else None` — sourced from `ActionDefinition`, not from `DetectionResult`

**Alternatives considered**: Adding a `detect()` shim method to Defence — rejected: would add coupling and redundancy; the real interface is stable.

---

## Decision 2: Action construction for observe() call

**Decision**: Build `Action` from `REGISTRY.get_action(action_id)` immediately before calling `defence.observe()`.

```python
action_def = REGISTRY.get_action(action_id)
action = Action(
    action_id=action_id,
    category=action_def.category,
    parameters=action_def.default_parameters,
    timestamp=datetime.now(timezone.utc),
)
detection = defence.observe(action)
```

`Action` (Pydantic frozen model) requires: `action_id: str`, `category: str`, `parameters: dict[str, Any]`, `timestamp: datetime`. All fields are available from `ActionDefinition`. `datetime.now(timezone.utc)` is acceptable — F16's only deterministic-non-determinism is the timestamp (per step); the spec excludes it from reproducibility requirements.

**Rationale**: `REGISTRY.get_action(action_id)` is O(1) dict lookup; constructing `Action` each step is negligible overhead. The `action_def.suricata_category` field (e.g. `"ET SCAN"`) is the IDS category for `collect_feedback`.

---

## Decision 3: available_actions filtering — exclude completed actions

**Decision**: F16 must compute uncompleted reachable actions as:
```python
reachable = attack_graph.available_actions(episode_state.completed_actions)
available = [a for a in reachable if a not in episode_state.completed_actions]
```

`AttackGraph.available_actions(completed)` returns ALL reachable action_ids (entry points UNION successors of completed) — it does NOT filter out already-completed ones. Verified empirically:

```
available_actions(all_15_ids) == all_15_ids  # still returns everything
```

If the loop used the raw `available_actions()` result for the termination check, the episode would never terminate via `completed=True`. The filter `if a not in episode_state.completed_actions` is the correct gate.

**Rationale**: The spec described the check conceptually ("no more actions available to take") — the implementation must honour that intent, which requires filtering.

---

## Decision 4: StepRecord and EpisodeResult as frozen dataclasses

**Decision**: Use `@dataclass(frozen=True)` for both `StepRecord` and `EpisodeResult`. Module: `src/aatf/episode.py`.

Consistent with `FeedbackResult` (F15), `Action`/`DetectionResult` (F03). No Pydantic dependency needed — these are internal value objects, not serialized at this layer.

`EpisodeResult` holds a reference to `episode_state: EpisodeState` which is a mutable object (mutated during the episode). The frozen flag applies to the dataclass fields (the reference is immutable), not to the referenced state. This is acceptable — same pattern used in other places.

**Alternatives considered**: Pydantic models — rejected: over-engineering for purely in-memory orchestration result.

---

## Decision 5: REGISTRY method name

**Decision**: Use `REGISTRY.get_action(action_id: str) -> ActionDefinition`.

Confirmed via: `dir(REGISTRY)` → `['get_action', 'list_actions', 'actions_by_category', '_store']`. The `get_action` method is the correct per-id lookup.

---

## Decision 6: No randomness in run_episode itself

**Decision**: `run_episode` accepts `action_selector: Callable[[list[str], EpisodeState], str]` — all non-determinism is delegated to the selector. The loop itself is deterministic given fixed selector and defence stubs. No `rng` parameter needed in the function signature (the `rng=None` from the original spec proposal is omitted — the selector is the correct injection point).
