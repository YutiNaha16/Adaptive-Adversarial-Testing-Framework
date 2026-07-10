# Episode Loop Contracts (F16)

**Date**: 2026-07-10
**Feature**: 016-e4-episode-loop

## Shared Test Fixtures

```python
from aatf.contracts import Action, DetectionResult
from aatf.defence import Defence

class StubDefence(Defence):
    def __init__(self, alert: bool = False) -> None:
        self._alert = alert
    def observe(self, action: Action) -> DetectionResult:
        return DetectionResult(alerted=self._alert, rule_ids=[], anomaly_score=0.0, coverage="unknown")

_SELECTOR = lambda available, state: available[0]   # always picks first (alphabetical)
_EXECUTE = lambda action_id: None                    # no-op

# IDs for test setup
from aatf.action_library import REGISTRY
_ALL_IDS = frozenset(a.action_id for a in REGISTRY.list_actions())  # all 15
```

---

## C-001: StepRecord.action_id matches the selected action

**Story**: US1  
**Rationale**: Verifies the step record faithfully records what the selector chose.

```python
state = EpisodeState()
result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=1)
assert len(result.steps) == 1
assert result.steps[0].action_id in ["dns_subdomain_enum", "icmp_ping_sweep", "tcp_port_scan", "udp_sweep"]
```

---

## C-002: StepRecord.detected=False when no alert; reward=-0.1 (no progress case)

**Story**: US1  
**Rationale**: Verifies StepRecord.detected=False routes to REWARD_STALL (-0.1) when stage_progress=False.

Setup: pre-complete parent + siblings so the one remaining available action is terminal.

```python
# icmp_ping_sweep completed → ssh_version_probe becomes reachable but is terminal (no edges)
# Also complete all other entry points to eliminate other choices
state = EpisodeState(completed_actions=_ALL_IDS - {"ssh_version_probe"})
result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=1)
step = result.steps[0]
assert step.action_id == "ssh_version_probe"
assert step.detected == False
assert step.stage_progress == False
assert step.reward == -0.1
```

---

## C-003: StepRecord.detected=True, reward=-1.0 when alert fires

**Story**: US1  
**Rationale**: Verifies detection penalty regardless of stage_progress.

```python
state = EpisodeState(completed_actions=_ALL_IDS - {"ssh_version_probe"})
result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=True), max_steps=1)
step = result.steps[0]
assert step.detected == True
assert step.reward == -1.0
```

---

## C-004: StepRecord.stage_progress=True for an entry-point action that unlocks successors

**Story**: US1  
**Rationale**: Verifies stage_progress=True when completing an action that unlocks new reachable nodes.

```python
# Fresh state: tcp_port_scan is an entry point with 4 successors
state = EpisodeState()
selector = lambda available, state: "tcp_port_scan"
result = run_episode(state, selector, _EXECUTE, StubDefence(alert=False), max_steps=1)
assert result.steps[0].stage_progress == True
assert result.steps[0].reward == 1.0
```

---

## C-005: EpisodeState mutated — step, completed_actions, alert_history updated

**Story**: US1  
**Rationale**: Verifies in-place mutation of the caller's episode_state.

```python
state = EpisodeState()
assert state.step == 0
run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=1)
assert state.step == 1
assert len(state.alert_history) == 1
assert len(state.completed_actions) == 1
```

---

## C-006: completed=True and exactly 1 step when final action is terminal

**Story**: US2  
**Rationale**: Verifies episode terminates with completed=True when the last available action has no successors.

```python
# Pre-complete all except ssh_version_probe (terminal — no outgoing edges)
state = EpisodeState(completed_actions=_ALL_IDS - {"ssh_version_probe"})
result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False))
assert result.completed == True
assert len(result.steps) == 1
```

---

## C-007: completed=True and 0 steps when pre-completed state has no available actions

**Story**: US2  
**Rationale**: Tests immediate termination when all actions already completed on entry.

```python
state = EpisodeState(completed_actions=set(_ALL_IDS))
result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False))
assert result.completed == True
assert result.steps == []
assert result.total_reward == 0.0
```

---

## C-008: completed=False and exactly max_steps steps when step limit reached

**Story**: US3  
**Rationale**: Verifies step-limit termination with completed=False.

```python
state = EpisodeState()
result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=3)
assert result.completed == False
assert len(result.steps) == 3
```

---

## C-009: FR-003 — no-actions check wins over step-limit when both conditions true simultaneously

**Story**: US3  
**Rationale**: Critical priority ordering test. Both conditions true: no available actions AND step >= max_steps.

```python
# All actions completed, step already at max_steps limit
state = EpisodeState(completed_actions=set(_ALL_IDS), step=5)
result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=5)
assert result.completed == True   # no-actions wins → completed=True, NOT False
assert result.steps == []
```

---

## C-010: max_steps=0 — 0 steps executed, completed=False

**Story**: US3  
**Rationale**: Verifies step-limit check triggers before any step executes.

```python
state = EpisodeState()
result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=0)
assert result.completed == False
assert result.steps == []
assert result.total_reward == 0.0
```

---

## C-011: total_reward is arithmetic sum of step rewards

**Story**: US4  
**Rationale**: Verifies accumulation correctness. Expected: -1.0 + 1.0 + (-0.1) = -0.1 (abs tolerance < 1e-9).

```python
# Step 1: alert → -1.0; Step 2: no alert + progress → +1.0; Step 3: no alert, no progress → -0.1
# Engineer via toggling StubDefence alert per step:
rewards_seen = []
original_observe = StubDefence.observe

call_count = 0
class CountingDefence(Defence):
    def observe(self, action: Action) -> DetectionResult:
        nonlocal call_count
        call_count += 1
        alerted = call_count == 1  # only first step alerts
        return DetectionResult(alerted=alerted, rule_ids=[], anomaly_score=0.0, coverage="unknown")

state = EpisodeState()
# Selector: step 1→tcp_port_scan (progress), step 2→dns_subdomain_enum (progress), step 3→icmp_ping_sweep (progress)
steps_order = ["tcp_port_scan", "dns_subdomain_enum", "icmp_ping_sweep"]
i = 0
def seq_selector(available, s):
    nonlocal i
    choice = steps_order[i]; i += 1; return choice

result = run_episode(state, seq_selector, _EXECUTE, CountingDefence(), max_steps=3)
assert len(result.steps) == 3
# step 1: detected=True → -1.0; steps 2,3: detected=False + progress → +1.0 each
assert abs(result.total_reward - (-1.0 + 1.0 + 1.0)) < 1e-9
```

---

## C-012: episode_state.step == len(result.steps) after any episode

**Story**: US4  
**Rationale**: Verifies state.step is exactly incremented once per step (via collect_feedback), matches steps list length.

```python
state = EpisodeState()
result = run_episode(state, _SELECTOR, _EXECUTE, StubDefence(alert=False), max_steps=4)
assert state.step == len(result.steps)
```
