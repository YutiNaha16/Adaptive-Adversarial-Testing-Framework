# Feature Specification: Suricata + Pinned ET Open Ruleset

**Feature Branch**: `006-e1-suricata-etopen`
**Created**: 2026-07-02
**Status**: Draft
**Input**: F05 from docs/backlog.md — Epic E1, Isolated Lab Environment

## Overview

F05 adds Suricata as the detection judge of record to the existing Docker lab (F04).
Suricata runs inside the `aatf-lab` internal network, monitors all inter-container traffic,
and writes structured alerts (`eve.json`) to a shared location accessible to the feedback
collector (F15) and adapter (F11) in later features.

This feature does NOT implement the eve.json parser (F11), the feedback collector (F15),
or any attacker logic. It only installs and verifies Suricata + ET Open ruleset in the lab.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Detection Service in Lab (Priority: P1) 🎯 MVP

When a researcher runs `make lab-up`, Suricata starts alongside the three existing lab
containers (attacker, defender, environment), monitors all traffic on the internal lab
network, and writes detection alerts to a shared volume that other lab components can read.
The Suricata version and ET Open ruleset version are both recorded for reproducibility.

**Why this priority**: Without a running Suricata service, no detection signal exists —
every downstream feature (F11 adapter, F15 collector, F16 orchestrator) is blocked. This is
the foundational detection capability for the entire Phase 1 experiment.

**Independent Test**: Run `make lab-up`; confirm Suricata container is running and healthy;
confirm eve.json output path exists and is readable from the host or other containers.

**Acceptance Scenarios**:

1. **Given** a clean lab, **When** `make lab-up` runs, **Then** a Suricata container starts
   and reaches a healthy/ready state alongside the three existing containers.
2. **Given** the lab is running, **When** any traffic flows between lab containers,
   **Then** Suricata monitors it (interface configured to capture lab network traffic).
3. **Given** the lab is running, **When** the shared alert output is inspected,
   **Then** the eve.json file path is accessible (readable by other containers and/or
   mounted to the host).
4. **Given** the lab is running, **When** Suricata's version and ruleset version are
   inspected, **Then** both match the pinned values declared in the lab configuration —
   not "latest" or auto-updated values.

---

### User Story 2 — Smoke Test: Known Probe Triggers Expected SID (Priority: P1)

A researcher can verify that the Suricata + ET Open detection pipeline is correctly wired
by sending a known-malicious-shaped probe from the attacker container and confirming that
the expected rule identifier (SID) appears in eve.json within a bounded time window.

**Why this priority**: US1 proves Suricata is running; US2 proves it is actually detecting.
A Suricata service that starts but silently misses alerts gives false confidence to all
downstream metrics. The smoke test is the end-to-end detection wiring check.

**Independent Test**: With lab running, execute `make lab-smoke`; confirm it exits 0 and
prints the triggered SID. Without lab running, confirm it exits non-zero with a clear error.

**Acceptance Scenarios**:

1. **Given** the lab is running with Suricata active, **When** `make lab-smoke` is run,
   **Then** a probe is sent from the attacker container to the defender container, and
   within 10 seconds the expected SID appears in eve.json.
2. **Given** `make lab-smoke` succeeds, **When** its output is read, **Then** it exits 0
   and prints the triggered SID and timestamp.
3. **Given** the lab is not running, **When** `make lab-smoke` is run, **Then** it exits
   non-zero with a clear error (not a silent hang).
4. **Given** the expected SID does NOT appear within the timeout, **When** `make lab-smoke`
   completes, **Then** it exits non-zero and reports which SID was expected but not found.

---

### User Story 3 — SID Enable/Disable Hook (Priority: P2)

A researcher can disable a specific Suricata rule by SID before running an experiment and
re-enable it afterwards. When a rule is disabled, traffic that normally triggers that SID
produces no alert. This is the mechanism F22 (ground-truth validation) uses to create a
known set of blind spots and verify the explainability report finds exactly those gaps.

**Why this priority**: Not needed until F22 but must be in place before F22 is implemented.
Delivered here so the hook exists when the lab is first operational.

**Independent Test**: Disable a known SID; restart the lab; send the matching probe via
`make lab-smoke`; confirm the SID no longer appears in eve.json. Re-enable and repeat to
confirm the SID reappears.

**Acceptance Scenarios**:

1. **Given** a SID is added to the disabled-rules config and the lab is restarted,
   **When** a probe that normally triggers that SID is sent, **Then** no alert for that
   SID appears in eve.json.
2. **Given** a previously disabled SID is removed from the config and the lab is restarted,
   **When** the matching probe is sent, **Then** the alert reappears in eve.json.
3. **Given** the disable/enable hook is inspected, **When** the disabled-rules config is
   read, **Then** it is human-readable, version-controlled, and clearly documented.

---

### Edge Cases

- What if Suricata fails to start (bad config, missing ruleset)? `make lab-up` must exit
  non-zero with a clear error — not silently leave Suricata absent while other containers start.
- What if the probe sent during `make lab-smoke` does not trigger the SID within the
  timeout? The command must report a clear failure — never silently pass with a zero exit.
- What if eve.json grows large within a long session? No rotation needed now; the file is
  cleared when the volume is removed on `make lab-down`.
- What if multiple SIDs need to be disabled simultaneously? The hook must accept a list of
  SIDs (one per line in the config file), not just a single SID.
