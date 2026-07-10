# LinUCB Contracts (F17)

**Date**: 2026-07-10
**Feature**: 017-e4-attacker-update

## Shared Setup

```python
import json, math
import numpy as np
from aatf.linucb import LinUCBModel
```

---

## C-001: update() — A_inv correct after one observation (analytic ground truth)

**Story**: US1
**Rationale**: SC-001 — verifies Sherman-Morrison formula is correctly implemented to floating-point precision.

```python
def test_c001_update_a_inv_analytic() -> None:
    model = LinUCBModel(d=1, alpha=1.0)
    ctx = np.array([1.0])
    model.update("a", ctx, reward=1.0)
    A_inv, _ = model._arms["a"]
    expected = np.array([[0.5]])
    assert abs(A_inv[0, 0] - expected[0, 0]) < 1e-9
```

---

## C-002: update() — b correct after one observation (analytic ground truth)

**Story**: US1
**Rationale**: b = b_old + reward * context — simplest possible update.

```python
def test_c002_update_b_analytic() -> None:
    model = LinUCBModel(d=1, alpha=1.0)
    ctx = np.array([1.0])
    model.update("a", ctx, reward=2.0)
    _, b = model._arms["a"]
    expected = np.array([2.0])
    assert abs(b[0] - expected[0]) < 1e-9
```

---

## C-003: update() — lazy init creates eye(d) and zeros(d) on first reference

**Story**: US1
**Rationale**: FR-001/FR-003 — new action_ids must start from identity/zero before update.

```python
def test_c003_update_lazy_init() -> None:
    model = LinUCBModel(d=2, alpha=1.0)
    assert "new_action" not in model._arms
    model.update("new_action", np.array([1.0, 0.0]), reward=0.0)
    assert "new_action" in model._arms
    # reward=0 → b should still be zeros (0 * context)
    _, b = model._arms["new_action"]
    assert np.allclose(b, np.zeros(2))
```

---

## C-004: update() — A_inv and b correct after two sequential observations (d=2)

**Story**: US1
**Rationale**: Verifies correctness accumulates correctly across multiple updates.

```python
def test_c004_update_two_steps() -> None:
    model = LinUCBModel(d=2, alpha=1.0)
    ctx1 = np.array([1.0, 0.0])
    ctx2 = np.array([0.0, 1.0])
    model.update("a", ctx1, reward=1.0)
    model.update("a", ctx2, reward=0.5)
    A_inv, b = model._arms["a"]
    # After ctx1: A_inv=[[0.5,0],[0,1]], b=[1,0]
    # After ctx2: x=A_inv@ctx2=[0,1]; A_inv-=outer([0,1],[0,1])/(1+0*1+1*1)=[[0,0],[0,0.5]]
    #             A_inv=[[0.5,0],[0,0.5]], b=[1,0]+0.5*[0,1]=[1,0.5]
    expected_A = np.array([[0.5, 0.0], [0.0, 0.5]])
    expected_b = np.array([1.0, 0.5])
    assert np.allclose(A_inv, expected_A, atol=1e-9)
    assert np.allclose(b, expected_b, atol=1e-9)
```

---

## C-005: select_action() — returns highest-UCB action between trained and untrained

**Story**: US2
**Rationale**: SC-002/SC-006 — trained action (positive reward) must beat untrained action.

```python
def test_c005_select_trained_over_untrained() -> None:
    model = LinUCBModel(d=1, alpha=1.0)
    ctx = np.array([1.0])
    # Give "b_action" 5 positive updates; leave "a_action" untrained
    for _ in range(5):
        model.update("b_action", ctx, reward=1.0)
    winner = model.select_action(["a_action", "b_action"], ctx)
    assert winner == "b_action"
```

---

## C-006: select_action() — alphabetical tie-break when scores are equal

**Story**: US2
**Rationale**: SC-003 — tie-break must be deterministic; alphabetically first wins.

```python
def test_c006_select_alphabetical_tie_break() -> None:
    # Both arms unseen → identical default A_inv and b → same UCB score for any context
    model = LinUCBModel(d=2, alpha=1.0)
    ctx = np.array([1.0, 1.0])
    # Pass in reverse alphabetical order to show it's not order-dependent
    winner = model.select_action(["z_action", "a_action", "m_action"], ctx)
    assert winner == "a_action"
```

---

## C-007: select_action() — alpha=0 gives pure greedy (exploration term = 0)

**Story**: US2
**Rationale**: FR-007, edge case from spec — zero exploration reduces to argmax of expected reward.

```python
def test_c007_select_alpha_zero_pure_greedy() -> None:
    model = LinUCBModel(d=1, alpha=0.0)
    ctx = np.array([1.0])
    model.update("good", ctx, reward=1.0)
    # With alpha=0: score = theta @ context (no exploration bonus)
    # "good" has theta=A_inv@b=[[0.5]]@[1.0]=[0.5], score=0.5
    # "bad" has theta=[[1.0]]@[0.0]=[0.0], score=0.0
    # Tie: "bad" and "other" both untrained score 0.0; "good" scores 0.5 → "good" wins
    winner = model.select_action(["good", "other"], ctx)
    assert winner == "good"
```

---

## C-008: to_dict() — output is JSON-serialisable (no numpy arrays)

**Story**: US3
**Rationale**: SC-004 — zero tolerance; any non-serialisable object fails.

```python
def test_c008_to_dict_json_serialisable() -> None:
    model = LinUCBModel(d=2, alpha=1.5)
    model.update("scan", np.array([1.0, 0.0]), reward=0.8)
    d = model.to_dict()
    # Must not raise
    serialised = json.dumps(d)
    assert '"scan"' in serialised
    assert d["alpha"] == 1.5
    assert d["d"] == 2
```

---

## C-009: from_dict() — round-trip produces identical select_action() output

**Story**: US3
**Rationale**: SC-005 — restored model must be functionally identical.

```python
def test_c009_round_trip_identical_scores() -> None:
    model = LinUCBModel(d=2, alpha=1.0)
    ctx = np.array([1.0, 0.5])
    model.update("tcp_port_scan", ctx, reward=1.0)
    model.update("udp_sweep", ctx, reward=-1.0)

    restored = LinUCBModel.from_dict(model.to_dict())
    available = ["tcp_port_scan", "udp_sweep"]
    assert model.select_action(available, ctx) == restored.select_action(available, ctx)
```

---

## C-010: from_dict() of fresh model behaves like new LinUCBModel

**Story**: US3
**Rationale**: FR-012 — round-trip of a model with no updates must reproduce the same scores as constructing a new model.

```python
def test_c010_round_trip_fresh_model() -> None:
    original = LinUCBModel(d=2, alpha=1.0)
    restored = LinUCBModel.from_dict(original.to_dict())
    ctx = np.array([1.0, 0.0])
    available = ["a", "b"]
    # Both fresh → should pick alphabetically first ("a") in both cases
    assert original.select_action(available, ctx) == "a"
    assert restored.select_action(available, ctx) == "a"
```
