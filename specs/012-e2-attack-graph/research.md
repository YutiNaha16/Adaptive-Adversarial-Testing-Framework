# Research: Attack Graph Staging (F09)

## Decision 1 — Data structure: frozen dataclass vs plain class with __slots__

- **Decision**: `@dataclass(frozen=True)` with `__post_init__` validation
- **Rationale**: `frozen=True` makes the instance hash-able and immutable after construction. `__post_init__` runs during `__init__` (before the freeze lock) so validation can read fields without violating immutability. No need for `__slots__` — the dataclass generates `__eq__` and `__hash__` automatically.
- **Alternatives considered**: Plain class with `__slots__` — more verbose with no benefit here since we have no performance-sensitive hot path. NamedTuple — fields would need to be tuples not frozensets, awkward for the edge dict.

## Decision 2 — available_actions semantics: direct successors only (not transitive closure)

- **Decision**: Return `entry_points ∪ {successor for action_id in completed for successor in edges.get(action_id, frozenset())}`. Direct successors only.
- **Rationale**: The spec Assumptions section explicitly states "completing action B is sufficient to unlock B's successors even if B was itself a successor of A and A was not completed." This means the experiment loop adds each action_id to `completed` as it runs them; the graph only needs to look one hop ahead. Transitive closure would require BFS/DFS and is unnecessary complexity.
- **Alternatives considered**: Full transitive reachability (BFS from entry points given completed set) — more complex and not required by the spec. Would also change the adversary-shortcut semantics documented in spec Assumptions.

## Decision 3 — Validation strategy: import-time vs construction-time

- **Decision**: Validate in `AttackGraph.__post_init__` — raises `ValueError` with the offending action_id if any entry_point or successor target is not in `REGISTRY`. Since `ATTACK_GRAPH` is constructed at module scope, this fires at import time.
- **Rationale**: FR-005 requires import-time validation. Constructing the constant at module scope achieves this without any separate import hook or metaclass magic. If `REGISTRY` is imported first (which it is, since `action_library` is a dependency), the REGISTRY is populated before validation runs.
- **Alternatives considered**: Separate `validate(registry)` call — requires the caller to remember to call it. Module `__init_subclass__` hook — overcomplicated for a single constant.

## Decision 4 — edges field type: dict[str, frozenset[str]] (not list)

- **Decision**: `edges: dict[str, frozenset[str]]` — maps each source action_id to a frozenset of target action_ids.
- **Rationale**: `frozenset` for values ensures the `AttackGraph` is fully immutable (no mutable collections inside a frozen dataclass). Lookup is O(1) average. A list of tuples would be O(n) for lookup. `frozenset` also prevents duplicate edges at construction.
- **Alternatives considered**: `dict[str, list[str]]` — mutable lists violate the spirit of `frozen=True`; Python allows it but it's semantically wrong. `frozenset[tuple[str, str]]` for edges — harder to look up by source.

## Decision 5 — available_actions return type: list[str] (sorted)

- **Decision**: Return `sorted(reachable)` as `list[str]`.
- **Rationale**: FR-004 requires deterministic output. Sorting by action_id string gives a stable, reproducible order without needing any additional state. The caller (experiment loop) can iterate or sample from the list.
- **Alternatives considered**: `frozenset[str]` — caller would need to convert for iteration; less ergonomic. Unsorted list — non-deterministic ordering across Python versions/environments.

## Decision 6 — Module structure: single file, no sub-packages

- **Decision**: Single file `src/aatf/attack_graph.py` exporting `AttackGraph`, `ATTACK_GRAPH`.
- **Rationale**: The feature is ~50 lines of logic. A sub-package would add indirection with no benefit. Consistent with F07 (`action_library.py`) and F08 (`action_executor.py`).
- **Alternatives considered**: Separate `topology.py` for the edge data — premature split; the topology is inseparable from the graph class.

## No NEEDS CLARIFICATION items

All design decisions are resolved. The canonical v1 topology is fully specified in spec Assumptions. No external dependencies to research.
