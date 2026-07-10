# Data Model: Attacker Update Rule — LinUCB (F17)

**Date**: 2026-07-10
**Feature**: 017-e4-attacker-update

## New Entities

### LinUCBModel

The learned belief model for the contextual-bandit attacker.

| Field   | Type                                         | Constraints         | Description                                           |
|---------|----------------------------------------------|---------------------|-------------------------------------------------------|
| d       | int                                          | > 0, required       | Context vector dimension (50 in production, 1–2 in tests) |
| alpha   | float                                        | ≥ 0.0, default 1.0  | Exploration coefficient; 0 = pure greedy              |
| _arms   | dict[str, tuple[np.ndarray, np.ndarray]]     | mutable, private    | Per-action (A_inv, b); created lazily on first reference |

Implementation: plain Python class in `src/aatf/linucb.py`.

**Methods**:
- `_get_or_init_arm(action_id: str) -> tuple[ndarray, ndarray]` — private; returns existing arm or creates default
- `update(action_id: str, context: ndarray, reward: float) -> None` — mutates A_inv and b for action_id
- `select_action(available: list[str], context: ndarray) -> str` — returns highest-UCB action_id
- `to_dict() -> dict` — exports all state as JSON-serialisable dict
- `from_dict(cls, data: dict) -> LinUCBModel` — class method; reconstructs model from dict

### Belief Record (per arm)

Stored as a tuple `(A_inv, b)` in `_arms`. Not a named class — a plain tuple for minimal overhead.

| Component | Type            | Shape    | Initial Value     | Description                                                    |
|-----------|-----------------|----------|-------------------|----------------------------------------------------------------|
| A_inv     | np.ndarray      | (d, d)   | np.eye(d, dtype=float) | Inverse of accumulated observation matrix A               |
| b         | np.ndarray      | (d,)     | np.zeros(d, dtype=float) | Accumulated reward-weighted context vector               |

**Update rule** (per step):
```
x       = A_inv @ context          # d-vector
A_inv   ← A_inv - outer(x, x) / (1.0 + context @ x)   # Sherman-Morrison
b       ← b + reward * context
```

**UCB score** (per candidate action):
```
theta = A_inv @ b
score = (theta @ context) + alpha * sqrt(context @ A_inv @ context)
```

## Serialisation Schema

`to_dict()` output (JSON-safe):
```python
{
    "d": 2,
    "alpha": 1.0,
    "arms": {
        "tcp_port_scan": {
            "A_inv": [[0.5, 0.0], [0.0, 1.0]],
            "b": [1.0, 0.0]
        }
    }
}
```

`from_dict()` reconstruction:
```python
np.array(data["arms"][action_id]["A_inv"], dtype=float)   # → ndarray shape (d, d)
np.array(data["arms"][action_id]["b"], dtype=float)        # → ndarray shape (d,)
```

## Relationships

```
LinUCBModel
  ├── d            ← set at construction; must match context vector output from build_context() (F13)
  ├── alpha        ← injectable; default 1.0
  └── _arms        dict[action_id → (A_inv, b)]
        └── Belief Record  created lazily on first update() or select_action() reference

run_episode() (F16/F20+)
  └── calls LinUCBModel.select_action(available, context)  ← action selection each step
  └── calls LinUCBModel.update(action_id, context, reward) ← belief update after feedback
```

## State Transitions

```
Construction:       _arms = {}  (empty; no beliefs yet)
First reference:    _arms[action_id] = (eye(d), zeros(d))
After update():     _arms[action_id] = (A_inv_new, b_new)  ← mutated in-place replacement
to_dict():          → dict (no mutation)
from_dict():        → fresh LinUCBModel with _arms populated from dict (no empty state)
```
