# Research: Attacker Interface + Baselines (F18)

**Date**: 2026-07-11
**Feature**: 018-e5-attacker-baselines

## Decision 1: Abstract base class mechanism

**Decision**: Use `abc.ABC` + `@abstractmethod` (stdlib, zero deps).

**Rationale**: Standard Python pattern; subclass compliance enforced at instantiation time; works with `isinstance(obj, Attacker)` for type checks; no need for Pydantic or Protocol here since concrete implementations are in-process.

**Alternatives considered**: `typing.Protocol` (structural subtyping — allows duck typing without explicit inheritance). Rejected because the spec requires explicit compliance testing via `isinstance`, and Protocol only works with `isinstance` if `@runtime_checkable` is added; ABC is simpler and the established pattern already used for `Defence` (F10).

## Decision 2: RandomAttacker RNG

**Decision**: `random.Random(seed)` instance stored per-object.

**Rationale**: `random.Random` is seeded once at construction; produces a stateful RNG isolated from the global `random` module state; `choice(available)` is uniform and deterministic given seed. Verified: `random.Random(42).choice(['a','b','c'])` first call → `'c'`; identical on fresh instance.

**Alternatives considered**: `numpy.random.default_rng(seed)` — heavier import; already using numpy for context but no advantage here since we're picking from a list. `random.seed()` (global) — rejected; mutates global state, breaks parallel tests.

## Decision 3: FixedScriptAttacker cycle mechanism

**Decision**: `itertools.cycle` iterator, created lazily on first `choose_action` call; iterator stored as instance variable.

**Rationale**: `itertools.cycle` is a stdlib infinite iterator — no need to track index manually. Lazy init allows the default-alphabetical-sort behaviour (we don't know `available` at construction time). The cycle object persists across calls, so position is maintained correctly.

**Implementation sketch**:
```python
def choose_action(self, available, context):
    if self._cycle is None:
        if self._script is None:
            self._script = sorted(available)
        self._cycle = itertools.cycle(self._script)
    return next(self._cycle)
```

**Alternatives considered**: Manual index with `self._script[self._index % len(self._script)]` and `self._index += 1` — equivalent, slightly more explicit. Rejected in favour of `cycle` because it is idiomatic and eliminates index arithmetic.

## Decision 4: LinUCBAttacker delegation

**Decision**: Thin delegation — `choose_action` → `self._model.select_action(available, context)`; `observe` → `self._model.update(action_id, context, reward)`. No additional logic.

**Rationale**: The `LinUCBModel` (spec-017) already implements the full UCB selection and Sherman-Morrison update. `LinUCBAttacker` is purely an adapter that maps the `Attacker` interface to `LinUCBModel`'s API. Adding any logic here would duplicate what is already in `LinUCBModel` and obscure the delegation.

**Alternatives considered**: Inlining the LinUCB math in `LinUCBAttacker` — rejected; would duplicate spec-017 code, violate DRY, and make `LinUCBModel` orphaned.

## Decision 5: Module layout

**Decision**: Single file `src/aatf/attacker.py` containing `Attacker`, `RandomAttacker`, `FixedScriptAttacker`, `LinUCBAttacker`.

**Rationale**: All four are small classes with minimal code. A single-file module keeps imports simple (`from aatf.attacker import RandomAttacker, LinUCBAttacker`). All four are highly cohesive — they all implement the same interface.

**Alternatives considered**: Separate files per class — overcomplicated for this size; would require an `__init__.py` re-export and produce unnecessary module fragmentation.

## Decision 6: Analytic ground truth for contracts

- **C-003** (seeded determinism): `random.Random(42).choice(['a','b','c'])` for 5 calls → `['c','a','a','c','b']`. Verified empirically.
- **C-007** (FixedScriptAttacker explicit cycle): `script=['x','y']`, 4 calls → `['x','y','x','y']`. Verified.
- **C-008** (FixedScriptAttacker default): `available=['c','a','b']` → default script = `sorted(['c','a','b'])` = `['a','b','c']`; first call → `'a'`.
- **C-010** (LinUCBAttacker observe mutates): `observe("scan", np.array([1.0]), 1.0)` on fresh `LinUCBModel(d=1)` → `model._arms["scan"]` created; `b = [1.0]` (from spec-017 C-002 ground truth).
- **C-011** (LinUCBAttacker choose_action matches model directly): fresh `LinUCBModel(d=1, alpha=1.0)`, `available=['a','b']`, `ctx=[1.0]` → alphabetical tie-break → `'a'` from both direct call and via `LinUCBAttacker`.

## Decision 7: Test isolation

All tests use d=1 or d=2 context vectors for tractability. No REGISTRY, ATTACK_GRAPH, or episode loop needed — pure unit tests. `LinUCBAttacker` tests inject a `LinUCBModel(d=1)` directly.
