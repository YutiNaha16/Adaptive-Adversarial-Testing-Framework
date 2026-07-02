# Feature Specification: Isolation Verification

**Feature Branch**: `005-e1-isolation-verify`
**Created**: 2026-07-02
**Status**: Draft
**Input**: F06 from docs/backlog.md — Epic E1, Isolated Lab Environment

## Overview

F04 created the structural isolation (`internal: true` lab network). F06 makes that isolation
guarantee **machine-verifiable** — so no human needs to remember to run a manual check and CI
catches any misconfiguration automatically.

This feature has no experiment logic, no attacker, and no Suricata. It is purely the safety
proof layer required by Constitution Principle I: isolation MUST be provably enforced, not
just claimed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Structural Isolation Test in Standard Suite (Priority: P1)

A developer or CI pipeline runs the standard test suite (`make test`) and, without needing
Docker running, receives automated confirmation that the lab's network configuration
structurally blocks outbound traffic. The test reads the lab's network configuration and
asserts that the isolation property is declared and no experiment container exposes host
routes.

**Why this priority**: This is the minimum viable safety proof. It runs without Docker,
catches misconfiguration before anyone boots the lab, and is fully automated. Every CI run
validates the safety property — no separate step required.

**Independent Test**: Run `make test` on a machine without Docker installed; the suite passes
and includes at least one test that verifies the lab network configuration declares the
isolation property.

**Acceptance Scenarios**:

1. **Given** the standard test suite runs on any developer machine, **When** all tests
   execute, **Then** a test verifying the lab network declares `internal: true` passes
   with no Docker daemon required.
2. **Given** the lab network configuration has its isolation property removed,
   **When** the test suite runs, **Then** the structural isolation test fails, explicitly
   identifying the violated isolation requirement.
3. **Given** the lab network configuration is correct, **When** the test suite runs,
   **Then** the structural isolation test completes in under 1 second (no network I/O,
   no container startup).

---

### User Story 2 — Fail-Closed External Target Guard (Priority: P1)

Any code within the framework that attempts to direct traffic to an externally routable
address must be blocked at the code level — not just by the network. A validated guard
component raises and aborts whenever an external target is specified, so even a misconfigured
network would not result in real external traffic.

**Why this priority**: Constitution Principle I requires fail-closed behaviour AND a test
asserting it. This is the second layer of defence beyond network-level isolation — the guard
catches targeting mistakes before a packet is ever attempted.

**Independent Test**: Run `make test`; the suite includes tests that invoke the guard with
external addresses and confirm it raises, and with lab-internal addresses and confirm it passes.
No Docker required.

**Acceptance Scenarios**:

1. **Given** a request to target a publicly routable IP address, **When** the guard
   validates the target, **Then** it raises an error and aborts — no traffic is sent.
2. **Given** a request to target a public hostname, **When** the guard validates the
   target, **Then** it raises an error and aborts.
