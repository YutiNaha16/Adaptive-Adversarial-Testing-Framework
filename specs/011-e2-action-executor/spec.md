# Feature Specification: Action Executor

**Feature Branch**: `011-e2-action-executor`
**Created**: 2026-07-06
**Status**: Draft
**Input**: F08 (Epic E2 — Attack Surface) — translate abstract Actions into harmless, lab-only network traffic

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Traffic Emission (Priority: P1)

The experiment loop hands the executor an Action and the executor emits network traffic shaped to resemble the described technique against the lab target. The traffic is harmless but recognisable enough for Suricata rules to fire. Each of the 15 action categories (scan, brute, ssh, web, dns, exfil) has a dedicated handler.

**Why this priority**: Without traffic emission the experiment loop cannot generate detection signals. This is the core value of the executor — connecting the abstract action library to real observable behaviour on the lab network.

**Independent Test**: Monkeypatch the network layer; call `executor.execute(action)` for one action from each category; assert an `ExecutionResult` is returned, `emitted_count >= 1`, and no real socket is opened.

**Acceptance Scenarios**:

1. **Given** a valid Action with `target_ip = "172.28.0.2"`, **When** `executor.execute(action)` is called, **Then** an `ExecutionResult` is returned with `success=True` and `emitted_count >= 1`.
2. **Given** a scan action, **When** executed, **Then** the handler emits TCP connection attempts shaped to resemble a port scan.
3. **Given** a brute action, **When** executed, **Then** the handler emits repeated connection attempts shaped to resemble credential stuffing.
4. **Given** any action, **When** execution completes, **Then** `ExecutionResult.category` matches the Action's category.

---

### User Story 2 — Internal-Target Guard (Priority: P2)

Before emitting any traffic, the executor checks that the target IP is within the lab-internal address space. If the target is externally routable, the executor raises immediately and emits nothing. This enforces Constitution Principle I structurally.

**Why this priority**: Safety is non-negotiable. The guard must be a hard structural barrier, not a convention. It protects the lab from accidentally reaching external systems.

**Independent Test**: Call `executor.execute(action_with_external_ip)`; assert `ExternalTargetError` is raised and no network call was attempted.

**Acceptance Scenarios**:

1. **Given** an Action with `target_ip = "8.8.8.8"`, **When** `executor.execute(action)` is called, **Then** `ExternalTargetError` is raised before any traffic is emitted.
2. **Given** an Action with `target_ip = "172.28.0.2"` (lab-internal), **When** executed, **Then** no error is raised and traffic is emitted.
3. **Given** an Action with no `target_ip` parameter, **When** executed, **Then** the executor treats the absence as safe and proceeds (target defaults to lab address).

---

### User Story 3 — Deterministic Execution Under Seed (Priority: P3)

Any timing jitter introduced between packets/requests is drawn from a seeded random source. Given the same seed and the same Action, two calls to the executor produce identical `emitted_count` and timing sequences, enabling reproducible experiments.

**Why this priority**: Constitution Principle II requires determinism. Without seeded jitter the experiment is not reproducible, which invalidates every downstream metric.

**Independent Test**: Construct two executors with the same seed; execute the same Action on each; assert `ExecutionResult.emitted_count` and the captured timing sequence are identical.

**Acceptance Scenarios**:

1. **Given** two executors initialised with seed `42`, **When** both execute the same Action, **Then** both return `ExecutionResult` with identical `emitted_count`.
2. **Given** an executor with seed `42` re-used across two calls to the same Action, **Then** both calls produce the same `emitted_count`.
3. **Given** two executors with different seeds, **When** executing the same Action, **Then** the timing jitter sequences may differ (seeds are respected).

---

### Edge Cases

- What if `target_ip` is a private but non-lab address (e.g. `192.168.1.1`)? — The guard only permits `172.28.0.0/16`; all other addresses including other RFC-1918 ranges raise `ExternalTargetError`.
- What if the network call times out or is refused during integration? — `ExecutionResult.success = False` with a non-zero `emitted_count` reflecting partial emission; the executor does not raise on connection refusal.
- What if an action category has no registered handler? — `ExecutionResult.success = False`, `emitted_count = 0`, error message identifies the missing handler.
- What if `emitted_count` would be zero (e.g. rate=0)? — The handler must emit at least 1 probe; rate=0 is treated as rate=1.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The executor MUST accept an `Action` and return an `ExecutionResult` for every registered action category.
- **FR-002**: The executor MUST check `target_ip` against `172.28.0.0/16` before emitting any traffic; addresses outside this range MUST raise `ExternalTargetError` immediately with no traffic emitted.
- **FR-003**: Each of the 15 action categories MUST have a dedicated handler that emits traffic shaped to resemble the technique.
- **FR-004**: Timing jitter between packets/requests MUST be drawn from a seeded random source injected at construction time.
- **FR-005**: Two executors with the same seed executing the same Action MUST produce identical `ExecutionResult.emitted_count`.
- **FR-006**: `ExecutionResult` MUST contain: `success` (bool), `emitted_count` (int ≥ 0), `category` (str), `action_id` (str), `error` (str | None).
- **FR-007**: The executor MUST NOT open any real network socket during unit tests — the network layer MUST be injectable/monkeypatchable.
- **FR-008**: The executor MUST emit at least 1 probe per execution; a configured rate of 0 is silently promoted to 1.
- **FR-009**: No real exploit payloads, real credentials, or destructive operations may appear anywhere in executor code or tests.

### Key Entities

- **ActionExecutor**: The main class. Constructed with a seed. Exposes `execute(action: Action) -> ExecutionResult`. Holds a seeded random source and a registry of per-category handlers.
- **ExecutionResult**: The return value of `execute()`. Fields: `action_id`, `category`, `success`, `emitted_count`, `error`.
- **ExternalTargetError**: Exception raised when `target_ip` is outside `172.28.0.0/16`. Signals the fail-closed behaviour.
- **Handler**: A callable `(action: Action, rng: Random) -> int` that emits traffic for one category and returns the count of probes sent.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 15 action categories execute without error against a monkeypatched network layer — 0 handler failures in unit tests.
- **SC-002**: `ExternalTargetError` is raised for 100% of actions targeting addresses outside `172.28.0.0/16` — guard detection rate is 100% on known-bad inputs.
- **SC-003**: Two executors with the same seed produce identical `emitted_count` for the same Action — determinism verified by automated test.
- **SC-004**: Unit test suite runs without opening any real network socket — verified by monkeypatching.
- **SC-005**: Integration test (lab running) confirms at least one Suricata alert fires after executing a scan or brute action — verified by checking `eve.json` after execution.

## Assumptions

- The lab defender IP is always `172.28.0.2`; all action `default_parameters` from F07 use this address.
- "Shaped to resemble" means the traffic pattern (connection count, destination port, payload strings) is recognisable to ET Open rules — not that it carries a real exploit. A TCP port scan sends real TCP SYN packets to the target; a SQLi probe sends an HTTP request with a recognisable payload string.
- The executor runs inside the `aatf-attacker` container in integration; in unit tests it runs on the host with a monkeypatched socket layer.
- Timing jitter is applied between repeated probes (e.g. between brute-force attempts); single-probe actions (e.g. `ssh_version_probe`) have no jitter.

## Dependencies

- **F07** (`src/aatf/action_library.py`) — `Action` contract and category names already defined.
- **F03** (`src/aatf/contracts.py`) — `Action` model already in place.
- **F04** (Docker lab) — lab network `172.28.0.0/16` is the only valid target space.
- No new pip dependencies — stdlib only (`socket`, `http.client`, `random`, `ipaddress`).
