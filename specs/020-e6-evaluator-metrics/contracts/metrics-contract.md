# Contracts: Evaluator & Metrics (F20)

**Feature**: 020-e6-evaluator-metrics
**Date**: 2026-07-11
**Module under test**: `aatf.metrics`
**Test file**: `tests/test_metrics.py`

All tests use `StepRecord` imported from `aatf.episode` and `EpisodeRecord` from `aatf.metrics`.

---

## Helpers (used across contracts)

```python
from aatf.episode import StepRecord
from aatf.metrics import EpisodeRecord

def _step(detected: bool, stage_progress: bool = False, reward: float = 0.0) -> StepRecord:
    return StepRecord(action_id="scan", detected=detected, stage_progress=stage_progress, reward=reward)

def _ep(episode_index: int, steps: list[StepRecord], *, completed: bool = True) -> EpisodeRecord:
    return EpisodeRecord(
        attacker_class="TestAttacker",
        seed=0,
        steps=steps,
        total_reward=sum(s.reward for s in steps),
        completed=completed,
        episode_index=episode_index,
    )
```

---

## US1 — EpisodeRecord Contract

### C-001: EpisodeRecord construction with known fields

```python
def test_c001_episode_record_construction() -> None:
    steps = [_step(True), _step(False)]
    rec = _ep(episode_index=0, steps=steps)
    assert rec.attacker_class == "TestAttacker"
    assert rec.seed == 0
    assert rec.steps == steps
    assert rec.completed is True
    assert rec.episode_index == 0
```

**Expected**: Fields accessible; dataclass frozen (no AttributeError on read).

---

### C-002: EpisodeRecord with completed=False (hit step limit)

```python
def test_c002_episode_record_incomplete() -> None:
    rec = _ep(episode_index=3, steps=[_step(True), _step(True)], completed=False)
    assert rec.completed is False
    assert rec.episode_index == 3
```

**Expected**: `completed=False` stored correctly.

---

### C-003: EpisodeRecord with empty steps list

```python
def test_c003_episode_record_empty_steps() -> None:
    rec = _ep(episode_index=0, steps=[])
    assert rec.steps == []
    assert rec.total_reward == 0.0
```

**Expected**: Valid record; empty steps list.

---

## US2 — detection_rate

### C-004: All steps detected → 1.0

```python
def test_c004_detection_rate_all_detected() -> None:
    records = [
        _ep(0, [_step(True), _step(True), _step(True)]),
        _ep(1, [_step(True), _step(True)]),
    ]
    assert detection_rate(records) == 1.0
```

**Expected**: 5/5 = 1.0.

---

### C-005: No steps detected → 0.0

```python
def test_c005_detection_rate_none_detected() -> None:
    records = [
        _ep(0, [_step(False), _step(False)]),
        _ep(1, [_step(False), _step(False), _step(False)]),
    ]
    assert detection_rate(records) == 0.0
```

**Expected**: 0/5 = 0.0.

---

### C-006: Partial detection → correct fraction

```python
def test_c006_detection_rate_partial() -> None:
    # ep0: 3 steps, 2 detected; ep1: 2 steps, 0 detected → 2/5 = 0.4
    records = [
        _ep(0, [_step(True), _step(True), _step(False)]),
        _ep(1, [_step(False), _step(False)]),
    ]
    assert abs(detection_rate(records) - 0.4) < 1e-9
```

**Expected**: 2/5 = 0.4.

---

### C-007: Empty records list → 0.0

```python
def test_c007_detection_rate_empty() -> None:
    assert detection_rate([]) == 0.0
```

**Expected**: No steps → 0.0 (no ZeroDivisionError).

---

## US3 — robustness_score & adaptation_gain

### C-008: robustness_score uses last window episodes

```python
def test_c008_robustness_score_last_window() -> None:
    # 6 episodes: first 3 all detected (dr=1.0), last 3 none detected (dr=0.0)
    records = (
        [_ep(i, [_step(True)]) for i in range(3)] +
        [_ep(i + 3, [_step(False)]) for i in range(3)]
    )
    score = robustness_score(records, window=3)
    assert score == 0.0  # last 3 all non-detected
```

**Expected**: `detection_rate(records[-3:])` = 0.0.

---

### C-009: robustness_score with window > len(records) uses all records

```python
def test_c009_robustness_score_window_exceeds_len() -> None:
    records = [_ep(i, [_step(True)]) for i in range(3)]  # 3 records, all detected
    score = robustness_score(records, window=20)
    assert score == 1.0  # uses all 3 records
```

**Expected**: 3/3 = 1.0 (Python slice handles window > len naturally).

---

### C-010: robustness_score empty records → 0.0

```python
def test_c010_robustness_score_empty() -> None:
    assert robustness_score([], window=5) == 0.0
```

**Expected**: No records → 0.0.

---

### C-011: adaptation_gain positive (learner evades more)

