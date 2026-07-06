# Feature Specification: Attack Graph Staging

**Feature Branch**: `012-e2-attack-graph`
**Created**: 2026-07-06
**Status**: Draft
**Input**: F09 (Epic E2 — Attack Surface) — directed attack graph modelling which actions become available after prior actions succeed

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Entry-Point Actions Always Available (Priority: P1)

The experiment loop needs to know which actions to offer at the very start of a campaign, before anything has been executed. A fixed set of "entry-point" actions requires no prerequisites and is always reachable — the loop can pick any of them to begin.

**Why this priority**: Without a defined starting set the experiment loop cannot begin. This is the simplest slice and unlocks every downstream story.

**Independent Test**: Call `available_actions(completed=set())` on the module-level graph constant; assert the returned list contains exactly the four entry-point action_ids (`tcp_port_scan`, `udp_sweep`, `icmp_ping_sweep`, `dns_subdomain_enum`) and nothing else.

**Acceptance Scenarios**:

1. **Given** no actions have been completed, **When** `available_actions(set())` is called, **Then** the four entry-point action_ids are returned.
2. **Given** no actions have been completed, **When** `available_actions(set())` is called, **Then** no non-entry-point action_id appears in the result.
3. **Given** the module is imported, **When** the module-level `ATTACK_GRAPH` constant is accessed, **Then** it is available without any instantiation call.

---

### User Story 2 — Completing Actions Unlocks Successors (Priority: P2)

After the executor runs an action successfully, the experiment loop passes the updated completed set to `available_actions`. The graph returns all currently reachable actions — the original entry points plus any actions that have been unlocked by prior completions. This models a realistic multi-stage campaign where early reconnaissance opens doors to targeted exploitation.

**Why this priority**: This is the core value of the attack graph. Without it the graph is just a static list.

**Independent Test**: Complete `tcp_port_scan` (an entry-point); call `available_actions({"tcp_port_scan"})`; assert that at least `ssh_brute_force` and `http_dir_scan` appear in the result in addition to the four entry-points.

**Acceptance Scenarios**:

1. **Given** `tcp_port_scan` has been completed, **When** `available_actions` is called, **Then** `ssh_brute_force` and `http_dir_scan` are in the result.
2. **Given** `dns_subdomain_enum` has been completed, **When** `available_actions` is called, **Then** `dns_zone_transfer` is in the result.
3. **Given** `http_sqli_probe` has been completed, **When** `available_actions` is called, **Then** `http_exfil` is in the result.
4. **Given** `dns_zone_transfer` has been completed, **When** `available_actions` is called, **Then** `dns_exfil` is in the result.
5. **Given** an action is completed whose successors were already available, **When** `available_actions` is called, **Then** the result is a superset of the previous result (no actions are removed).

---

### User Story 3 — Full Graph Coverage (Priority: P3)

After the experiment loop has completed all 15 actions, `available_actions` returns all 15 action_ids. No registered action is unreachable from the graph — every action_id in the F07 registry appears at least once (either as an entry point or as a successor to some other action).

**Why this priority**: Ensures completeness — the graph cannot accidentally omit an action, which would make that technique permanently unavailable to the experiment loop.

**Independent Test**: Pass the full set of 15 action_ids to `available_actions`; assert the result set equals the full set from `REGISTRY.list_actions()`.

**Acceptance Scenarios**:

1. **Given** all 15 actions have been completed, **When** `available_actions` is called, **Then** all 15 action_ids are returned.
2. **Given** the graph is imported, **When** every action_id in the graph (nodes and edges) is cross-checked against `REGISTRY`, **Then** no unknown action_id appears.
3. **Given** every action_id in `REGISTRY`, **When** the reachable set from the entry points (following all edges) is computed, **Then** it equals the full registry set — no action is permanently unreachable.

---

### Edge Cases

