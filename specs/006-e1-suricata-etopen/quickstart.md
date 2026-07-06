# Quickstart: Suricata + ET Open Ruleset (F05)

**Feature**: F05 — Suricata + ET Open Ruleset  
**Branch**: `006-e1-suricata-etopen`  
**Date**: 2026-07-02

## Prerequisites

- Docker Engine ≥ 20 with Compose V2 plugin (`docker compose`)
- `make` available
- Lab images built: `make lab-up` (builds `aatf-suricata:7.0.5` and `aatf-attacker:f05`
  on first run; subsequent runs use the cached layers)

## 5-Step Verification

### Step 1 — Start the lab

```sh
make lab-up
```

Expected output: Compose starts 4 containers. All reach `running` state within 60 seconds.

```
[+] Running 4/4
 ✔ Container aatf-attacker     Started
 ✔ Container aatf-defender     Started
 ✔ Container aatf-environment  Started
 ✔ Container aatf-suricata     Started
```

### Step 2 — Verify lab status (4 containers)

```sh
make lab-status
```

Expected:
```
  aatf-attacker          running
  aatf-defender          running
  aatf-environment       running
  aatf-suricata          running
Lab state: running (4/4 containers up)
```

### Step 3 — Read Suricata + ruleset versions

```sh
docker inspect aatf-suricata \
  --format 'suricata_version={{index .Config.Labels "suricata_version"}}  ruleset_version={{index .Config.Labels "ruleset_version"}}'
```

Expected:
```
suricata_version=7.0.5  ruleset_version=<build-date e.g. 20260702>
```

### Step 4 — Run smoke test

```sh
make lab-smoke
```

Expected (exit 0):
```
Sending probe from aatf-attacker to aatf-defender (6 SYN probes to port 22)...
Waiting for SID 2001219 in eve.json (timeout 30s)...
SMOKE PASS: SID 2001219 (ET SCAN Potential SSH Scan) detected at <timestamp>
```

The target SID is hardcoded in `lab/scripts/lab-smoke.sh` as `TARGET_SID=2001219`.
The fired rule is: **"ET SCAN Potential SSH Scan"** (SID 2001219) — a threshold-based
SSH SYN scan detection rule from the ET Open ruleset (`emerging-scan.rules`), triggered
by 6 successive nmap SYN probes to port 22. No real exploit payloads involved.

### Step 5 — Stop the lab

```sh
make lab-down
```

Expected: all 4 containers removed, `aatf-eve` volume removed, `aatf-lab-br` bridge
destroyed.

---

## SID Disable Hook

To suppress a rule during an experiment (used by F22 ground-truth validation):

```sh
# 1. Add the SID to the disabled rules file (one integer per line)
echo "2034660" >> lab/rules/disabled.conf

# 2. Restart the lab to apply the change
make lab-down && make lab-up

# 3. Confirm suppression (smoke test should FAIL if you disabled TARGET_SID)
make lab-smoke

# 4. Re-enable: remove the SID from disabled.conf, restart
```

`lab/rules/disabled.conf` supports:
- Blank lines (ignored)
- Lines starting with `#` (comments, ignored)
- One integer SID per non-comment, non-blank line

---

## Isolation Check

Run after smoke test to confirm the lab network remains isolated:

```sh
make lab-check
```

Expected: exits 0 with `ISOLATED`. Running `make lab-smoke` does NOT open any external
network paths — the nmap probe targets only `aatf-defender` (172.28.x.x).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `make lab-up` hangs on Suricata | `aatf-lab-br` not yet visible to host | Wait 5s; Suricata entrypoint retries. If persistent, run `ip link show aatf-lab-br` to diagnose. |
| `make lab-smoke` exits 1 — `SID not found` | Suricata not yet fully loaded rules at test time | `make lab-down && make lab-up` (cold start); wait 10s after `lab-up` before `lab-smoke`. |
| `make lab-status` shows 3/4 containers | Suricata image not built | Run `docker compose -f lab/docker-compose.yml build suricata`. |
| `eve.json` not visible at `/srv/eve/eve.json` inside attacker | Volume not mounted | Verify `volumes:` in `docker-compose.yml` for attacker service includes `aatf-eve:/srv/eve`. |
| `ip link show aatf-lab-br` returns error on host | Bridge name not applied | Check `driver_opts` in `lab/docker-compose.yml` for the `lab` network. |

---

## File Inventory (F05 additions)

| File | Purpose |
|------|---------|
| `lab/Dockerfile.suricata` | Builds `aatf-suricata:7.0.5` with pinned ET Open rules |
| `lab/Dockerfile.attacker` | Builds `aatf-attacker:f05` with `nmap` installed |
| `lab/suricata/suricata.yaml` | Suricata config: af-packet on `aatf-lab-br`, eve.json output |
| `lab/suricata/docker-entrypoint.sh` | Reads `disabled.conf`, generates `threshold.conf`, starts Suricata |
| `lab/rules/disabled.conf` | Empty file — SIDs to suppress (one per line) |
| `lab/scripts/lab-smoke.sh` | Smoke test: nmap probe + eve.json polling + exit code |
| `lab/docker-compose.yml` | +suricata service, +bridge name, +`aatf-eve` volume, +attacker build |
| `Makefile` | +`lab-smoke` target, updated `lab-status` (4 containers), updated `lab-down` |
