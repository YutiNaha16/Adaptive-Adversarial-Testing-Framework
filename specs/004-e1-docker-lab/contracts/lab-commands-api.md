# Lab Commands API: 004-e1-docker-lab

Four Makefile targets constitute the F04 interface. Each is a shell command with defined
pre-conditions, post-conditions, and exit codes. These are the acceptance contracts for tasks.md.

---

## make lab-up

**Purpose**: Pull required images (using host network), create the internal-only lab network,
and start all three stub containers.

**Pre-conditions**:
- Docker Engine and Compose V2 are installed
- No prior `make lab-up` is required (idempotent — can be re-run after crash)

**Steps** (Makefile implements in order):
1. `docker compose -f lab/docker-compose.yml pull` — pull `alpine:3.19` via host network
2. `docker compose -f lab/docker-compose.yml up -d` — create network + start containers

**Post-conditions**:
- Network `aatf-lab` exists with `internal: true` and subnet `172.28.0.0/16`
- Containers `aatf-attacker`, `aatf-defender`, `aatf-environment` all in `running` state
- No host ports published

**Exit codes**:
- `0` — all containers running
- Non-zero — at least one container failed to start; error printed to stderr

**Test contracts** (for tasks.md):
- T-LU1: After `make lab-up`, `docker ps` shows all 3 `aatf-*` containers running
- T-LU2: Network `aatf-lab` exists and `Internal: true` in `docker network inspect aatf-lab`
- T-LU3: `make lab-up` run twice produces identical container/network state (idempotent)
- T-LU4: If Docker is not installed, `make lab-up` exits non-zero with a clear error

---

## make lab-down

**Purpose**: Stop all lab containers and remove the lab network, leaving no orphaned resources.

**Pre-conditions**:
- Lab may be running or partially running (idempotent — safe to call even if stopped)

**Steps**:
1. `docker compose -f lab/docker-compose.yml down --remove-orphans`

**Post-conditions**:
- Containers `aatf-attacker`, `aatf-defender`, `aatf-environment` no longer exist
- Network `aatf-lab` no longer exists
- No orphaned containers from previous runs remain

**Exit codes**:
- `0` — all resources removed (or were already absent)
- Non-zero — removal failed; error printed to stderr

**Test contracts**:
- T-LD1: After `make lab-down`, `docker ps -a` shows no `aatf-*` containers
- T-LD2: After `make lab-down`, `docker network ls` shows no `aatf-lab` network
- T-LD3: `make lab-down` on an already-stopped lab exits 0 (idempotent)
- T-LD4: `make lab-up && make lab-down` cycle repeated 3 times leaves no orphans

---

## make lab-check

**Purpose**: Verify the lab has no outbound internet access. Exits non-zero if isolation is
breached. NOT called by `make test` — standalone target only (spec Q1).

**Pre-conditions**:
- Lab must be running (`make lab-up` already called)

**Steps** (`lab/scripts/check-isolation.sh`):
1. Confirm `aatf-attacker` container is running; exit 2 if not
2. `docker exec aatf-attacker nc -z -w 5 8.8.8.8 53`
   - `nc` exit 0 → outbound succeeded → BREACH
   - `nc` exit non-zero → outbound blocked → ISOLATED
3. Print result to stdout; print breach details to stderr

**Post-conditions**: None (read-only check)

**Exit codes**:
- `0` — isolated (outbound blocked; lab passes safety gate)
- `1` — breach (outbound connection succeeded; isolation is NOT enforced)
- `2` — lab not running (pre-condition violated)

**Test contracts**:
- T-LC1: With standard `internal: true` config, `make lab-check` exits 0 and prints "ISOLATED"
- T-LC2: With `internal: true` removed (deliberate misconfiguration), `make lab-check` exits 1
  and prints "BREACH" to stderr
- T-LC3: With lab stopped, `make lab-check` exits 2 with a clear "lab not running" message
- T-LC4: `make lab-check` completes in under 10 seconds (isolation failure is near-instant)

---

## make lab-status

**Purpose**: Report current lab state (running / stopped / degraded) without modifying anything.

**Pre-conditions**: None

**Steps**:
1. `docker compose -f lab/docker-compose.yml ps` — inspect container states
2. Classify overall state: all running → running; none → stopped; partial → degraded
3. Print per-container status lines and overall state

**Post-conditions**: None (read-only)

**Exit codes**:
- `0` — all containers running (lab healthy)
- `1` — lab stopped (no containers exist or all exited)
- `2` — lab degraded (≥1 container exited unexpectedly)

**Test contracts**:
- T-LS1: With lab stopped, `make lab-status` exits 1 and prints "stopped"
- T-LS2: With lab running, `make lab-status` exits 0 and lists all 3 containers as healthy
- T-LS3: With one container forcibly killed, `make lab-status` exits 2 and names the failed
  container
