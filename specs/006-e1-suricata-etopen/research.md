# Research: Suricata + ET Open Ruleset (F05)

**Branch**: `006-e1-suricata-etopen` | **Date**: 2026-07-02 | **Plan**: [plan.md](plan.md)

## Decision 1 — Suricata Docker Image Strategy

**Decision**: Build a custom `lab/Dockerfile.suricata` from `jasonish/suricata:7.0.5`
(the upstream Suricata community image pinned to the `7.0.5` tag).

**Rationale**: The `jasonish/suricata` image is the de-facto standard for running Suricata
in Docker. Pinning `7.0.5` by tag gives a deterministic Suricata binary. Building our own
derived image lets us bake the ET Open rules in at image-build time (Constitution Principle
II), eliminating all runtime internet access. The `latest` tag was explicitly ruled out per
the spec clarification.

**Alternatives considered**:
- `FROM suricata/suricata:7.0.5` — official image, fewer community fixes; rejected.
- Compile from source — maximally reproducible but weeks of work; overkill for Phase 1.
- Runtime ruleset download — violates Constitution Principle II; rejected.

---

## Decision 2 — ET Open Ruleset Pinning

**Decision**: Download the ET Open ruleset tarball for Suricata 7.0.5 inside the Dockerfile
`RUN` step using the URL:
`https://rules.emergingthreats.net/open/suricata-7.0.5/emerging.rules.tar.gz`
followed by a `sha256sum` verification against a known hash determined at image-build time
and stored in a comment beside the `ADD` instruction. The image tag acts as the external pin:
the same Docker image tag always contains the same ruleset snapshot.

**Rationale**: Emergingthreats.net publishes a stable tarball URL for each Suricata version.
By downloading once during `docker build` and baking the rules into the layer, `make lab-up`
never fetches rules from the internet. The `sha256` check inside the `RUN` step catches
accidental rule changes between builds. The ruleset version is recorded as a container label
(`LABEL ruleset_version=<date-of-build-download>`), readable via `docker inspect`.

**Alternatives considered**:
- Check rules tar into the repo — file is ~250 MB; would bloat the repository; rejected.
- Use `suricata-update` at container runtime — requires internet access at `make lab-up`;
  violates Constitution Principle II; rejected.
- Docker BuildKit `--checksum` on `ADD` — cleaner syntax but requires BuildKit to be active
  everywhere; `RUN` + `sha256sum` is equivalent and universally compatible.

---

## Decision 3 — Bridge Interface: Fixed Name for Suricata af-packet

**Decision**: Add `driver_opts: {com.docker.network.bridge.name: aatf-lab-br}` to the
`lab` network definition in `lab/docker-compose.yml`. Suricata is configured to listen on
the `aatf-lab-br` interface.

**Rationale**: Docker normally names bridge interfaces `br-<first-12-chars-of-network-id>`.
The network ID changes on every `docker network create`, making the bridge name
non-deterministic across environments. Setting `com.docker.network.bridge.name` to a
fixed string gives Suricata a stable, config-file-addressable interface name with no
runtime discovery step. This is the standard approach for Dockerised IDS deployments.

**Alternatives considered**:
- Runtime bridge discovery via `ip link show type bridge | grep br-` — fragile; fails if
  multiple bridges exist or if the interface race-conditions at start; rejected.
- Docker socket mount for `docker network inspect` inside Suricata — grants container access
  to Docker daemon; security risk; rejected.
- Macvlan / ipvlan network — captures L2 traffic but requires more complex Compose setup
  and host kernel support; overkill for Phase 1; rejected.

---

## Decision 4 — Suricata Network Mode

**Decision**: Run the Suricata container with `network_mode: host`. Suricata listens on
the `aatf-lab-br` host bridge interface using `af-packet`.

**Rationale**: Docker's bridge networking forwards unicast frames only to the destination
veth port. A Suricata container placed on `aatf-lab` as a peer cannot see traffic flowing
between `aatf-attacker` and `aatf-defender` — those frames never traverse Suricata's
veth. Host network mode lets Suricata access the host bridge interface directly, seeing all
frames forwarded by the Linux bridge regardless of their destination. Suricata is a passive
observer: it captures but does not route, so adding it with `network_mode: host` does not
introduce a new network path or external connectivity.

**Constitution Principle I compliance**: The experiment containers (attacker, defender,
environment) remain on `internal: true` `aatf-lab`. Suricata is passive monitoring
infrastructure, not an experiment participant. It does not relay traffic and does not
initiate connections (all runtime internet access is eliminated in Decision 2). This is a
justified exception documented in the plan's Complexity Tracking.

**Alternatives considered**:
- `cap_add: [NET_ADMIN, NET_RAW]` + promisc mode — containers with promisc `eth0` still
  only receive frames the Linux bridge forwards to their veth; not sufficient; rejected.
