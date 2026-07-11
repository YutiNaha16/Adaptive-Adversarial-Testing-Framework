# Quickstart: Attacker Interface + Baselines (F18)

**Date**: 2026-07-11
**Feature**: 018-e5-attacker-baselines

## Minimal working examples

### RandomAttacker

```python
import numpy as np
from aatf.attacker import RandomAttacker

attacker = RandomAttacker(seed=0)
available = ["tcp_port_scan", "udp_sweep", "dns_subdomain_enum"]
ctx = np.zeros(50)  # real context from build_context(); zeros for illustration

action = attacker.choose_action(available, ctx)
print(f"Chose: {action}")

# After seeing the reward:
attacker.observe(action, ctx, reward=-1.0)  # no-op for RandomAttacker
```

### FixedScriptAttacker

```python
from aatf.attacker import FixedScriptAttacker

# Explicit script:
attacker = FixedScriptAttacker(script=["icmp_ping_sweep", "tcp_port_scan"])

# Or let it default to alphabetical on first call:
attacker = FixedScriptAttacker()
```

### LinUCBAttacker (production adaptive attacker)

```python
import time
import numpy as np
from aatf.attacker import LinUCBAttacker
from aatf.linucb import LinUCBModel
from aatf.context_vector import EpisodeState, build_context, CONTEXT_DIM

model = LinUCBModel(d=CONTEXT_DIM, alpha=1.0)
attacker = LinUCBAttacker(model)

state = EpisodeState()
ctx = build_context(state, current_time=time.time()).astype(float)
available = ["tcp_port_scan", "udp_sweep", "dns_subdomain_enum"]

action = attacker.choose_action(available, ctx)
# ... execute action, collect reward ...
attacker.observe(action, ctx, reward=1.0)  # updates model._arms
```

## Swapping implementations

```python
from aatf.attacker import Attacker, RandomAttacker, FixedScriptAttacker, LinUCBAttacker
from aatf.linucb import LinUCBModel

def run_one_step(attacker: Attacker, available, ctx):
    action = attacker.choose_action(available, ctx)
    # ... execute, get reward ...
    reward = 0.5
    attacker.observe(action, ctx, reward)
    return action

# Drop-in swap — no change to run_one_step:
run_one_step(RandomAttacker(seed=42), ["a", "b"], np.zeros(50))
run_one_step(FixedScriptAttacker(), ["a", "b"], np.zeros(50))
run_one_step(LinUCBAttacker(LinUCBModel(d=50)), ["a", "b"], np.zeros(50))
```

## Wiring with run_episode() (F20+)

```python
# F20 will wire action_selector to an Attacker. Sketch:
import time
from aatf.context_vector import build_context

model = LinUCBModel(d=CONTEXT_DIM, alpha=1.0)
attacker = LinUCBAttacker(model)

def action_selector(available: list[str], episode_state) -> str:
    ctx = build_context(episode_state, current_time=time.time()).astype(float)
    return attacker.choose_action(available, ctx)
```

## Dependency map

```
Attacker (ABC)
  ├── RandomAttacker        — stdlib: random.Random
  ├── FixedScriptAttacker   — stdlib: itertools.cycle
  └── LinUCBAttacker        — aatf.linucb.LinUCBModel (spec-017)
                                   └── numpy
```
