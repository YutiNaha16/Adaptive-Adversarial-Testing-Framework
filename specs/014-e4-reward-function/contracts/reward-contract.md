# Contract: Reward Function (F14)

**File**: `src/aatf/reward.py`
**Test file**: `tests/test_reward.py`

---

## C-001: detected=True, stage_progress=False → −1.0

```python
from aatf.reward import compute_reward, REWARD_DETECTED
assert compute_reward(detected=True, stage_progress=False) == REWARD_DETECTED
assert compute_reward(detected=True, stage_progress=False) == -1.0
```

---

## C-002: detected=True, stage_progress=True → −1.0 (detection wins)

```python
assert compute_reward(detected=True, stage_progress=True) == REWARD_DETECTED
assert compute_reward(detected=True, stage_progress=True) == -1.0
```

---

## C-003: detected=False, stage_progress=True → +1.0

```python
from aatf.reward import REWARD_PROGRESS
assert compute_reward(detected=False, stage_progress=True) == REWARD_PROGRESS
assert compute_reward(detected=False, stage_progress=True) == 1.0
```

---

## C-004: detected=False, stage_progress=False → −0.1

```python
from aatf.reward import REWARD_STALL
assert compute_reward(detected=False, stage_progress=False) == REWARD_STALL
assert abs(compute_reward(detected=False, stage_progress=False) - (-0.1)) < 1e-9
```

---

## C-005: return type is float

```python
result = compute_reward(detected=False, stage_progress=True)
assert isinstance(result, float)
```

---

## C-006: named constants have correct values

```python
from aatf.reward import REWARD_DETECTED, REWARD_PROGRESS, REWARD_STALL
assert REWARD_DETECTED == -1.0
assert REWARD_PROGRESS == 1.0
assert abs(REWARD_STALL - (-0.1)) < 1e-9
```
