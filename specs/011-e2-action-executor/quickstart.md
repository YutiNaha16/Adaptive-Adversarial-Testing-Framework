# Quickstart: Action Executor (F08)

## Basic usage — execute an action

```python
from datetime import UTC, datetime
from aatf.action_library import REGISTRY
from aatf.action_executor import ActionExecutor

executor = ActionExecutor(seed=42)
defn = REGISTRY.get_action("tcp_port_scan")
action = defn.to_action(timestamp=datetime.now(UTC))

result = executor.execute(action)
print(result.success)        # True
print(result.emitted_count)  # e.g. 1024 (one probe per port in range 1-1024)
print(result.category)       # "scan"
```

## Guard — external IP raises immediately

```python
from aatf.contracts import Action
from aatf.action_executor import ActionExecutor, ExternalTargetError
from datetime import UTC, datetime

executor = ActionExecutor(seed=42)
bad_action = Action(
    action_id="tcp_port_scan",
    category="scan",
    parameters={"target_ip": "8.8.8.8", "port_range": "80-80", "rate_pps": 1, "timing_ms": 0},
    timestamp=datetime.now(UTC),
)
try:
    executor.execute(bad_action)
except ExternalTargetError as e:
    print(e)  # "target_ip '8.8.8.8' is outside lab network 172.28.0.0/16"
```

## Unit test pattern — inject recording SendFn

```python
from aatf.action_executor import ActionExecutor

calls: list[tuple] = []

def recording_send(host: str, port: int, payload: bytes) -> None:
    calls.append((host, port, payload))

executor = ActionExecutor(seed=42, send_fn=recording_send, sleep_fn=lambda _: None)
result = executor.execute(action)
assert result.success
assert len(calls) >= 1
assert all(host == "172.28.0.2" for host, _, _ in calls)
```

## Determinism verification

```python
executor_a = ActionExecutor(seed=42, send_fn=recording_send, sleep_fn=lambda _: None)
executor_b = ActionExecutor(seed=42, send_fn=recording_send, sleep_fn=lambda _: None)

result_a = executor_a.execute(action)
result_b = executor_b.execute(action)
assert result_a.emitted_count == result_b.emitted_count
```

## Execute all 15 actions in sequence

```python
from aatf.action_library import REGISTRY
from aatf.action_executor import ActionExecutor
from datetime import UTC, datetime

executor = ActionExecutor(seed=0, send_fn=recording_send, sleep_fn=lambda _: None)
for defn in REGISTRY.list_actions():
    action = defn.to_action(datetime.now(UTC))
    result = executor.execute(action)
    assert result.success, f"{defn.action_id} failed: {result.error}"
```

## What F08 does NOT do

- **No detection** — whether Suricata fired is F11's job.
- **No reward** — reward computation is F14's job.
- **No attack graph** — which actions are available at each stage is F09's job.
