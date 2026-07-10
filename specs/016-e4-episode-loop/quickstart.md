# Quickstart: Episode Loop (F16)

**Date**: 2026-07-10
**Feature**: 016-e4-episode-loop

## Minimal working example

```python
from aatf.context_vector import EpisodeState
from aatf.episode import run_episode
from aatf.defence import NullDefence

# NullDefence: always returns alerted=False, coverage="unknown"
defence = NullDefence()

# Action selector: always pick the first available action (alphabetical)
def greedy_selector(available: list[str], state: EpisodeState) -> str:
    return available[0]

# Execute no-op: lab not connected; for unit testing
def noop_execute(action_id: str) -> None:
    pass

state = EpisodeState()
result = run_episode(state, greedy_selector, noop_execute, defence, max_steps=10)

print(f"completed: {result.completed}, steps: {len(result.steps)}, total_reward: {result.total_reward}")
for step in result.steps:
    print(f"  {step.action_id}: detected={step.detected}, progress={step.stage_progress}, reward={step.reward}")
```

## Wiring in the real action executor (F11)

```python
from aatf.action_executor import execute_action  # F11

result = run_episode(state, my_selector, execute_action, defence, max_steps=50)
```

`execute_action(action_id: str) -> None` matches the expected `Callable[[str], None]` signature.

## Wiring in Suricata defence (F06/F03)

```python
from aatf.suricata_defence import SuricataDefence

defence = SuricataDefence(eve_path="/path/to/eve.json")
result = run_episode(state, my_selector, execute_action, defence, max_steps=50)
```

## Resuming a partial episode

```python
# Episode state persists; pass it back to continue from where it left off
state = EpisodeState()
partial = run_episode(state, my_selector, noop_execute, defence, max_steps=5)
# state is now mutated (5 steps in)
full = run_episode(state, my_selector, noop_execute, defence, max_steps=10)
# full picks up from step 5; terminates at 10 total steps or exhaustion
```

## Termination outcomes

| Condition at loop start                    | `completed` | `steps` length |
|--------------------------------------------|-------------|---------------|
| No available (uncompleted reachable) actions | `True`    | 0             |
| All actions exhausted mid-run              | `True`      | 1..N          |
| `max_steps=0` (no actions run)             | `False`     | 0             |
| `max_steps` reached before exhaustion      | `False`     | max_steps     |
| Both no-actions AND step≥limit (simultaneous) | `True`   | 0             |

## Dependency map

```
run_episode
  ├── REGISTRY.get_action()        src/aatf/action_library.py
  ├── Action(...)                  src/aatf/contracts.py
  ├── defence.observe(action)      src/aatf/defence.py  (Defence ABC)
  ├── collect_feedback(...)        src/aatf/feedback.py
  ├── compute_reward(...)          src/aatf/reward.py
  └── attack_graph.available_actions()  src/aatf/attack_graph.py
```
