# Attacker Contracts (F18)

**Date**: 2026-07-11
**Feature**: 018-e5-attacker-baselines

## Shared Setup

```python
import random
import numpy as np
import pytest
from aatf.attacker import Attacker, RandomAttacker, FixedScriptAttacker, LinUCBAttacker
from aatf.linucb import LinUCBModel
```

---

## C-001: All concrete classes are instances of Attacker

**Story**: US1
**Rationale**: SC-005 — interface compliance is a hard structural requirement.

```python
def test_c001_all_classes_are_attacker_instances() -> None:
    model = LinUCBModel(d=1)
    assert isinstance(RandomAttacker(), Attacker)
    assert isinstance(FixedScriptAttacker(), Attacker)
    assert isinstance(LinUCBAttacker(model), Attacker)
```

---

## C-002: choose_action always returns a value from available

**Story**: US1
**Rationale**: FR-002 — the return value must be one of the candidate action ids.

```python
def test_c002_choose_action_returns_from_available() -> None:
    available = ["tcp_port_scan", "icmp_ping_sweep", "dns_subdomain_enum"]
    ctx = np.zeros(1)
    model = LinUCBModel(d=1)
    for attacker in [RandomAttacker(), FixedScriptAttacker(), LinUCBAttacker(model)]:
        result = attacker.choose_action(available, ctx)
        assert result in available
```

---

## C-003: observe completes without error on all implementations

**Story**: US1
**Rationale**: FR-003 — stateless implementations must accept the call silently.

```python
def test_c003_observe_no_error_all_implementations() -> None:
    ctx = np.array([1.0])
    model = LinUCBModel(d=1)
    for attacker in [RandomAttacker(), FixedScriptAttacker(), LinUCBAttacker(model)]:
        attacker.observe("tcp_port_scan", ctx, reward=1.0)  # must not raise
```

---

## C-004: RandomAttacker seeded determinism

**Story**: US2
**Rationale**: SC-002 / FR-004 — identical seed produces identical choice sequence.

```python
def test_c004_random_attacker_seeded_determinism() -> None:
    available = ["a", "b", "c"]
    ctx = np.zeros(1)
    seq1 = [RandomAttacker(seed=42).choose_action(available, ctx) for _ in range(5)]
    # Build a second independent instance to compare
    rng2 = RandomAttacker(seed=42)
    seq2 = [rng2.choose_action(available, ctx) for _ in range(5)]
    assert seq1 == seq2
```

---

## C-005: RandomAttacker single-element available always returns that element

**Story**: US2
**Rationale**: Edge case — single-item list must be handled correctly.

```python
def test_c005_random_attacker_single_element() -> None:
    attacker = RandomAttacker(seed=0)
    for _ in range(10):
        assert attacker.choose_action(["only_action"], np.zeros(1)) == "only_action"
```

---

## C-006: RandomAttacker raises ValueError on empty available

**Story**: US2
**Rationale**: FR-010 — programming error must surface as ValueError, not silent wrong behaviour.

```python
def test_c006_random_attacker_empty_available_raises() -> None:
    attacker = RandomAttacker()
    with pytest.raises(ValueError):
        attacker.choose_action([], np.zeros(1))
```

---

## C-007: RandomAttacker observe is a no-op (no state change)

**Story**: US2
**Rationale**: FR-003 — stateless attacker; observe must complete silently without affecting RNG state.

```python
def test_c007_random_attacker_observe_noop() -> None:
    # observe between calls must not affect the RNG sequence
    r1 = RandomAttacker(seed=7)
    r2 = RandomAttacker(seed=7)
    available = ["x", "y", "z"]
    ctx = np.zeros(1)
    r1.choose_action(available, ctx)
    r1.observe("x", ctx, reward=-1.0)  # should not affect rng
    r1.choose_action(available, ctx)
    r2.choose_action(available, ctx)
    # after same number of choose_action calls, next result must be same
    assert r1.choose_action(available, ctx) == r2.choose_action(available, ctx)
```

---

## C-008: FixedScriptAttacker explicit script cycles correctly

**Story**: US2
**Rationale**: SC-003 / FR-005 — cycle must repeat from start after exhaustion.

```python
def test_c008_fixed_script_attacker_explicit_cycle() -> None:
    attacker = FixedScriptAttacker(script=["x", "y"])
    ctx = np.zeros(1)
    results = [attacker.choose_action(["x", "y"], ctx) for _ in range(4)]
    assert results == ["x", "y", "x", "y"]
```

---

## C-009: FixedScriptAttacker default alphabetical script from first call

**Story**: US2
**Rationale**: FR-006 — when no script is supplied, first-call available determines the order.

```python
def test_c009_fixed_script_attacker_default_alphabetical() -> None:
    attacker = FixedScriptAttacker()
    ctx = np.zeros(1)
    # Pass in reverse alphabetical order — default must sort
    first = attacker.choose_action(["c_action", "a_action", "b_action"], ctx)
    assert first == "a_action"
    # Script is now locked; subsequent calls cycle ["a_action","b_action","c_action"]
    assert attacker.choose_action(["c_action", "a_action", "b_action"], ctx) == "b_action"
    assert attacker.choose_action(["c_action", "a_action", "b_action"], ctx) == "c_action"
    assert attacker.choose_action(["c_action", "a_action", "b_action"], ctx) == "a_action"
```

---

## C-010: FixedScriptAttacker single-element repeats indefinitely

**Story**: US2
**Rationale**: Edge case — single-item script produces the same element on every call.

```python
def test_c010_fixed_script_attacker_single_element() -> None:
    attacker = FixedScriptAttacker(script=["only"])
    ctx = np.zeros(1)
    for _ in range(5):
        assert attacker.choose_action(["only"], ctx) == "only"
```

---

## C-011: LinUCBAttacker observe delegates to model.update

**Story**: US3
**Rationale**: SC-004 / FR-007 — observe must mutate model state identically to calling update directly.

```python
def test_c011_linucb_attacker_observe_mutates_model() -> None:
    model = LinUCBModel(d=1, alpha=1.0)
    attacker = LinUCBAttacker(model)
    ctx = np.array([1.0])
    attacker.observe("scan", ctx, reward=1.0)
    assert "scan" in model._arms
    _, b = model._arms["scan"]
    assert abs(b[0] - 1.0) < 1e-9  # b = reward * context = 1.0 * [1.0]
```

---

## C-012: LinUCBAttacker choose_action matches model.select_action directly

**Story**: US3
**Rationale**: FR-007 — delegation must be exact, not a reimplementation.

```python
def test_c012_linucb_attacker_choose_action_matches_model() -> None:
    model = LinUCBModel(d=1, alpha=1.0)
    attacker = LinUCBAttacker(model)
    ctx = np.array([1.0])
    available = ["a_action", "b_action"]
    # Both paths must return the same result
    assert attacker.choose_action(available, ctx) == model.select_action(available, ctx)
```
