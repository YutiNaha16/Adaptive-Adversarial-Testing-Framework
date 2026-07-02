# Feature Specification: Internal-only Docker Lab

**Feature Branch**: `004-e1-docker-lab`
**Created**: 2026-07-02
**Status**: Draft
**Input**: F04 (Epic E1 — Isolated Lab Environment): Internal-only Docker Compose lab with no route to the public internet.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Lab Network Provisioning (Priority: P1)

A researcher can bring the isolated lab environment up and tear it down with a single command.
The lab runs on an internal-only network — no container inside it can reach the public internet.

**Why this priority**: Every subsequent feature (Suricata adapter, attacker, orchestrator) runs
inside this lab. Nothing can be tested safely until the isolated network exists. This is the
foundation of constitution Principle I (Safety & Isolation).

**Independent Test**: Run the bring-up command and confirm the lab reaches a healthy state.
Run the tear-down command and confirm all containers and the network are removed cleanly.
Delivers value on its own: a reproducible, isolated network that future features can join.

**Acceptance Scenarios**:

1. **Given** Docker is installed and no lab is running, **When** the researcher runs the
   bring-up command, **Then** all lab containers start and the internal network is created
   with no outbound routing within 60 seconds.
2. **Given** the lab is running, **When** the researcher runs the tear-down command, **Then**
   all containers stop and the network is removed with no orphaned resources.
3. **Given** the bring-up command is run twice with the same configuration, **When** the second
   run completes, **Then** the network topology is identical to the first run (reproducible).

---

### User Story 2 — Isolation Verification (Priority: P1)

A researcher can verify that the lab has no outbound internet access by running a single
verification command. The command attempts an outbound connection from inside the lab and
confirms it is blocked.

**Why this priority**: Constitution Principle I requires the lab to be air-gapped. Without a
verifiable test, there is no guarantee the isolation is actually in effect. A passing isolation
test is a hard gate before any attacker simulation can run.

**Independent Test**: With the lab running, execute the isolation check. The check must confirm
that outbound connections from lab containers are blocked (connection refused or timed out).

**Acceptance Scenarios**:

1. **Given** the lab is running, **When** the isolation check runs, **Then** any attempt to
   connect from a lab container to an external host (e.g., a public DNS resolver) fails with
   a network error — confirming no outbound route exists.
2. **Given** the lab is running with correct internal-only network config, **When** containers
   communicate with each other on the internal network, **Then** intra-lab communication
   succeeds (isolation only blocks outbound, not intra-lab traffic).
3. **Given** the isolation check fails (outbound connection succeeds), **When** the check
   reports its result, **Then** it exits with a non-zero status code and a clear error message
   identifying the breach.

---

### User Story 3 — Lab Status Visibility (Priority: P2)

A researcher can check the current state of the lab (running / stopped / degraded) at any time
with a single command, without having to inspect raw container state manually.

**Why this priority**: Useful for CI and for researchers resuming work, but the lab is functional
without it. Status visibility is a quality-of-life feature, not a safety gate.

**Independent Test**: With the lab stopped, run the status command — it reports "not running".
Start the lab, run status again — it reports all containers healthy.

**Acceptance Scenarios**:

1. **Given** no lab is running, **When** the status command runs, **Then** it reports the lab
   as stopped with no containers active.
2. **Given** the lab is running and all containers are healthy, **When** the status command
   runs, **Then** it reports each container as healthy with its role name.
3. **Given** the lab is running but one container has exited unexpectedly, **When** the status
   command runs, **Then** it reports the lab as degraded and identifies the failed container.

---

### Edge Cases

- What if Docker is not installed when the bring-up command runs? The command must exit with
  a clear error message identifying the missing dependency.
- What if the internal network already exists from a previous unclean teardown? The bring-up
  command must handle this gracefully — reuse or recreate the network without error.
- What if a container fails to start? The bring-up command must report which container failed
  and exit non-zero (no silent partial starts).
- What if the isolation check is run when the lab is not running? It must fail fast with a
  clear message rather than hanging on a connection attempt.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The lab network MUST be configured as internal-only — no container on the lab
  network may have a route to the public internet.
- **FR-002**: The lab MUST be startable with a single command that brings up all containers
  and the internal network.
