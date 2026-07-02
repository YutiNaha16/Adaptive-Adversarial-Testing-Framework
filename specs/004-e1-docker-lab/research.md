# Research: 004-e1-docker-lab

## D1 — Docker network `internal: true` behaviour

**Decision**: Use `internal: true` on the Compose network definition.

**Rationale**: Constitution Principle I mandates this explicitly: "Compose files MUST declare
networks as `internal: true`." With `internal: true`, Docker removes the default gateway from
the network's routing table. Containers on the network receive immediate ICMP "Network
unreachable" when attempting outbound connections — no TCP timeout hang. This makes the
isolation check fast and deterministic.

**Alternatives considered**: `--network none` per container — rejected because it also blocks
intra-lab traffic, which breaks container-to-container communication required by later features.

---

## D2 — Stub image choice

**Decision**: `alpine:3.19` pinned by tag for all three stub containers.

**Rationale**: Alpine is the standard minimal image (~7 MB). Pinning to `3.19` satisfies
constitution Principle II (reproducibility) — `alpine:latest` would drift between pulls.
Alpine includes `nc` (netcat) and `wget` via BusyBox, both needed by the isolation check.
No custom Dockerfile is needed — stub containers simply run an idle loop.

**Alternatives considered**: `busybox:1.36` — equally minimal but less familiar; `scratch` —
no shell, cannot exec for isolation check.

---

## D3 — Isolation check mechanism

**Decision**: `docker exec` into the running attacker stub, attempt TCP connection to
`8.8.8.8:53` with a 5-second timeout using `nc`. Exit 0 from `nc` = breach; non-zero = isolated.

**Rationale**: `nc -z -w 5 8.8.8.8 53` probes an external IP:port without transmitting data.
With `internal: true`, `nc` exits immediately with non-zero ("Network unreachable"). The
5-second timeout is a safety net only — in practice the failure is instant. Using `docker exec`
on an already-running container (vs. `docker run` with a temp container) avoids pulling a
separate image and keeps the check fast.

**Alternatives considered**: `wget http://8.8.8.8` — requires HTTP server to respond; `ping`
— may be filtered differently from TCP; `curl` — not available in alpine by default.

---

## D4 — Image pull before internal network activation

**Decision**: `make lab-up` runs `docker compose pull` (uses host network) then `docker compose up -d`.

**Rationale**: Docker image pulls happen at the daemon level using the host's network stack,
not the container network — so `internal: true` does not block pulls. However, to make the
intent explicit and satisfy FR-008 (images must be available before the internal network is
activated), we separate the pull and up steps in the Makefile. This also gives a clear failure
point if the image is unavailable.

**Alternatives considered**: `docker compose up -d --pull always` (single command) — works
but makes the two-phase intent less visible; `docker compose up -d` without explicit pull —
relies on cached images, could silently use stale versions.

---

## D5 — Lab directory layout

**Decision**: `lab/` directory at repo root containing `docker-compose.yml` and `scripts/`.

**Rationale**: Keeps all Docker infrastructure separate from Python source (`src/aatf/`) and
tests (`tests/`). Consistent with the two-layer architecture in the constitution (live lab vs.
offline analysis). Future features (Suricata adapter, network policy) extend `lab/` without
touching Python code.

**Alternatives considered**: `docker/` directory — less descriptive for this project;
`docker-compose.yml` at repo root — pollutes the root and mixes concerns.

---

## D6 — Container and network naming

**Decision**: Deterministic names — `aatf-attacker`, `aatf-defender`, `aatf-environment`
(containers); `aatf-lab` (network); subnet `172.28.0.0/16`.

**Rationale**: FR-009 requires deterministic names for CI scripts and the status command.
`aatf-` prefix prevents collision with other containers on the host. `172.28.0.0/16` is a
private range not commonly used by default Docker networks (`172.17.0.0/16`) or VPNs, reducing
subnet conflict risk.

**Alternatives considered**: Docker Compose default names (project name + service name) —
less predictable across environments; random suffixes — explicitly prohibited by FR-009.

---

## D7 — Compose V2 vs V1

**Decision**: Docker Compose V2 (`docker compose` as a CLI plugin, no hyphen).

**Rationale**: Docker Compose V1 (`docker-compose`) is deprecated and removed from Docker
Desktop 4.x+. V2 is the current standard. The `name:` top-level key in `docker-compose.yml`
(supported in V2) pins the project name, ensuring container names are deterministic regardless
of the directory the compose file is run from.

**Alternatives considered**: V1 — deprecated, not reliably available on modern hosts.

---

## D8 — `make lab-check` not in `make test`

**Decision**: `make lab-check` is a standalone Makefile target only. `make test` (pytest suite)
remains Docker-free.

**Rationale**: Confirmed by spec clarification Q1. The pytest suite must pass on any machine
with Python 3.12 and the venv — no Docker dependency. `make lab-check` is called separately
in CI, on a runner that has Docker available, after `make test` passes.

**Alternatives considered**: pytest marker `@pytest.mark.docker` with `skipif` — rejected
because it still requires Docker on the test host for the marked tests to run, creating a
conditional dependency that complicates CI matrix.
