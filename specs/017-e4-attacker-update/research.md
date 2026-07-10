# Research: Attacker Update Rule — LinUCB (F17)

**Date**: 2026-07-10
**Feature**: 017-e4-attacker-update

## Decision 1: Context vector dimension d = 50

**Decision**: `d = 50` (float32). Verified by running `build_context(EpisodeState(), current_time=time.time())` from F13 on a fresh state — returns a 50-element float32 array.

**Impact on tests**: Tests use `d=1` or `d=2` for analytic tractability. `d=50` is used only in integration smoke tests (if any). The model accepts `d` as a constructor parameter — tests are fully independent of the real context dimension.

---

## Decision 2: Sherman-Morrison rank-1 update formula (analytic ground truth for SC-001)

**Decision**: Use the Sherman-Morrison formula to update A_inv in-place after each observation, avoiding explicit matrix inversion.

Given A = A_old + outer(context, context), the inverse is updated as:

```
x       = A_inv_old @ context          # d-vector
A_inv   = A_inv_old - outer(x, x) / (1 + context @ x)
b       = b_old + reward * context
```

**Analytic ground truth (d=1, for SC-001 test)**:

```
Input:  A_inv_old = [[1.0]], b_old = [0.0], context = [1.0], reward = 1.0, alpha = 1.0
x       = [[1.0]] @ [1.0] = [1.0]
A_inv   = [[1.0]] - outer([1.0],[1.0]) / (1 + 1.0) = [[1.0]] - [[0.5]] = [[0.5]]
b       = [0.0] + 1.0 * [1.0] = [1.0]
theta   = [[0.5]] @ [1.0] = [0.5]
score   = 0.5 + 1.0 * sqrt([1.0] @ [[0.5]] @ [1.0]) = 0.5 + sqrt(0.5) ≈ 1.2071...
```

Verified numerically: `0.5 + math.sqrt(0.5) = 1.2071067811865475`.

**Rationale**: Sherman-Morrison avoids O(d³) matrix inversion per step; each update is O(d²) — suitable for d=50 without any efficiency concern.

**Alternatives considered**: Explicit re-inversion of A — rejected: O(d³) per step, unnecessary.

---

## Decision 3: Class design — regular class (not frozen dataclass)

**Decision**: `LinUCBModel` is a plain Python class (not `@dataclass`), because it holds mutable per-arm state (`_arms: dict`). Frozen dataclasses are for immutable value objects.

```python
class LinUCBModel:
    def __init__(self, d: int, alpha: float = 1.0) -> None:
        self.d = d
        self.alpha = alpha
        self._arms: dict[str, tuple[np.ndarray, np.ndarray]] = {}
```

`d` is required (no default) — it cannot be inferred from context without a call. `alpha` defaults to 1.0 per spec.

**Alternatives considered**: `@dataclass` with `field(default_factory=dict)` — rejected: mutable fields in dataclasses are semantically misleading for a model class; regular `__init__` is clearer.

---

## Decision 4: Lazy per-arm initialisation

**Decision**: Arms are created on first reference via a private `_get_or_init_arm(action_id)` helper:

```python
def _get_or_init_arm(self, action_id: str) -> tuple[np.ndarray, np.ndarray]:
    if action_id not in self._arms:
        self._arms[action_id] = (np.eye(self.d, dtype=float), np.zeros(self.d, dtype=float))
    return self._arms[action_id]
```

`select_action` uses this helper too — unseen actions get the default (identity A_inv, zero b), giving them a high uncertainty bonus (exploration) before any data is collected.

**Rationale**: Avoids requiring the full action list at construction; consistent with how LinUCB is used in production (arms arrive online).

---

## Decision 5: Tie-breaking in select_action

**Decision**: Iterate over `sorted(available)` and update best only when strictly greater (`>`). The first alphabetical action wins on tied scores.

```python
best_id, best_score = sorted(available)[0], float("-inf")
for action_id in sorted(available):
    score = ...
    if score > best_score:
        best_score, best_id = score, action_id
return best_id
```

Two unseen actions with the same default A_inv and b will produce identical scores for any context — the alphabetically first one wins by construction.

---

## Decision 6: Serialisation format

**Decision**: `to_dict()` returns:
```python
{
    "d": int,
    "alpha": float,
    "arms": {
        action_id: {"A_inv": list[list[float]], "b": list[float]}
        for each arm
    }
}
```

`np.ndarray.tolist()` produces nested Python lists — JSON-serialisable by `json.dumps()` without any custom encoder. `from_dict()` restores with `np.array(data, dtype=float)`.

`from_dict` is a `@classmethod` — no existing instance required.

---

## Decision 7: numpy dtype consistency

**Decision**: Always use `dtype=float` (= float64) for A_inv and b, regardless of whether the real context vector is float32. Tests use float64 literals. The model does not cast incoming contexts — if the caller passes float32, the result is float64 due to NumPy promotion rules.

**Rationale**: float64 gives the precision needed for SC-001 analytic correctness test (< 1e-9 tolerance). float32 would lose ~7 decimal digits.
