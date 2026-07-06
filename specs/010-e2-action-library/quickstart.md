# Quickstart: Defanged Action Library (F07)

## Enumerate all actions

```python
from aatf.action_library import REGISTRY

for action_def in REGISTRY.list_actions():
    print(action_def.action_id, action_def.category)
# tcp_port_scan scan
# udp_sweep scan
# ... (≥15 total)
```

## Look up a specific action

```python
defn = REGISTRY.get_action("ssh_brute_force")
print(defn.description)
# "Simulates SSH brute-force login attempts at configurable rate..."
print(defn.suricata_category)
# "ET BRUTE_FORCE"
print(defn.default_parameters)
# {"target_ip": "172.28.0.2", "attempts": 10, "interval_ms": 500, "username": "root"}
```

## Filter by category

```python
scan_actions = REGISTRY.actions_by_category("scan")
assert len(scan_actions) >= 3
```

## Convert to Action (wire format for F08 executor)

```python
from datetime import UTC, datetime
from aatf.action_library import REGISTRY

defn = REGISTRY.get_action("tcp_port_scan")
action = defn.to_action(timestamp=datetime.now(UTC))
# action is a fully-validated aatf.contracts.Action instance
print(action.action_id)   # "tcp_port_scan"
print(action.parameters)  # {"target_ip": "172.28.0.2", "port_range": "1-1024", ...}
```

## Run the safety guard

```python
from aatf.action_library import REGISTRY, safety_guard

violations = safety_guard(REGISTRY)
assert violations == [], f"Safety violations found: {violations}"
```

## Integration scenario: attacker agent selects an action

```python
import random
from datetime import UTC, datetime
from aatf.action_library import REGISTRY

rng = random.Random(42)  # seeded for reproducibility
all_actions = REGISTRY.list_actions()
chosen_defn = rng.choice(all_actions)
action = chosen_defn.to_action(timestamp=datetime.now(UTC))
# Pass action to F08 executor
```

## What F07 does NOT do

- **No traffic emission** — that is F08's job. ActionDefinition describes behaviour; it does not execute it.
- **No attack graph staging** — which actions are available at each stage is F09's concern.
- **No reward or feedback** — detection results and rewards are F14/F15.
