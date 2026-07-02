# Data Model: Suricata + ET Open Ruleset (F05)

**Branch**: `006-e1-suricata-etopen` | **Date**: 2026-07-02 | **Plan**: [plan.md](plan.md)

This feature is infrastructure-only (shell scripts, Docker config, Makefile). There are no
new Python modules or Pydantic models. The data model here describes the **file-system and
runtime artifacts** that F05 introduces.

---

## Entity 1 — Suricata Container Service

**What it is**: A Docker service running Suricata 7.0.5 with the pinned ET Open ruleset.

**Runtime identity**:
- Container name: `aatf-suricata`
- Network mode: `host` (sees all bridge traffic on `aatf-lab-br`)
- Image: `aatf-suricata:7.0.5` (built from `lab/Dockerfile.suricata`)

**Key labels** (on the built image):
| Label | Example value | Purpose |
|-------|--------------|---------|
| `suricata_version` | `7.0.5` | Recorded in run manifests (F03 field) |
| `ruleset_version` | `20260702` | Recorded in run manifests (F03 field) |
| `build_date` | `2026-07-02` | Traceability |

**State lifecycle**:
```
absent → starting (make lab-up) → running/healthy → stopped (make lab-down)
```

**Validation rules**:
- Must reach `running` state before `make lab-up` exits (health check: `suricata --build-info`)
- `aatf-lab-br` bridge interface must exist before Suricata starts (depends_on ordering or
  startup retry in entrypoint)

---

## Entity 2 — eve.json Alert Record

**What it is**: A single JSON line emitted by Suricata to `/var/log/suricata/eve.json`
when a detection rule fires.

**Relevant fields** (subset used by smoke test and future F11 parser):

| Field | Type | Always present | Notes |
|-------|------|---------------|-------|
| `timestamp` | string (ISO8601) | Yes | Alert emission time |
| `event_type` | string | Yes | `"alert"` for rule-triggered events |
| `alert.signature_id` | integer | When `event_type=alert` | The SID that fired |
| `alert.signature` | string | When `event_type=alert` | Human-readable rule message |
| `alert.category` | string | When `event_type=alert` | Rule category (e.g. "ET SCAN") |
| `alert.severity` | integer | When `event_type=alert` | Suricata severity level (1–3) |
| `src_ip` | string | Yes | Source IP of the triggering packet |
| `dest_ip` | string | Yes | Destination IP |
| `proto` | string | Yes | `"TCP"`, `"UDP"`, `"ICMP"` |

**Volume location**:
- Written by Suricata: `/var/log/suricata/eve.json` (inside Suricata container)
- Read by smoke test: `/srv/eve/eve.json` (inside attacker container, same named volume)
- Named Docker volume: `aatf-eve`

**Lifecycle**:
- Created: when first alert fires after `make lab-up`
- Cleared: volume removed on `make lab-down`
- Format: newline-delimited JSON (one JSON object per line)

---

## Entity 3 — Disabled Rules Config

**What it is**: A plain-text file declaring Suricata SIDs to suppress.

**File path**: `lab/rules/disabled.conf`
**Mount path inside Suricata container**: `/lab-rules/disabled.conf`

**Format**:
```
# Lines beginning with # are comments (ignored)
# Blank lines are ignored
# One SID (integer) per non-comment, non-blank line

# Example — disable ET SCAN mass scan rule during F22 blind-spot experiment:
# 2034660
```

**Default state**: Empty file (no SIDs disabled out of the box, per FR-007).

**Processing**:
The `docker-entrypoint.sh` in the Suricata container reads this file at startup and
generates `/etc/suricata/threshold.conf` with `suppress` entries:
```
suppress gen_id 1, sig_id <SID>, track by_any, ip any
```
Suricata is started with `--threshold-file /etc/suricata/threshold.conf`.

**Validation rules**:
- Each non-comment, non-blank line MUST be a positive integer (SID)
- Invalid lines cause the entrypoint to log a warning and skip (not abort)

---

## Entity 4 — Smoke Test Result

**What it is**: The exit status and output of `make lab-smoke` / `lab/scripts/lab-smoke.sh`.

**Not a file artifact** — result is expressed through exit code and stdout.

| Outcome | Exit code | Stdout contains |
|---------|-----------|----------------|
| SID found within timeout | `0` | `SMOKE PASS: SID <N> detected at <timestamp>` |
| Lab not running | `1` | `ERROR: lab is not running (aatf-attacker absent)` |
| SID not found in timeout | `1` | `SMOKE FAIL: SID <N> not found within <T>s` |
| Probe command failed | `1` | `ERROR: probe failed: <reason>` |

**Target SID** (determined during implementation, hardcoded in `lab/scripts/lab-smoke.sh`):
- Placeholder: `TARGET_SID` constant at top of script
- Category: ET SCAN (confirmed against pinned ruleset during implementation)

---

## Entity 5 — Attacker Container (updated)

**What it is**: The updated `aatf-attacker` container, now built from a custom Dockerfile
(`lab/Dockerfile.attacker`) that adds `nmap` to the base `alpine:3.19` image.

**Change from F04**: Previously used `image: alpine:3.19` directly. F05 introduces a
Dockerfile so that `nmap` (the smoke test probe tool) is available in the container.

**Key installed tools** (additions over base alpine:3.19):
- `nmap` — for smoke test TCP SYN scan probe

**Image tag**: `aatf-attacker:f05` (or `aatf-attacker:latest`) — rebuilt on `make lab-up`
with `docker compose build`.

---

## File Tree (F05 new files)

```text
lab/
├── Dockerfile.suricata          # Suricata 7.0.5 + baked ET Open rules
├── Dockerfile.attacker          # alpine:3.19 + nmap
├── suricata/
│   ├── suricata.yaml            # Suricata config (af-packet on aatf-lab-br, eve.json output)
│   └── docker-entrypoint.sh    # Reads disabled.conf, generates threshold.conf, starts Suricata
└── rules/
    └── disabled.conf            # Empty by default; one SID per line to suppress

lab/scripts/
└── lab-smoke.sh                 # Sends nmap probe from attacker, waits for SID in eve.json

lab/docker-compose.yml           # +suricata service +bridge name +aatf-eve volume
                                 # +attacker build context (Dockerfile.attacker)
Makefile                         # +lab-smoke target, updated lab-status (4 containers),
                                 # updated lab-down (remove aatf-suricata + aatf-eve volume)
```

## No New Python Entities

F05 introduces no new Python modules, no Pydantic models, and no changes to `src/aatf/`.
The `suricata_version` and `ruleset_version` fields already exist in `RunManifest` (F03)
and are populated when an experiment run queries the container labels. That population is
deferred to F11/F15 (the eve.json adapter and feedback collector).
