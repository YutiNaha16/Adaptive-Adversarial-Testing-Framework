# Research: Feedback Collector (F15)

**Feature**: `015-e4-feedback-collector` | **Date**: 2026-07-10

No NEEDS CLARIFICATION items — all design decisions are fully specified. Documented for rationale record.

---

## Decision 1: FeedbackResult type — frozen dataclass vs namedtuple

**Decision**: `@dataclass(frozen=True)` with two bool fields.

**Rationale**: Consistent with project style (F03 uses dataclasses throughout). Frozen guarantees immutability without boilerplate. IDE/mypy type checking is richer than namedtuple (field names visible, not positional). Future field addition (e.g., `reward: float` in Phase 2) requires only one decorator change.

**Alternatives considered**: `collections.namedtuple` — rejected because positional access is error-prone for callers and type checkers produce weaker inference. `typing.NamedTuple` — acceptable but less consistent with rest of codebase.

---

## Decision 2: Mutation order (FR-009) — snapshot before or after?

**Decision**: Snapshot `before_actions = set(attack_graph.available_actions(episode_state.completed_actions))` **before** any mutation, then add `action_id` to `completed_actions`, then compute `after_actions`.

**Rationale**: `available_actions()` on the AttackGraph (F09) returns successors of all completed actions. Adding `action_id` to `completed_actions` first means `after_actions` includes any steps unlocked by the just-executed action. If we snapshotted after adding, we'd need to remove the action again to get the "before" set — more complex and error-prone.

**Alternatives considered**: Snapshot after mutation → rejected because it makes "before" impossible to reconstruct without reversing the mutation. Pass both sets to caller → rejected because it violates the single-responsibility of collect_feedback.

---

## Decision 3: detection_history initialisation — setdefault vs explicit if

**Decision**: `episode_state.detection_history.setdefault(action_id, []).append(alert_fired)`

**Rationale**: One-liner, idiomatic Python, atomically initialises the list and appends. No risk of key-not-found errors. Readable.

**Alternatives considered**: `if action_id not in detection_history: detection_history[action_id] = []` followed by `detection_history[action_id].append(...)` — functionally identical but 2 lines with more mutation surface.

---

## Decision 4: EpisodeState import location

**Decision**: `from aatf.context_vector import EpisodeState`

**Rationale**: EpisodeState was defined in F13 (`context_vector.py`). F15 depends on F13 per the spec. The coupling is explicit and intentional — feedback.py directly extends context_vector.py's data model.

**Alternatives considered**: Moving EpisodeState to its own `episode.py` module — valid but premature refactor for Phase 1; deferred to F16 planning if the episode loop needs it separately.

---

## Decision 5: stage_progress computation — set difference idiom

**Decision**: `stage_progress = bool(after_actions - before_actions)`

**Rationale**: `set.difference()` gives exactly the newly reachable actions. An empty set is falsy, so `bool()` is a clean one-liner. No branching needed.

**Alternatives considered**: `len(after_actions) > len(before_actions)` — incorrect when actions are removed from the graph (not possible in Phase 1 but fragile). `any(a not in before_actions for a in after_actions)` — semantically equivalent but less readable.

---

## No Unknowns

All five decisions are resolved. No external research required — all answers derive from existing project code (F09 AttackGraph API, F13 EpisodeState definition) and Python stdlib idioms.
