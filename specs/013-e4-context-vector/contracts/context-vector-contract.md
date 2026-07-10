# Contract: Context Vector Builder (F13)

**File**: `src/aatf/context_vector.py`
**Test file**: `tests/test_context_vector.py`

---

## C-001: Output shape and dtype

`build_context(state)` returns `np.ndarray` with `shape == (50,)` and `dtype == np.float32`.

```python
state = EpisodeState(completed_actions=set(), detection_history={},
                     alert_history=[], step=0, start_time=time.time(),
                     fired_categories=set())
vec = build_context(state)
assert vec.shape == (CONTEXT_DIM,)
assert vec.dtype == np.float32
```

---

## C-002: CONTEXT_DIM constant equals 50

```python
from aatf.context_vector import CONTEXT_DIM
assert CONTEXT_DIM == 50
```

---

## C-003: Pure / deterministic

Two calls with identical EpisodeState (same start_time, same injected current_time) return bitwise-identical arrays.

```python
t = time.time()
state = EpisodeState(..., start_time=t, ...)
assert np.array_equal(build_context(state, t), build_context(state, t))
```

---

## C-004: Fresh state — all zeros except timing

For step=0, empty collections, current_time == start_time:

```python
vec = build_context(state, current_time=state.start_time)
assert np.all(vec == 0.0)
```

(timing slots are both 0.0 when step=0 and elapsed=0.)

---

## C-005: alert_history window — zero-pad left, most-recent in slot 9

Three-step history `[True, False, True]`, window=10:

```python
state.alert_history = [True, False, True]
vec = build_context(state, current_time=state.start_time)
alert = vec[0:10]
expected = [0,0,0,0,0,0,0, 1.0, 0.0, 1.0]
assert np.allclose(alert, expected)
```

---

## C-006: alert_history window — truncate to last N when longer than N

History of 12 bools; only the last 10 appear.

```python
state.alert_history = [True]*2 + [False]*10  # 12 entries
vec = build_context(state, current_time=state.start_time)
assert np.all(vec[0:10] == 0.0)  # last 10 are all False
```

---

## C-007: attack_progress — completed action flags 1.0

`tcp_port_scan` completed → its slot is 1.0, all others 0.0.

```python
state.completed_actions = {"tcp_port_scan"}
vec = build_context(state, current_time=state.start_time)
progress = vec[10:25]
tcp_idx = sorted_action_ids.index("tcp_port_scan")
assert progress[tcp_idx] == 1.0
assert progress.sum() == 1.0
```

---

## C-008: technique_history — detection rate correct

`ssh_brute_force` executed 3 times, detected 2:

```python
state.detection_history = {"ssh_brute_force": [True, True, False]}
vec = build_context(state, current_time=state.start_time)
tech = vec[25:40]
ssh_idx = sorted_action_ids.index("ssh_brute_force")
assert abs(tech[ssh_idx] - 2/3) < 1e-5
```

---

## C-009: technique_history — zero for never-executed action, no NaN

```python
state.detection_history = {}
vec = build_context(state, current_time=state.start_time)
assert not np.any(np.isnan(vec[25:40]))
assert np.all(vec[25:40] == 0.0)
```

---

## C-010: timing — step normalisation, clips at 1.0

`step=50` → timing[0] = 0.5; `step=200` → timing[0] = 1.0.

```python
state.step = 50
vec = build_context(state, current_time=state.start_time)
assert abs(vec[40] - 0.5) < 1e-5

state.step = 200
vec = build_context(state, current_time=state.start_time)
assert vec[40] == pytest.approx(1.0)
```

---

## C-011: timing — elapsed normalisation

`current_time - start_time = 1800` → timing[1] = 0.5.

```python
state.step = 0
vec = build_context(state, current_time=state.start_time + 1800)
assert abs(vec[41] - 0.5) < 1e-5
```

---

## C-012: rule_category_fired — correct flag positions

`fired_categories = {"ET SCAN", "ET DNS"}` → slots 42 and 46 are 1.0, others 0.0.

```python
state.fired_categories = {"ET SCAN", "ET DNS"}
vec = build_context(state, current_time=state.start_time)
cats = vec[42:50]
assert cats[0] == 1.0   # ET SCAN
assert cats[4] == 1.0   # ET DNS
assert cats.sum() == 2.0
```

---

## C-013: unknown fired category silently ignored

```python
state.fired_categories = {"ET SCAN", "UNKNOWN_CATEGORY_XYZ"}
vec = build_context(state, current_time=state.start_time)
assert vec[42:50].sum() == 1.0  # only ET SCAN counted
```

---

## C-014: negative step raises ValueError

```python
with pytest.raises(ValueError, match="step must be non-negative"):
    EpisodeState(completed_actions=set(), detection_history={},
                 alert_history=[], step=-1, start_time=time.time(),
                 fired_categories=set())
```

---

## C-015: unknown action_id in completed_actions raises ValueError

```python
with pytest.raises(ValueError, match="unknown action_id"):
    EpisodeState(completed_actions={"nonexistent_xyz"}, detection_history={},
                 alert_history=[], step=0, start_time=time.time(),
                 fired_categories=set())
```

---

## C-016: no NaN or infinity in output for any valid state

```python
state = EpisodeState(
    completed_actions={"tcp_port_scan", "ssh_brute_force"},
    detection_history={"tcp_port_scan": [True, False], "ssh_brute_force": [False]},
    alert_history=[True, False, True],
    step=5,
    start_time=time.time() - 300,
    fired_categories={"ET SCAN"},
)
vec = build_context(state)
assert not np.any(np.isnan(vec))
assert not np.any(np.isinf(vec))
```
