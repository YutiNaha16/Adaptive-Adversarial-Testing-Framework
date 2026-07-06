# Action Executor Contracts (F08)

## C-001 — execute() returns ExecutionResult for every registered action

For every `action_id` in `REGISTRY.list_actions()`:
`isinstance(executor.execute(action), ExecutionResult)` is True.

---

## C-002 — success=True and emitted_count≥1 for valid lab-internal action

Given `action.parameters["target_ip"] = "172.28.0.2"` and a recording SendFn:
`result.success is True` and `result.emitted_count >= 1`.

---

## C-003 — ExternalTargetError raised for external IP

Given `action.parameters["target_ip"] = "8.8.8.8"`:
`executor.execute(action)` raises `ExternalTargetError`.

---

## C-004 — No traffic emitted before ExternalTargetError

Given a recording SendFn and `target_ip = "8.8.8.8"`:
After `ExternalTargetError` is raised, the recording SendFn call count is 0.

---

## C-005 — Private non-lab IP also raises ExternalTargetError

Given `target_ip = "192.168.1.1"` (RFC-1918 but not 172.28.0.0/16):
`executor.execute(action)` raises `ExternalTargetError`.

---

## C-006 — Same seed produces identical emitted_count

Given two `ActionExecutor(seed=42)` instances executing the same Action with recording SendFn:
`result_a.emitted_count == result_b.emitted_count`.

---

## C-007 — ExecutionResult fields match Action

`result.action_id == action.action_id` and `result.category == action.category`.

---

## C-008 — error is None on success

`result.success is True` implies `result.error is None`.

---

## C-009 — Unknown action_id returns failure result (does not raise)

Given an Action with `action_id = "unknown_action"`:
`result.success is False`, `result.emitted_count == 0`, `result.error` is not None.

---

## C-010 — rate=0 promoted to at least 1 probe

Given an Action with `parameters["attempts"] = 0` (brute action):
`result.emitted_count >= 1`.

---

## C-011 — all 15 action_ids have handlers

For every `action_id` in `REGISTRY.list_actions()`:
`executor.execute(action)` does NOT return `success=False` with "no handler" error.

---

## C-012 — No real socket opened in unit tests

With a recording SendFn injected:
`socket.socket` is never called during `execute()`.

---

## C-013 — ExecutionResult is a dataclass with required fields

`ExecutionResult` has fields: `action_id`, `category`, `success`, `emitted_count`, `error`.
`dataclasses.fields(ExecutionResult)` returns entries for all five.

---

## C-014 — ExternalTargetError is a subclass of ValueError

`issubclass(ExternalTargetError, ValueError)` is True.

---

## C-015 — Integration: scan action triggers Suricata alert (auto-skip)

Given the lab is running (`docker inspect aatf-attacker` returns 0):
Execute `tcp_port_scan` against `172.28.0.2`; wait 2 seconds;
check `eve.json` for at least one alert entry — `result.emitted_count >= 1`.
Skip if lab not running.
