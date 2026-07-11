# Data Model: Attacker Interface + Baselines (F18)

**Date**: 2026-07-11
**Feature**: 018-e5-attacker-baselines

## Entities

### `Attacker` (abstract base class)

**Purpose**: Common policy interface for all attacker implementations.

| Method | Signature | Contract |
|--------|-----------|----------|
| `choose_action` | `(available: list[str], context: np.ndarray) -> str` | Must return one of the strings in `available` |
| `observe` | `(action_id: str, context: np.ndarray, reward: float) -> None` | Must complete without error; stateless implementations may no-op |

**State**: None (pure interface).

---

### `RandomAttacker`

**Purpose**: Uniform-random baseline; deterministic given seed.

| Field | Type | Initial value | Notes |
|-------|------|---------------|-------|
| `_rng` | `random.Random` | `random.Random(seed)` | Private; seeded at construction |

**Behaviour**:
- `choose_action`: `self._rng.choice(available)` — raises `ValueError` if `available` is empty.
- `observe`: no-op.

**State transitions**: `_rng` advances with each `choose_action` call; `observe` does not affect state.

---

### `FixedScriptAttacker`

**Purpose**: Deterministic round-robin baseline over a fixed ordered script.

| Field | Type | Initial value | Notes |
|-------|------|---------------|-------|
| `_script` | `list[str] \| None` | Explicit script or `None` | Set to `sorted(available)` lazily on first call if `None` |
| `_cycle` | `Iterator[str] \| None` | `None` | `itertools.cycle(self._script)` created on first `choose_action` |

**Behaviour**:
- `choose_action`: initialises `_cycle` from `_script` (or `sorted(available)`) on first call; returns `next(self._cycle)` thereafter.
- `observe`: no-op.

**State transitions**: `_script` set once (lazily); `_cycle` advances one position per `choose_action` call.

---

### `LinUCBAttacker`

**Purpose**: Thin adapter wrapping `LinUCBModel` behind the `Attacker` interface.

| Field | Type | Notes |
|-------|------|-------|
| `_model` | `LinUCBModel` | Injected at construction; mutable (updated by `observe`) |

**Behaviour**:
- `choose_action`: delegates to `self._model.select_action(available, context)`.
- `observe`: delegates to `self._model.update(action_id, context, reward)`.

**State transitions**: `_model._arms` mutated by `observe` (via `LinUCBModel.update`); `choose_action` is read-only from `_model`'s perspective (but `_get_or_init_arm` may create lazy arm entries as a side-effect of `select_action`).

---

## Relationships

```
Attacker (ABC)
  ├── RandomAttacker        — wraps random.Random
  ├── FixedScriptAttacker   — wraps itertools.cycle
  └── LinUCBAttacker        — wraps LinUCBModel (from aatf.linucb, spec-017)
                                   └── _arms: dict[str, (A_inv, b)]
```

## Module import map

```python
# All importable from one place:
from aatf.attacker import Attacker, RandomAttacker, FixedScriptAttacker, LinUCBAttacker
from aatf.linucb import LinUCBModel  # needed only when constructing LinUCBAttacker
```
