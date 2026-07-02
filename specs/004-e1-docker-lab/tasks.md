---
description: "Task list for 004-e1-docker-lab"
---

# Tasks: Internal-only Docker Lab

**Input**: Design documents from `specs/004-e1-docker-lab/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/lab-commands-api.md

**Tests**: No pytest tests (the existing `make test` suite is Docker-free by design — spec Q1).
Acceptance is verified by running each Makefile target and confirming the 14 shell-level
contracts from `contracts/lab-commands-api.md`. Verification steps are embedded in the
implementation tasks rather than written as separate test files.

**Organization**: Three user stories map to three phases. All share one foundational file
(`lab/docker-compose.yml`). No Python source files are modified.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: US1–US3 per spec.md

## Path Conventions

All new files live under `lab/` at the repo root. `Makefile` at root gets 4 new targets.
No changes to `src/`, `tests/`, `requirements.in`, or `requirements.txt`.

---

## Phase 1: Setup

**Purpose**: Create directory structure and confirm Docker prerequisites.

- [X] T001 Create `lab/` and `lab/scripts/` directories: `mkdir -p lab/scripts`
- [X] T002 Verify Docker Engine and Compose V2 are installed: run `docker --version` and
  `docker compose version` — both must succeed. If Docker is absent, note it for the user;
  the remaining tasks require Docker but the files can still be created.

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Create `lab/docker-compose.yml` — the shared foundation that all three user
stories depend on. No Makefile targets yet; just the compose file.

**⚠️ CRITICAL**: Phases 3–5 all depend on this file existing and being correct.

- [X] T003 Create `lab/docker-compose.yml` with the following content exactly:
  - Top-level `name: aatf-lab` (pins Compose project name for deterministic container names)
  - `networks:` block: network named `lab`, `name: aatf-lab`, `internal: true`,
    `ipam.config` subnet `172.28.0.0/16`
  - Three services (`attacker`, `defender`, `environment`), each with:
    - `image: alpine:3.19`
    - `container_name: aatf-<role>` (e.g. `aatf-attacker`)
    - `networks: [lab]`
    - `command: ["sleep", "infinity"]`
    - `restart: "no"`
  - No host ports published on any service
  - No volumes

**Checkpoint**: `lab/docker-compose.yml` exists and `docker compose -f lab/docker-compose.yml config`
validates without errors (if Docker is installed).

---

## Phase 3: User Story 1 — Lab Network Provisioning (Priority: P1) 🎯 MVP

**Goal**: `make lab-up` brings up the isolated lab; `make lab-down` tears it down cleanly.
Both are idempotent. The network is internal-only (no outbound routing).

**Independent Test**: Run `make lab-up` → `docker ps` shows 3 `aatf-*` containers →
`docker network inspect aatf-lab` shows `"Internal": true` → `make lab-down` → no containers
or network remain.

### Implementation for User Story 1

- [X] T004 [US1] Add `lab-up` target to `Makefile` — define `COMPOSE := docker compose -f lab/docker-compose.yml`
  at the top of the Makefile lab section, then:
  ```makefile
  lab-up:  ## Pull images and start the isolated lab (internal-only network)
      $(COMPOSE) pull
      $(COMPOSE) up -d
  ```
  Place below the existing `run` target. Add `lab-up` to the `.PHONY` list.

- [X] T005 [US1] Add `lab-down` target to `Makefile`:
  ```makefile
  lab-down:  ## Stop and remove all lab containers and the lab network
      $(COMPOSE) down --remove-orphans
  ```
  Add `lab-down` to the `.PHONY` list.

- [ ] T006 [US1] Verify T-LU1 and T-LU2 — run `make lab-up` and confirm:
  - `docker ps --format "{{.Names}}"` shows `aatf-attacker`, `aatf-defender`, `aatf-environment`
  - `docker network inspect aatf-lab --format "{{.Internal}}"` prints `true`

- [ ] T007 [US1] Verify T-LU3 — run `make lab-up` a second time while lab is already running;
  confirm it exits 0 with no errors and container count remains exactly 3 (idempotent).

- [ ] T008 [US1] Verify T-LD1 and T-LD2 — run `make lab-down` and confirm:
  - `docker ps -a --format "{{.Names}}" | grep aatf` produces no output
  - `docker network ls --format "{{.Name}}" | grep aatf-lab` produces no output

- [ ] T009 [US1] Verify T-LD3 — run `make lab-down` again (lab already stopped); confirm it
  exits 0 without errors (idempotent teardown).

- [ ] T010 [US1] Verify T-LD4 — run the full `make lab-up && make lab-down` cycle 3 times in
  succession; after the third teardown, confirm no `aatf-*` containers or `aatf-lab` network
  remain (cycle stability, SC-003).

**Checkpoint**: US1 complete — `make lab-up` / `make lab-down` work, are idempotent, and
leave no orphaned resources. The isolated network is operational.

---

## Phase 4: User Story 2 — Isolation Verification (Priority: P1)

**Goal**: `make lab-check` confirms no outbound internet access from inside the lab.
Exits 0 if isolated, 1 if breach detected, 2 if lab is not running.

**Independent Test**: With lab running under standard config (`internal: true`),
`make lab-check` exits 0 and prints "ISOLATED". With `internal: true` removed, it exits 1.

### Implementation for User Story 2

- [X] T011 [US2] Create `lab/scripts/check-isolation.sh` with this content:
  ```sh
  #!/usr/bin/env sh
  # Verify lab has no outbound internet access.
  # Exit 0 = isolated, 1 = breach, 2 = lab not running.
  set -e

  CONTAINER="aatf-attacker"
  TARGET_HOST="8.8.8.8"
  TARGET_PORT="53"
  TIMEOUT="5"

  if ! docker inspect "$CONTAINER" > /dev/null 2>&1; then
      printf 'ERROR: Lab is not running. Run "make lab-up" first.\n' >&2
      exit 2
  fi

  if docker exec "$CONTAINER" nc -z -w "$TIMEOUT" "$TARGET_HOST" "$TARGET_PORT" 2>/dev/null; then
      printf 'BREACH: Outbound connection to %s:%s succeeded — isolation NOT enforced.\n' \
          "$TARGET_HOST" "$TARGET_PORT" >&2
      exit 1
  else
      printf 'ISOLATED: Outbound connection to %s:%s blocked — lab isolation confirmed.\n' \
          "$TARGET_HOST" "$TARGET_PORT"
      exit 0
  fi
  ```

- [X] T012 [US2] Make the script executable: `chmod +x lab/scripts/check-isolation.sh`

- [X] T013 [US2] Add `lab-check` target to `Makefile`:
  ```makefile
  lab-check:  ## Verify lab has no outbound internet access (exits 1 on breach)
      @bash lab/scripts/check-isolation.sh
  ```
  Add `lab-check` to the `.PHONY` list. Note: NOT called by `make test` — standalone only.

- [ ] T014 [US2] Verify T-LC1 — with lab running (`make lab-up` first): run `make lab-check`;
  confirm it exits 0 and prints a line containing "ISOLATED".

- [ ] T015 [US2] Verify T-LC2 (breach detection) — temporarily comment out `internal: true`
  in `lab/docker-compose.yml`, run `make lab-down && make lab-up && make lab-check`; confirm
  it exits 1 and prints "BREACH" to stderr. Restore `internal: true` and run `make lab-down`.

- [ ] T016 [US2] Verify T-LC3 — run `make lab-down` first, then `make lab-check`; confirm it
  exits 2 and prints the "lab not running" error message.

- [ ] T017 [US2] Verify T-LC4 — with lab running, time `make lab-check`; confirm it completes
  in under 10 seconds (should be near-instant with `internal: true` due to immediate ICMP
  unreachable).

**Checkpoint**: US2 complete — isolation is structurally enforced and verifiably checked.
Constitution Principle I safety gate is operational.

---

## Phase 5: User Story 3 — Lab Status Visibility (Priority: P2)

**Goal**: `make lab-status` reports current lab state (running / stopped / degraded) and
exits with the appropriate code: 0 = running, 1 = stopped, 2 = degraded.

**Independent Test**: Lab stopped → `make lab-status` exits 1. Lab running → exits 0 with all
3 containers listed. One container killed → exits 2 naming the failed container.

### Implementation for User Story 3

- [X] T018 [US3] Create `lab/scripts/lab-status.sh` with this content:
  ```sh
  #!/usr/bin/env sh
  # Report lab state: exits 0=running, 1=stopped, 2=degraded.
  set -e

  CONTAINERS="aatf-attacker aatf-defender aatf-environment"
  running=0
  total=0

  for name in $CONTAINERS; do
      total=$((total + 1))
      state=$(docker inspect --format '{{.State.Status}}' "$name" 2>/dev/null || echo "absent")
      printf '  %-22s %s\n' "$name" "$state"
      if [ "$state" = "running" ]; then
          running=$((running + 1))
      fi
  done

  if [ "$running" -eq "$total" ]; then
      printf 'Lab state: running (%d/%d containers up)\n' "$running" "$total"
      exit 0
  elif [ "$running" -eq 0 ]; then
      printf 'Lab state: stopped (0/%d containers up)\n' "$total"
      exit 1
  else
      printf 'Lab state: degraded (%d/%d containers up)\n' "$running" "$total"
      exit 2
  fi
  ```

- [X] T019 [US3] Make the script executable: `chmod +x lab/scripts/lab-status.sh`

- [X] T020 [US3] Add `lab-status` target to `Makefile`:
  ```makefile
  lab-status:  ## Show current lab container states (exits 0=running, 1=stopped, 2=degraded)
      @bash lab/scripts/lab-status.sh
  ```
  Add `lab-status` to the `.PHONY` list.

- [ ] T021 [US3] Verify T-LS1 — with lab stopped: run `make lab-status`; confirm it exits 1
  and output includes "stopped".

- [ ] T022 [US3] Verify T-LS2 — run `make lab-up`, then `make lab-status`; confirm it exits 0
  and output lists all 3 containers as "running".

- [ ] T023 [US3] Verify T-LS3 — with lab running, run `docker kill aatf-defender`, then
  `make lab-status`; confirm it exits 2 and output identifies `aatf-defender` as non-running.
  Then run `make lab-down` to clean up.

**Checkpoint**: All 3 user stories complete — all 14 test contracts from lab-commands-api.md
verified. Lab is fully operational.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T024 Run `make test` — confirm all 63 Python tests still pass (Docker-free suite must
  not be affected by any Makefile or shell additions).

- [X] T025 [P] Run `make lint` — confirm `ruff check .` and `ruff format --check .` pass
  (no Python files changed, but confirms no accidental edits).

- [X] T026 [P] Update `README.md`:
  - Add `docker` and `docker compose` (v2) to the **Requirements** section
  - Add `make lab-up`, `make lab-down`, `make lab-check`, `make lab-status` to the
    **Quickstart** section with one-line descriptions
  - Add `lab/` to the **Project layout** section:
    ```
    lab/
    ├── docker-compose.yml  # internal-only network + 3 alpine:3.19 stub containers
    └── scripts/
        ├── check-isolation.sh  # exits 0=isolated, 1=breach, 2=not-running
        └── lab-status.sh       # exits 0=running, 1=stopped, 2=degraded
    ```

- [ ] T027 Validate `quickstart.md` SC-001 through SC-005 are all covered by the implemented
  targets and scripts (manual review — confirm each scenario produces the documented output).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001 and T002 immediately.
- **Foundational (Phase 2)**: T001 must complete (directory exists) before T003.
- **US1 (Phase 3)**: T003 must complete (compose file exists) before T004–T010.
- **US2 (Phase 4)**: T003 must complete; T004 (lab-up target) must exist for T014–T017
  verification steps.
- **US3 (Phase 5)**: Independent of US2; depends only on T003 and T004 (lab-up for T022–T023).
- **Polish (Phase 6)**: All US phases complete.

### Parallel Opportunities

- T001 and T002 are independent (can run together)
- US2 (Phase 4) and US3 (Phase 5) are largely independent — both depend on Phase 2+3
  completion but do not depend on each other. T011–T013 and T018–T020 touch different files.
- T024, T025, T026 in Polish are all independent files — can run in parallel.

---

## Implementation Strategy

### MVP First (US1 Only)

1. Phase 1 Setup → Phase 2 Foundational (T001–T003)
2. Phase 3 US1: lab-up + lab-down (T004–T010)
3. **STOP and VALIDATE**: Lab brings up 3 containers on internal network and tears down cleanly.
   That's a usable, constitution-compliant isolated environment — future features (F05, F11)
   can join this network immediately.

### Incremental Delivery

US1 (provisioning) → US2 (isolation verified = safety gate passes) → US3 (status visibility) → Polish.
Each phase adds a distinct capability without breaking the previous.

---

## Notes

- No Python files are modified in this feature. `make test` must stay green throughout.
- The `.PHONY` line in Makefile must include all 4 new targets: `lab-up lab-down lab-check lab-status`.
- T015 (breach detection test) requires temporarily editing docker-compose.yml — always restore
  `internal: true` before proceeding and run `make lab-down` to reset.
- If Docker is not installed, T001–T003 can still be completed (file creation only). T004+
  verification steps require Docker.
- `COMPOSE` variable in Makefile should be defined once at the top of the lab section to
  avoid repeating the `-f lab/docker-compose.yml` flag across all 4 targets.
