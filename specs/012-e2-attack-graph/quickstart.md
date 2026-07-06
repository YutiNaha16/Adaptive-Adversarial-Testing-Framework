# Quickstart: Attack Graph Staging (F09)

## Basic usage — get available actions at experiment start

```python
from aatf.attack_graph import ATTACK_GRAPH

# No actions completed yet — returns the 4 entry points
available = ATTACK_GRAPH.available_actions(set())
print(available)
# ['dns_subdomain_enum', 'icmp_ping_sweep', 'tcp_port_scan', 'udp_sweep']
```

## After completing a reconnaissance action

```python
# Attacker just ran tcp_port_scan successfully
completed = {"tcp_port_scan"}
available = ATTACK_GRAPH.available_actions(completed)
print(available)
# ['dns_subdomain_enum', 'ftp_brute_force', 'http_dir_scan',
#  'icmp_ping_sweep', 'ssh_brute_force', 'ssh_user_enum',
#  'tcp_port_scan', 'udp_sweep']
```

## Typical experiment loop integration

```python
from aatf.attack_graph import ATTACK_GRAPH
from aatf.action_library import REGISTRY
from aatf.action_executor import ActionExecutor
from datetime import UTC, datetime

executor = ActionExecutor(seed=42)
completed: set[str] = set()

for step in range(10):
    # Ask the graph which actions are currently available
    candidates = ATTACK_GRAPH.available_actions(completed)

    # Attacker policy picks one (e.g. random, LinUCB — to be added in E4)
    import random
    action_id = random.choice(candidates)

    defn = REGISTRY.get_action(action_id)
    action = defn.to_action(datetime.now(UTC))
    result = executor.execute(action)

    if result.success:
        completed.add(action_id)

    print(f"Step {step}: {action_id} → success={result.success}, "
          f"available={len(candidates)}")
```

## Full coverage — all 15 actions unlocked

```python
all_ids = {defn.action_id for defn in REGISTRY.list_actions()}
available = ATTACK_GRAPH.available_actions(all_ids)
assert set(available) == all_ids  # True — no action is an island
```

## What F09 does NOT do

- **No execution** — which actions to run is F08's job.
- **No detection** — whether Suricata fired is F10–F11's job.
- **No policy** — which available action to pick is the attacker brain's job (E4, LinUCB).
- **No reward** — reward computation is F14's job.