- **FR-003**: The lab MUST be stoppable with a single command that removes all containers and
  the internal network, leaving no orphaned resources.
- **FR-004**: The lab configuration MUST be reproducible — the same configuration file run on
  the same host produces an identical network topology every time.
- **FR-005**: An isolation verification command MUST exist that confirms outbound internet
  access is blocked from within the lab. It MUST exit non-zero if outbound access succeeds.
- **FR-006**: The lab MUST define named roles for the three experiment participants: attacker,
  defender, and environment. At this stage, containers for these roles are stubs (minimal
  images) — no experiment logic is implemented.
- **FR-007**: The bring-up, tear-down, isolation-check, and status commands MUST be accessible
  via Makefile targets, consistent with the existing `make test` / `make lint` pattern.
  The isolation-check target (`make lab-check`) MUST NOT be wired into `make test` — it runs
  as a separate CI step on a Docker-capable runner, keeping the pytest suite Docker-free.
- **FR-008**: The lab MUST NOT require any credentials, API keys, or outbound network access
  during experiment execution. `make lab-up` MUST automatically pull all required images
  (while the host still has internet access) before activating the internal-only network —
  no separate pull step is required.
- **FR-009**: Container names and network names MUST be deterministic (not random suffixes) so
  that the status command and CI scripts can reference them reliably.

### Key Entities

- **Lab Network**: The internal-only virtual network. Has a fixed name and subnet. Carries all
  intra-lab traffic. Has no gateway to the host's external network interfaces.
- **Attacker Container**: Stub container occupying the attacker role on the lab network.
  No experiment logic yet.
- **Defender Container**: Stub container occupying the defender role on the lab network.
- **Environment Container**: Stub container occupying the simulation environment role on the
  lab network.
- **Isolation Check**: A one-shot command that attempts an outbound connection from inside the
  lab and reports pass/fail. Not a long-running service.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The lab reaches a fully healthy state (all containers running) in under 60 seconds
  from a cold start on a machine with Docker already installed.
- **SC-002**: The isolation check passes — outbound connection attempts from lab containers are
  blocked — on every run with the standard configuration.
- **SC-003**: The lab can be started and stopped at least 3 times in succession with no orphaned
  containers, networks, or volumes remaining after each teardown.
- **SC-004**: The same configuration brought up on the same host twice produces a network
  topology with identical names, subnets, and container roles both times.
- **SC-005**: The bring-up, teardown, and isolation-check commands complete without requiring
  any manual steps beyond running the single command (no interactive prompts).

## Clarifications

### Session 2026-07-02

- Q: Should the isolation check be integrated into `make test` or remain a separate CI step? → A: Separate CI step — `make lab-check` is standalone; the existing pytest suite stays Docker-free.
- Q: Image pull strategy for FR-008 — auto-pull in `make lab-up` or separate `make lab-pull` step? → A: `make lab-up` pulls images automatically before activating the internal-only network — one command, no manual pre-steps.

## Assumptions

- Docker Engine and Docker Compose (v2 plugin) are installed on the developer's machine.
  Installation of Docker is not in scope for this feature.
- The three stub containers use a minimal base image — no custom Dockerfiles are needed at
  this stage.
- "Internal-only" means the network is configured with no external gateway, preventing
  containers from routing traffic outside the lab.
- The isolation check uses a network-level probe (TCP connection or DNS resolution attempt
  to a known external address) from inside a lab container.
- CI will run these commands on a Linux host with Docker available.

## Out of Scope

- Suricata adapter (F11), attacker logic (F17+), episode orchestrator (F16), ML detectors.
- Custom Dockerfiles for attacker/defender/environment — stub images only.
- Multi-host or Kubernetes deployment.
- Container resource limits (CPU/memory) — deferred to a later hardening feature.
- Persistent volumes or data storage for experiment outputs — deferred to F16+.

## Dependencies

- **F01**: Makefile conventions — new lab targets follow the same pattern as `make test`.
- **F02**: `config.yaml` pattern — lab network name and subnet follow the same config approach.
- **F03**: `contracts.py` — data shapes that will flow through this network in later features;
  no direct dependency at this stage, but the lab must be ready to carry them.