- What if the researcher forgets disabled SIDs are active? The disabled-rules config is
  version-controlled and visible — the state is always explicit and auditable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The lab MUST include a Suricata service that starts as part of `make lab-up`
  and stops as part of `make lab-down`, alongside the existing three containers.
- **FR-002**: The Suricata service MUST run on a pinned version (not "latest") and monitor
  traffic on the `aatf-lab` internal network interface.
- **FR-003**: The ET Open ruleset MUST be pinned to a specific snapshot; it MUST NOT
  auto-update on `make lab-up`. The pinned version MUST be recorded as `ruleset_version`
  in run manifests (field already defined in F03's `RunManifest`).
- **FR-004**: Suricata MUST write `eve.json` alerts to a shared location (Docker volume
  or bind-mounted path) accessible to other lab containers and readable from the host.
- **FR-005**: `make lab-smoke` MUST send a known probe from the attacker container to the
  defender container, wait up to 10 seconds for the expected SID to appear in eve.json,
  print the result, and exit 0 on success or non-zero on failure or lab-not-running.
- **FR-006**: The smoke test MUST target at least one specific, documented ET Open SID that
  is reliably triggered by the probe without real exploit payloads.
- **FR-007**: A documented mechanism MUST exist to disable one or more rules by SID before
  starting the lab; the set of disabled SIDs MUST be stored in a human-readable,
  version-controlled file (empty by default — no SIDs disabled out of the box).
- **FR-008**: When SIDs are disabled via the hook and the lab is restarted, Suricata MUST
  NOT alert on traffic that matches those SIDs.
- **FR-009**: `make lab-status` MUST report Suricata's container state alongside the
  existing three containers (4 containers total after this feature).
- **FR-010**: The Suricata version string MUST be accessible via a documented command or
  container label so it can be recorded as `suricata_version` in run manifests.
- **FR-011**: `make test` MUST remain Docker-free and pass its existing 78 tests (1 skipped)
  without modification — no new pytest tests require Docker for this feature.

### Key Entities

- **Suricata Service**: The detection judge. Runs in the lab, monitors traffic, emits
  alerts. Pinned version, pinned ruleset.
- **ET Open Ruleset**: Detection rules loaded into Suricata. Pinned to a specific snapshot;
  version recorded in manifest.
- **eve.json**: Suricata's structured alert output file. Written to a shared Docker volume.
  Source of truth for all detection signals in the experiment loop.
- **Disabled-Rules Config**: A version-controlled file listing SIDs to suppress. Empty by
  default; populated by F22 for ground-truth validation experiments.
- **Smoke Probe**: A network action from the attacker container that reliably triggers a
  specific ET Open SID, used to verify the detection pipeline is operational.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `make lab-up` brings up 4 containers (3 from F04 + Suricata) and all reach a
  running/healthy state within 60 seconds on a warm start (images already pulled).
- **SC-002**: `make lab-smoke` exits 0 and prints the triggered SID within 15 seconds of
  being run against a running lab.
- **SC-003**: Disabling a SID and restarting the lab results in zero alerts for that SID
  when the matching probe is sent — verified by `make lab-smoke` reporting the expected SID
  is absent.
- **SC-004**: Suricata version and ET Open ruleset version are both readable via a
  documented command without starting an experiment.
- **SC-005**: `make test` continues to pass 78 tests with 1 skipped after this feature is
  implemented — no regressions in the Docker-free test suite.

## Clarifications

### Session 2026-07-02

- Q: How is the smoke test invoked? → A: [NEEDS CLARIFICATION: dedicated Makefile target
  (`make lab-smoke`) vs pytest `@pytest.mark.docker` test consistent with F06's approach]
- Q: How is the ET Open ruleset pinned for reproducibility? → A: [NEEDS CLARIFICATION:
  baked into a custom Suricata Dockerfile (most reproducible, requires image build) vs
  downloaded from a pinned snapshot URL into a named volume at first `make lab-up`]

## Assumptions

- The Suricata service is added to `lab/docker-compose.yml` alongside the existing three
  containers; it joins the same `aatf-lab` internal network.
- The smoke probe does not require real exploit payloads — a traffic pattern matching an
  ET SCAN or ET POLICY SID (e.g., a port scan or suspicious HTTP request) is sufficient
  to demonstrate detection.
- eve.json is cleared on each `make lab-down` + `make lab-up` cycle (volume removed and
  recreated). No log rotation is needed within a single lab session.
- The disabled-rules config is an empty file by default; it is populated only when F22
  (ground-truth validation) runs deliberate blind-spot experiments.
- `make test` remains Docker-free (FR-011) — consistent with decisions made in F04/F06.

## Dependencies

- **F04** (`004-e1-docker-lab`): The `aatf-lab` network and `lab/docker-compose.yml` are
  extended by this feature. `make lab-up/down/status` Makefile targets are updated.
- **F03** (`003-e0-core-contracts`): `RunManifest` already has `suricata_version` and
  `ruleset_version` fields — this feature makes those fields meaningful.
- **Constitution Principle I**: Suricata monitors only the internal `aatf-lab` network.
  No external connectivity is introduced. The probe stays fully inside the lab.
- **Constitution Principle II**: Both Suricata version and ET Open ruleset version must be
  pinned and deterministic — not "latest" or auto-updated between runs.