- What if `completed` contains an action_id not in the graph? — `available_actions` ignores unknown ids silently; it does not raise.
- What if `completed` is the empty set? — Returns only entry-point actions (same as US1 baseline).
- What if `completed` contains all 15 action_ids? — Returns all 15 (same as US3 full coverage).
- What if the graph topology creates a cycle (A unlocks B, B unlocks A)? — `available_actions` must still terminate; it computes reachability without following cycles indefinitely.
- What if an action's successor is already an entry point? — The action still appears in the result regardless of whether its unlock-parent was completed; no double-counting or removal occurs.
- What if `available_actions` is called multiple times with the same input? — Must return identical results every call (no hidden mutable state).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The module MUST expose a module-level constant `ATTACK_GRAPH` of type `AttackGraph` that is constructed at import time without any instantiation call from the caller.
- **FR-002**: `AttackGraph` MUST store a set of entry-point action_ids (actions with no prerequisites) and a mapping of action_id → set of successor action_ids (the unlock edges).
- **FR-003**: `AttackGraph` MUST provide `available_actions(completed: set[str]) -> list[str]` that returns all action_ids that are either entry-points or are a direct successor of any action_id in `completed`.
- **FR-004**: `available_actions` MUST return a deterministic result for the same input — the set of returned ids must be identical across calls (list ordering may vary).
- **FR-005**: All action_ids referenced in `ATTACK_GRAPH` (as entry points or successor targets) MUST exist in `REGISTRY`; the module MUST raise `ValueError` at import time if an unknown action_id is referenced.
- **FR-006**: Every action_id in `REGISTRY` MUST be reachable from the entry points by following the graph edges — no registered action may be permanently unreachable.
- **FR-007**: `available_actions` MUST be non-destructive — calling it must not modify the graph or any internal state.
- **FR-008**: No filesystem I/O, network calls, or subprocess calls are permitted anywhere in the module.

### Key Entities

- **AttackGraph**: The main data structure. Holds entry-point action_ids and a directed edge mapping (action_id → set of action_ids it unlocks). Provides `available_actions(completed: set[str]) -> list[str]`.
- **Entry point**: An action_id that is always available regardless of completion state. The four entry points are: `tcp_port_scan`, `udp_sweep`, `icmp_ping_sweep`, `dns_subdomain_enum`.
- **Edge**: A directed unlock relationship meaning "completing action A makes action B available". An action_id may have zero or more outgoing edges.
- **ATTACK_GRAPH**: Module-level constant of type `AttackGraph`; constructed and validated against `REGISTRY` at import time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `available_actions(set())` returns exactly the 4 entry-point action_ids — verified by automated test.
- **SC-002**: `available_actions({"tcp_port_scan"})` returns a superset of entry-points including at least `ssh_brute_force` and `http_dir_scan` — verified by automated test.
- **SC-003**: `available_actions` with all 15 action_ids returns all 15 — 100% graph coverage verified by automated test.
- **SC-004**: Every action_id in the graph exists in `REGISTRY` — 0 unknown references, verified at import time.
- **SC-005**: Module imports in under 100 ms on the host machine — no I/O at import time.

## Assumptions

- "Completing" an action means the experiment loop received a successful `ExecutionResult` (F08) and added that `action_id` to the `completed` set. The graph does not evaluate success itself — it is purely topological.
- `available_actions` returns all entry-points PLUS all direct successors of any action in `completed`. It does NOT require the full transitive prerequisite chain — completing action B is sufficient to unlock B's successors even if B was itself a successor of A and A was not completed. This simulates an adversary who finds a shortcut.
- The canonical v1 unlock topology (all 15 actions covered, no islands):
  - Entry points (no prerequisites): `tcp_port_scan`, `udp_sweep`, `icmp_ping_sweep`, `dns_subdomain_enum`
  - `tcp_port_scan` → `ssh_brute_force`, `ftp_brute_force`, `http_dir_scan`, `ssh_user_enum`
  - `udp_sweep` → `dns_zone_transfer`
  - `icmp_ping_sweep` → `ssh_version_probe`
  - `dns_subdomain_enum` → `dns_zone_transfer`
  - `ssh_brute_force` → `ssh_version_probe`
  - `http_dir_scan` → `http_sqli_probe`, `http_xss_probe`, `http_basic_brute`
  - `http_sqli_probe` → `http_exfil`
  - `dns_zone_transfer` → `dns_exfil`
- The graph may contain redundant paths (e.g., `dns_zone_transfer` reachable from both `udp_sweep` and `dns_subdomain_enum`); this is intentional and acceptable.

## Dependencies

- **F07** (`src/aatf/action_library.py`) — `REGISTRY` used at import time to validate all action_ids in the graph.
- No dependency on F08 (`ActionExecutor`) — the graph is pure topology with no execution semantics.
- No new pip dependencies — stdlib only (`dataclasses`, `collections.abc`).
