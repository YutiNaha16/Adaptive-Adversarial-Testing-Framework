# Quickstart: LinUCB Attacker Update Rule (F17)

**Date**: 2026-07-10
**Feature**: 017-e4-attacker-update

## Minimal working example

```python
import numpy as np
import time
from aatf.linucb import LinUCBModel
from aatf.context_vector import EpisodeState, build_context

# Construct with the real context vector dimension (d=50)
model = LinUCBModel(d=50, alpha=1.0)

# Build a context from the current episode state
state = EpisodeState()
context = build_context(state, current_time=time.time()).astype(float)

# Select which action to take next
available = ["tcp_port_scan", "udp_sweep", "dns_subdomain_enum"]
chosen = model.select_action(available, context)
print(f"Selected: {chosen}")

# After the step, update with the observed reward
reward = 1.0  # e.g. undetected + progress
model.update(chosen, context, reward)

# Next episode: context will be different; model prefers better-rewarded actions
```

## Wiring with run_episode() (F20+)

```python
# F20 will wire this together; sketch only:
def my_selector(available: list[str], state: EpisodeState) -> str:
    ctx = build_context(state, current_time=time.time()).astype(float)
    return model.select_action(available, ctx)

# After each step in run_episode:
#   model.update(action_id, context, reward)
```

## Exploration vs Exploitation

| alpha | Behaviour |
|-------|-----------|
| 0.0   | Pure greedy — always exploits known-best action |
| 1.0   | Default — balanced; uncertainty bonus equals confidence |
| 2.0+  | Heavy exploration — prefers least-tried actions |

## Saving and restoring model state

```python
import json

# Save
state_dict = model.to_dict()
with open("linucb_state.json", "w") as f:
    json.dump(state_dict, f)

# Restore
with open("linucb_state.json") as f:
    state_dict = json.load(f)
restored = LinUCBModel.from_dict(state_dict)

# Restored model produces identical selections
assert model.select_action(available, context) == restored.select_action(available, context)
```

## Dependency map

```
LinUCBModel
  ├── d = len(build_context(...))     src/aatf/context_vector.py (F13)
  └── numpy: eye(), zeros(), outer()  (already in requirements)
```