```python
def test_c011_adaptation_gain_positive() -> None:
    # baseline: 8/10 detected → dr=0.8
    baseline = [_ep(i, [_step(True)] * 4 + [_step(False)] * 1) for i in range(2)]
    # learner: 5/10 detected → dr=0.5
    learner = [_ep(i, [_step(True)] * 2 + [_step(False)] * 3) for i in range(2)]
    gain = adaptation_gain(baseline, learner)
    assert abs(gain - 30.0) < 1e-9  # (0.8 - 0.5) * 100 = 30.0
```

**Expected**: 30.0 pp.

---

### C-012: adaptation_gain zero (equal detection rates)

```python
def test_c012_adaptation_gain_zero() -> None:
    records = [_ep(i, [_step(True), _step(False)]) for i in range(3)]
    gain = adaptation_gain(records, records)
    assert gain == 0.0
```

**Expected**: 0.0 pp.

---

### C-013: adaptation_gain negative (learner is worse)

```python
def test_c013_adaptation_gain_negative() -> None:
    # baseline: 3/10 detected → dr=0.3; learner: 6/10 detected → dr=0.6
    baseline = [_ep(i, [_step(True)] * 1 + [_step(False)] * 4) for i in range(2)]  # 2/10
    # let's use simpler: 3 detected, 7 not across 2 episodes
    baseline = [_ep(0, [_step(True)] * 1 + [_step(False)] * 4),
                _ep(1, [_step(True)] * 2 + [_step(False)] * 3)]  # 3/10
    learner = [_ep(0, [_step(True)] * 3 + [_step(False)] * 2),
               _ep(1, [_step(True)] * 3 + [_step(False)] * 2)]  # 6/10
    gain = adaptation_gain(baseline, learner)
    assert abs(gain - (-30.0)) < 1e-9  # (0.3 - 0.6) * 100 = -30.0
```

**Expected**: -30.0 pp.

---

## US4 — convergence_episodes

### C-014: convergence at known episode (window=3)

```python
def test_c014_convergence_at_known_episode() -> None:
    # ep0,ep1: detected=True; ep2,ep3,ep4: detected=False; window=3, threshold=0.5
    records = (
        [_ep(i, [_step(True)]) for i in range(2)] +
        [_ep(i + 2, [_step(False)]) for i in range(3)]
    )
    # i=3: records[1:4] = [T, F, F] → dr=1/3 < 0.5 → return records[3].episode_index = 3
    result = convergence_episodes(records, threshold=0.5, window=3)
    assert result == 3
```

**Expected**: Episode index 3 (first trailing-window dr < threshold).

---

### C-015: no convergence (dr never drops below threshold)

```python
def test_c015_no_convergence() -> None:
    records = [_ep(i, [_step(True)]) for i in range(5)]  # all detected → dr=1.0
    assert convergence_episodes(records, threshold=0.5) is None
```

**Expected**: None.

---

### C-016: immediate convergence at episode 0

```python
def test_c016_immediate_convergence() -> None:
    records = [_ep(0, [_step(False)]), _ep(1, [_step(False)])]
    result = convergence_episodes(records, threshold=0.5, window=1)
    assert result == 0  # records[0].episode_index = 0
```

**Expected**: 0 (first episode immediately below threshold).

---

### C-017: empty records → None

```python
def test_c017_convergence_empty_records() -> None:
    assert convergence_episodes([]) is None
```

**Expected**: None.

---

## Import Contract

```python
# Everything needed must be importable from aatf.metrics:
from aatf.metrics import (
    EpisodeRecord,
    detection_rate,
    robustness_score,
    adaptation_gain,
    convergence_episodes,
)
```

All five names MUST be importable from `aatf.metrics` with no ImportError.

---

## Contract Summary

| ID | Function | Scenario | Expected |
|----|----------|----------|----------|
| C-001 | EpisodeRecord | Full construction | All fields accessible |
| C-002 | EpisodeRecord | completed=False | completed stored correctly |
| C-003 | EpisodeRecord | Empty steps | steps=[], total_reward=0.0 |
| C-004 | detection_rate | All detected | 1.0 |
| C-005 | detection_rate | None detected | 0.0 |
| C-006 | detection_rate | 2/5 detected | 0.4 |
| C-007 | detection_rate | Empty list | 0.0 |
| C-008 | robustness_score | Last-window slice | 0.0 (last 3 undetected) |
| C-009 | robustness_score | window > len | Uses all (1.0) |
| C-010 | robustness_score | Empty list | 0.0 |
| C-011 | adaptation_gain | Positive (0.8-0.5) | 30.0 |
| C-012 | adaptation_gain | Zero (equal) | 0.0 |
| C-013 | adaptation_gain | Negative (0.3-0.6) | -30.0 |
| C-014 | convergence_episodes | Converges at ep 3 | 3 |
| C-015 | convergence_episodes | Never converges | None |
| C-016 | convergence_episodes | Immediate (ep 0) | 0 |
| C-017 | convergence_episodes | Empty list | None |