3. **Given** a request to target a lab-internal address (within the lab's declared subnet),
   **When** the guard validates the target, **Then** it passes without error.
4. **Given** a request to target loopback (`127.0.0.1`), **When** the guard validates the
   target, **Then** it passes without error (loopback is lab-safe).
5. **Given** a request targeting an RFC1918 address outside the lab subnet (e.g. a home
   router), **When** the guard validates the target, **Then** it raises — the guard rejects
   any address not in the declared lab subnet, including private ranges outside it.

---

### User Story 3 — Live Egress Probe in Automated Suite (Priority: P2)

When the Docker lab is available, an automated test actually attempts an outbound connection
from inside the network and asserts it is blocked at the network layer. This confirms that
the `internal: true` declaration is **enforced by the Docker runtime** — not just declared in
configuration.

**Why this priority**: US1 proves the configuration is correct; US3 proves the runtime
enforces it. US1 is sufficient for daily development CI; US3 provides the deeper guarantee
needed before releases or after Docker/network changes.

**Independent Test**: With the lab running (`make lab-up` already done), the automated live
egress test attempts an outbound connection from within the lab network and asserts it is
blocked.

**Acceptance Scenarios**:

1. **Given** the lab is running, **When** the live egress test runs, **Then** an attempted
   outbound connection to an external host is confirmed blocked and the test passes.
2. **Given** the lab is not running, **When** the live egress test runs, **Then** the test
   is skipped (not failed) with a clear skip message explaining that Docker lab is required.
3. **Given** the isolation property has been removed and the lab restarted,
   **When** the live egress test runs, **Then** it fails, detecting the active breach.

---

### Edge Cases

- What if the lab network configuration file is missing or malformed? The structural test
  (US1) must fail with a clear error message — not a cryptic parse exception.
- What if a target address is in an RFC1918 private range but outside the lab subnet (e.g.
  a home router at 192.168.1.1)? The guard (US2) must reject it — only the declared lab
  subnet is permitted, not all private ranges.
- What if IPv6 is used? The guard must reject externally routable IPv6 addresses; it may
  reject all IPv6 (safe default) until explicit IPv6 lab support is tested.
- What if the guard receives a hostname rather than an IP? The guard resolves the hostname
  to an IP and applies the same check — a resolvable external hostname is rejected.
- What if the lab is mid-start (containers exist but not yet running)? The live egress
  probe (US3) skips in this state with the same "lab not ready" message.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The standard automated test suite MUST include a test that verifies the lab
  network configuration structurally declares the isolation property, with no Docker
  daemon required to run it.
- **FR-002**: The structural isolation test MUST fail if the isolation property is absent
  or disabled in the lab network configuration, with an explicit failure message citing
  the violated requirement.
- **FR-003**: The system MUST provide a validated guard component that, given a target
  address or hostname, raises and aborts if the target is not within the declared lab
  subnet or loopback — before any network I/O occurs.
- **FR-004**: The fail-closed guard MUST be covered by automated tests asserting it raises
  on external targets and passes on lab-internal targets and loopback; these tests MUST
  run without Docker.
- **FR-005**: The guard MUST reject any address not explicitly within the declared lab
  subnet range, including RFC1918 ranges outside that subnet and all publicly routable
  addresses.
- **FR-006**: The test suite MUST include a live egress probe that, when the lab is
  running, confirms an outbound connection attempt from within the lab network is blocked
  at the network layer.
- **FR-007**: The live egress probe MUST skip gracefully (not fail) when the lab is not
  running, with a clear skip message; it MUST NOT cause `make test` to fail on a machine
  without Docker.
- **FR-008**: The structural isolation test and fail-closed guard tests MUST run as part
  of `make test` with no additional prerequisites beyond the base development environment.
- **FR-009**: All isolation tests that do not require Docker MUST complete in under 5
  seconds total.

### Key Entities

- **Lab Network Configuration**: The declarative definition of the experiment network,
  including the isolation property and subnet range. Owned by F04; read (not modified) by
  this feature.
- **External Target Guard**: The validation component that checks a target address against
  the permitted lab subnet and loopback, raising on any external or out-of-subnet address.
  Consumed by F08 (action executor) in a later feature.
- **Lab Subnet**: The declared internal IP range of the lab (from F04). The guard's
  allowlist.
- **Live Egress Probe**: An automated test that runs from inside the lab network and
  confirms an outbound connection is blocked at the network layer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of isolation-related tests that do not require Docker pass as part of
  `make test` — zero manual steps and no Docker daemon needed.
- **SC-002**: Any removal of the isolation property from the lab network configuration is
  detected automatically within the same `make test` run, with a failure message
  identifying the specific violated requirement.
- **SC-003**: The fail-closed guard tests cover at minimum: a public IP (raises), a public
  hostname (raises), an RFC1918 address outside the lab subnet (raises), a lab-internal
  address (passes), and loopback (passes) — all passing in `make test`.
- **SC-004**: The live egress probe, when run with the lab active, confirms network-layer
  blocking in under 10 seconds and reports a clear "blocked" result.
- **SC-005**: The total wall-clock time added to `make test` by the new isolation tests
  (excluding Docker-dependent tests) is under 5 seconds.

## Assumptions

- The lab network configuration from F04 (`lab/docker-compose.yml`) is the canonical
  source of truth; F06 reads it but does not own or modify it.
- The lab subnet is `172.28.0.0/16` as declared in F04; this is the guard's allowlist.
- The fail-closed guard provided here will be wired into the action executor (F08) in a
  later feature; F06 only creates and tests the guard as a standalone component.
- Loopback (`127.0.0.1`, `::1`) is lab-safe and the guard must not reject it.
- IPv6 external addresses are rejected by the guard as a safe default.
- The live egress probe (US3) reuses the logic of `lab/scripts/check-isolation.sh` rather
  than duplicating it.
- `make test` remains Docker-free after this feature; Docker-dependent tests are marked to
  skip when Docker is unavailable.

## Dependencies

- **F04** (`004-e1-docker-lab`): The lab network, isolation configuration, lab subnet, and
  `lab/scripts/check-isolation.sh` all come from F04. This feature reads F04 artifacts; it
  does not modify them.
- **Constitution Principle I**: US1 (structural test) and US2 (fail-closed guard with
  tests) directly implement the mandatory requirement: "Any code path that could send
  traffic to an externally routable address MUST fail closed (raise and abort), and MUST
  be covered by a test asserting it fails closed."