- Suricata as IPS "bump in the wire" (NFQ mode) — routes all traffic through Suricata;
  significantly more complex Compose topology; rejected for Phase 1 scope.
- tcpdump on host + PCAP replay to Suricata — adds a host dependency and latency; rejected.

---

## Decision 5 — eve.json Shared Volume

**Decision**: Use a named Docker volume `aatf-eve` mounted at `/var/log/suricata/` in
the Suricata container and at `/srv/eve/` in the attacker, defender, and environment
containers. Suricata writes `eve.json` to `/var/log/suricata/eve.json`; the smoke test
reads it from `/srv/eve/eve.json` via attacker's mount.

**Note**: Because Suricata uses `network_mode: host`, it does NOT participate in Docker's
volume attachment via the Compose service definition the same way. Instead, the named volume
is mounted explicitly: `docker run --volume aatf-eve:/var/log/suricata suricata-service`.
This is handled by the `volumes:` key in the Compose suricata service definition (volume
mounts work independently of `network_mode`).

**Rationale**: Named volumes persist across container restarts within a lab session and are
cleared on `make lab-down` (`docker volume rm` is added to the `lab-down` target). This
matches the spec edge case: "eve.json is cleared on each lab-down + lab-up cycle." The
`/srv/eve/` mount point avoids conflicts with attacker/defender container workdirs.

**Alternatives considered**:
- Bind-mount to host path (`./logs/eve.json`) — simpler but creates host filesystem
  side-effects that complicate `make lab-down` cleanup; also pollutes the repo directory; rejected.
- tmpfs — data lost on container restart, not useful for post-mortem reads; rejected.

---

## Decision 6 — Smoke Test Probe and SID

**Decision**: The smoke test sends a TCP SYN port scan from the attacker container using
`nmap` (installed in a custom `lab/Dockerfile.attacker` derived from `alpine:3.19`). The
probe: `nmap -sS -p 1-1024 --min-rate 500 aatf-defender`. This generates >500 TCP SYN
packets per second to ports 1–1024, reliably triggering ET SCAN mass-scan detection rules.

**Target SID**: The exact SID is determined during implementation by running the probe
against the pinned ET Open ruleset and recording the first SID that fires. That SID is
then hardcoded in `lab/scripts/lab-smoke.sh` and documented in the quickstart. A typical
candidate is within the `ET SCAN` category (e.g., SIDs in the `200xxxx` range covering
mass SYN scans or Nmap detection). The smoke test exits 0 only when that specific SID
appears in `eve.json` within 10 seconds.

**Rationale**: nmap `--min-rate 500 -p 1-1024` generates enough traffic to trigger
threshold-based ET SCAN rules (most require 20+ SYNs/second to ports 0–1024 from one
source). This does not require any port to be open on the defender. nmap is available in
the Alpine package repository as `apk add nmap`. The approach uses only defanged network
traffic (no real exploit payload — just TCP SYN probes).

**Alternatives considered**:
- `curl` with Nmap scripting user-agent — requires defender to serve HTTP on port 80; adds
  a service dependency; rejected for simplicity.
- Shellshock / real HTTP exploits — violates Constitution Principle I (real exploit
  payload); explicitly rejected.
- ICMP ping sweep — requires multiple target IPs; single attacker → single defender ping
  is unlikely to trigger threshold-based sweep rules; rejected.

---

## Decision 7 — SID Disable Hook

**Decision**: `lab/rules/disabled.conf` is a plain-text file with one SID per line
(integers, blank lines and `#` comments ignored). A `lab/suricata/docker-entrypoint.sh`
startup script reads `disabled.conf` and generates Suricata `threshold.conf` suppress
entries:
```
suppress gen_id 1, sig_id <SID>, track by_any, ip any
```
Suricata is then invoked with `--threshold-file /etc/suricata/threshold.conf`. The
generated threshold.conf is created at container startup; no rebuild required for SID
disable/enable — only a `make lab-down && make lab-up`.

**Rationale**: Suricata's native `threshold.conf` suppress mechanism is the documented,
version-stable way to silence specific SIDs without editing rule files. The disable config
is a simple text file in the repo, version-controlled, human-readable, and empty by
default (FR-007). F22 will populate this file to create deliberate blind spots for
ground-truth validation. Converting on entrypoint startup means the container image never
needs rebuilding when SID sets change — only a lab restart is required.

**Alternatives considered**:
- Comment out rules in the `.rules` files — requires rebuilding the image or editing files
  inside a running container; not version-controlled; rejected.
- `suricata-update --disable-conf` — requires suricata-update installed in image;
  adds a dependency; overly complex for one-file disable list; rejected.
- Suricata `disable-detection` CLI flag (single SID only) — not suitable for lists; rejected.
