# Feature Specification: Defanged Action Library

**Feature Branch**: `010-e2-action-library`
**Created**: 2026-07-06
**Status**: Draft
**Input**: F07 (Epic E2 — Attack Surface) — ≥15 defanged attack actions across scan, brute-force, SSH, web, DNS, exfiltration categories

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Action Registry (Priority: P1)

The attacker agent needs to enumerate all available techniques so it can make an informed choice at each decision step. As a consumer of this library, the agent calls a single registry lookup and receives a complete, typed list of actions it can choose from — without knowing implementation details.

**Why this priority**: The registry is the entry point for every downstream component. Without it F08 (executor), F09 (graph), and F17 (attacker) cannot reference actions by stable identifier.

**Independent Test**: Import the action registry, call `list_actions()`, and assert ≥15 entries are returned, each with a non-empty `action_id`, `category`, and `parameters` dict.

**Acceptance Scenarios**:

1. **Given** the action library is imported, **When** the registry is queried for all actions, **Then** ≥15 distinct actions are returned with unique `action_id` values.
2. **Given** the registry, **When** an action is looked up by `action_id`, **Then** the returned object matches the `Action` data contract.
3. **Given** the registry, **When** actions are filtered by category, **Then** at least one action exists in each of: `scan`, `brute`, `ssh`, `web`, `dns`, `exfil`.

---

### User Story 2 — Parameterised Behaviour Descriptions (Priority: P2)

Each action must be tunable (rate, timing, volume, port) so the attacker can explore threshold-evasion behaviour. A researcher examining the library can read an action's description and immediately understand which detection rule category it exercises and what parameters control its intensity.

**Why this priority**: Parameterisation is what separates an action library from a static list — it enables the adaptive attacker to vary technique intensity as part of its strategy.

**Independent Test**: For every registered action, assert that `parameters` is non-empty and contains at least one tunable key; assert that a human-readable `description` field is present.

**Acceptance Scenarios**:

1. **Given** a scan action, **When** its parameters are inspected, **Then** tunables such as port range, rate (packets/sec), and timing offset are present.
2. **Given** a brute-force action, **When** its parameters are inspected, **Then** attempt count and inter-attempt delay are tunable.
3. **Given** any action, **When** its description is read, **Then** it states the simulated behaviour and the Suricata rule category it exercises.

---

### User Story 3 — Safety Guard (Priority: P3)

A security reviewer or CI pipeline can run a structural check over the entire library and get a pass/fail result confirming that no action definition contains real exploit logic, references external addresses, or performs network I/O at import time.

**Why this priority**: Safety is non-negotiable (Constitution Principle I). The guard must be automated so it cannot be bypassed by accident.

**Independent Test**: Run the guard function against all registered actions; assert it returns no violations. Inject a fake action referencing an external IP (`8.8.8.8`) and assert the guard flags it.

**Acceptance Scenarios**:

1. **Given** all registered actions, **When** the safety guard is run, **Then** zero violations are reported.
2. **Given** a crafted action whose parameters reference a public IP address, **When** the safety guard is run, **Then** it reports at least one violation for that action.
3. **Given** the library module is imported, **When** import completes, **Then** no network socket is opened and no subprocess is spawned.

---

### Edge Cases

- What happens when two actions share the same `action_id`? — Registry construction must raise immediately on duplicate IDs.
- What happens when `parameters` is an empty dict? — The guard treats an action with no parameters as structurally invalid (no tunables = no threshold-evasion capability).
- What if a parameter value is a non-lab IP string (e.g. `"8.8.8.8"`)? — The guard must flag any string value matching a publicly routable address pattern.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The library MUST expose a registry containing ≥15 defanged attack actions at import time.
- **FR-002**: Each action MUST have a globally unique `action_id` string, a `category` string (one of `scan`, `brute`, `ssh`, `web`, `dns`, `exfil`), and a non-empty `parameters` dict of tunables.
- **FR-003**: Each action MUST include a `description` field stating the simulated behaviour and the Suricata rule category it exercises.
- **FR-004**: The registry MUST be queryable by `action_id` (exact lookup) and by `category` (filter).
- **FR-005**: All action definitions MUST reference only lab-internal address space (`172.28.0.0/16`); any action referencing a publicly routable address MUST cause the safety guard to fail.
- **FR-006**: The library MUST perform no network I/O, subprocess execution, or file I/O at import or action-definition time.
- **FR-007**: A safety guard function MUST scan all registered actions and return a list of violations (empty list = pass); it MUST detect external IP references and reserved dangerous parameter patterns.
- **FR-008**: The registry MUST raise on duplicate `action_id` at construction time.
- **FR-009**: Actions MUST be pure data / factory output — no executable payloads, no real credentials, no destructive operations.

### Key Entities

- **ActionDefinition**: A named, categorised, parameterised description of one defanged technique. Fields: `action_id`, `category`, `description`, `default_parameters` (dict of tunable name → default value), `suricata_category` (the ET Open rule category it targets).
- **ActionRegistry**: The module-level catalogue mapping `action_id → ActionDefinition`. Provides `list_actions()`, `get_action(action_id)`, and `actions_by_category(category)`.
- **SafetyViolation**: A record emitted by the guard: `action_id`, `field`, `reason`. Zero violations = pass.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The registry contains ≥15 actions covering all six categories — verified by automated test, 0 failures.
- **SC-002**: Every action passes structural validity (unique ID, non-empty parameters, description present) — 0 structural failures.
- **SC-003**: The safety guard reports 0 violations against the full registered library.
- **SC-004**: A crafted action with a public IP in its parameters is flagged by the guard — guard detection rate is 100% on known-bad inputs.
- **SC-005**: Importing the library completes in under 1 second with no network activity detected.

## Assumptions

- The existing `Action` Pydantic model in `src/aatf/contracts.py` is the canonical data contract; `ActionDefinition` produces instances compatible with that model.
- "Lab-internal" means the `172.28.0.0/16` subnet defined in the Docker Compose network; no other address space is valid for action targets.
- Phase 1 requires only the action definitions and registry — actual traffic emission is entirely F08's responsibility.
- Six categories (scan, brute, ssh, web, dns, exfil) cover the technique families from the project proposal §7; additional categories may be added in later features without breaking this library.

## Dependencies

- **F03** (`src/aatf/contracts.py`) — `Action` model already implemented; this feature produces instances of that model.
- No new pip dependencies — stdlib only (`ipaddress` for IP validation in the guard).
