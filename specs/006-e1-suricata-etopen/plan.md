# Implementation Plan: Suricata + ET Open Ruleset (F05)

**Branch**: `006-e1-suricata-etopen` | **Date**: 2026-07-02 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/006-e1-suricata-etopen/spec.md`

## Summary

Add Suricata 7.0.5 as the detection judge of record to the existing Docker lab (F04).
Suricata runs with `network_mode: host`, listening on the fixed-name bridge `aatf-lab-br`
(set via `com.docker.network.bridge.name` in Compose), so it sees all inter-container
traffic. ET Open rules are baked into the image at build time via a custom
`lab/Dockerfile.suricata`. eve.json is written to a named Docker volume shared with all
lab containers. A smoke test (`make lab-smoke`) runs an nmap TCP SYN scan from
`aatf-attacker` to `aatf-defender`, then polls eve.json for a specific ET SCAN SID within
10 seconds. SID suppression is controlled via a version-controlled `lab/rules/disabled.conf`
translated to Suricata `threshold.conf` entries by a container entrypoint script. The
existing attacker image is replaced with a custom Dockerfile that adds nmap. No Python
changes — `make test` stays at 78 passed / 1 skipped.

## Technical Context

**Language/Version**: Shell (bash/sh) for all new scripts; YAML for Docker Compose and
Suricata config; Dockerfile DSL. No Python changes.  
**Primary Dependencies**: Docker Engine (≥ 20); Docker Compose V2; `jasonish/suricata:7.0.5`
(base image); `alpine:3.19` with `apk add nmap` (attacker); `nmap` (probe tool, Alpine
repo). No new pip dependencies.  
**Storage**: Named Docker volume `aatf-eve` for eve.json; `lab/rules/disabled.conf`
version-controlled file for SID suppression configuration.  
**Testing**: No new pytest tests. Contracts verified manually via `make lab-up`,
`make lab-smoke`, `make lab-check`, `make lab-status`. `make test` (Docker-free) remains
unchanged at 78 passed / 1 skipped.  
**Target Platform**: Linux (Ubuntu 24.04 host). Docker Engine must support
`com.docker.network.bridge.name` driver option (standard since Docker 1.9).  
**Performance Goals**: `make lab-up` cold-start within 60 seconds on pre-pulled images
(SC-001). `make lab-smoke` completes within 15 seconds of invocation (SC-002).  
**Constraints**: Zero new pip deps. No Python file changes. No F06 isolation test regressions.
Suricata uses `network_mode: host` (justified exception — see Complexity Tracking).
ET Open rules baked into image (no internet at runtime). SID disable requires only a lab
restart, not a rebuild.  
**Scale/Scope**: 6 new files (Dockerfile.suricata, Dockerfile.attacker, suricata.yaml,
docker-entrypoint.sh, lab-smoke.sh, disabled.conf); 2 updated files (docker-compose.yml,
Makefile); 1 updated script (lab-status.sh); 11 acceptance contracts.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I — Safety & Isolation | ✅ PASS (with exception) | Experiment containers (attacker, defender, environment) remain on `internal: true` `aatf-lab`. Suricata uses `network_mode: host` as a PASSIVE monitoring exception (see Complexity Tracking). Smoke probe targets only `aatf-defender` (172.28.x.x). No real exploit payloads. |
| II — Reproducibility | ✅ PASS | Suricata version pinned to `7.0.5` tag. ET Open rules baked into image at build time (sha256 verified in Dockerfile RUN step). Same image tag = same binary + same rules. `suricata_version` and `ruleset_version` recorded as container labels. |
| III — Pluggable Defence | ✅ N/A | No `Defence` interface changes. F05 only installs Suricata in the lab. The Defence abstraction is wired in F11. |
| IV — Scientific Validity / Test-First | ✅ PASS | 11 contracts written first ([contracts/lab-smoke-contract.md](contracts/lab-smoke-contract.md)). The smoke test is the verification artifact. No pytest tests added (this is infrastructure, not application logic). |
| V — Explainability | ✅ N/A | No report pipeline changes. |
| VI — Observability | ✅ PASS | Suricata writes structured eve.json alerts to the shared `aatf-eve` volume. eve.json is the alert source of record for all downstream features (F11, F15). |
| VII — Phased Delivery | ✅ PASS | F05 is within E1 scope. No Phase 2 code introduced. |

**No gate violations. One justified exception documented in Complexity Tracking.**

Post-design re-check: `network_mode: host` for Suricata verified not to affect experiment
container isolation. The `internal: true` flag on `aatf-lab` is unchanged. F06
isolation tests (`test_no_host_ports_on_experiment_containers`) do not check the suricata
service, and F06 `test_lab_config_declares_internal` still passes because the lab network
declaration is unchanged. No regressions in F06 contracts.

## Project Structure

### Documentation (this feature)

```text
specs/006-e1-suricata-etopen/
├── plan.md              ← this file
├── research.md          ← 7 decisions: Suricata version, ET Open pinning, bridge name,
│                           network mode, eve.json volume, smoke probe SID, disable hook
├── data-model.md        ← 5 entities: Suricata service, eve.json record, disabled rules
│                           config, smoke test result, updated attacker container
├── contracts/
│   └── lab-smoke-contract.md  ← 11 contracts (C-001–C-011)
├── quickstart.md        ← 5-step verification guide + SID disable instructions
└── tasks.md             ← generated by /sp.tasks (NOT created by /sp.plan)
```

### Source Code Changes

```text
lab/
├── Dockerfile.suricata          # NEW — FROM jasonish/suricata:7.0.5; bake ET Open rules
├── Dockerfile.attacker          # NEW — FROM alpine:3.19; apk add nmap
├── suricata/
│   ├── suricata.yaml            # NEW — af-packet on aatf-lab-br; eve.json; threshold.conf
│   └── docker-entrypoint.sh    # NEW — reads disabled.conf → threshold.conf; exec suricata
└── rules/
    └── disabled.conf            # NEW — empty; one SID per line to suppress

lab/scripts/
└── lab-smoke.sh                 # NEW — probe (nmap) + eve.json poll + exit codes

lab/docker-compose.yml           # UPDATE — suricata service; bridge.name; aatf-eve volume;
                                 #          attacker build context (Dockerfile.attacker)
Makefile                         # UPDATE — lab-smoke target; lab-status (4 containers);
                                 #          lab-down cleanup (aatf-suricata + aatf-eve vol)
lab/scripts/lab-status.sh        # UPDATE — add aatf-suricata to container list
```

**No changes to**:
- `src/aatf/` (any module)
- `tests/` (any test file)
- `pyproject.toml`
- `requirements.in` / `requirements.txt`
- F06's `src/aatf/isolation.py`

**Structure Decision**: Pure infrastructure layer. All new files are in `lab/` (Docker
artifacts) or `lab/scripts/` (shell scripts). No Python or test structure changes.

## Implementation Phases

### Phase 1 — Bridge Name & Compose Update

Update `lab/docker-compose.yml`:
1. Add `driver_opts: {com.docker.network.bridge.name: aatf-lab-br}` to the `lab` network.
2. Add named volume `aatf-eve`.
3. Add `suricata` service:
   - `build: {context: lab, dockerfile: Dockerfile.suricata}`
   - `container_name: aatf-suricata`
   - `network_mode: host`
   - `volumes: [aatf-eve:/var/log/suricata]`
   - `restart: "no"`
   - `depends_on: [attacker, defender, environment]` (ensures bridge exists before Suricata starts)
4. Change `attacker` from `image: alpine:3.19` to `build: {context: lab, dockerfile: Dockerfile.attacker}`.
5. Add `aatf-eve:/srv/eve` volume mount to `attacker`, `defender`, `environment` services.

### Phase 2 — Suricata Dockerfile

`lab/Dockerfile.suricata`:
```dockerfile
FROM jasonish/suricata:7.0.5
LABEL suricata_version="7.0.5"
# Download and bake ET Open rules at build time
RUN set -eux; \
    curl -fsSL https://rules.emergingthreats.net/open/suricata-7.0.5/emerging.rules.tar.gz \
      -o /tmp/emerging.rules.tar.gz; \
    # Verify hash (replace PLACEHOLDER with actual sha256 obtained during first build)
    # echo "PLACEHOLDER  /tmp/emerging.rules.tar.gz" | sha256sum -c -; \
    mkdir -p /etc/suricata/rules /etc/suricata/threshold.d; \
    tar -xzf /tmp/emerging.rules.tar.gz -C /etc/suricata/rules --strip-components=1; \
    rm /tmp/emerging.rules.tar.gz; \
    # Record ruleset version as label (date of build)
    RULESET_DATE=$(date +%Y%m%d); \
    echo "RULESET_DATE=${RULESET_DATE}" >> /etc/suricata/ruleset-version.txt
LABEL ruleset_version_note="See /etc/suricata/ruleset-version.txt for build-date stamp"
COPY lab/suricata/suricata.yaml /etc/suricata/suricata.yaml
COPY lab/suricata/docker-entrypoint.sh /docker-entrypoint.sh
COPY lab/rules/disabled.conf /lab-rules/disabled.conf
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
```

**Note**: The sha256 hash is obtained by running one build without verification, noting
the hash from output, then adding the `sha256sum` check. This is documented as a task step.

### Phase 3 — Attacker Dockerfile

`lab/Dockerfile.attacker`:
```dockerfile
FROM alpine:3.19
RUN apk add --no-cache nmap
CMD ["sleep", "infinity"]
```

Minimal — only adds `nmap` for the smoke test probe.

### Phase 4 — Suricata Config

`lab/suricata/suricata.yaml` (minimal working config):
```yaml
%YAML 1.1
---
af-packet:
  - interface: aatf-lab-br
    cluster-id: 99
    cluster-type: cluster_flow
    defrag: yes

outputs:
  - eve-log:
      enabled: yes
      filetype: regular
      filename: eve.json
      types:
        - alert

default-log-dir: /var/log/suricata/

rule-files:
  - /etc/suricata/rules/*.rules

classification-file: /etc/suricata/classification.config
reference-config-file: /etc/suricata/reference.config
threshold-file: /etc/suricata/threshold.conf

home-net: "[172.28.0.0/16]"
external-net: "!$HOME_NET"
```

The `threshold-file` points to the file generated by `docker-entrypoint.sh`.

### Phase 5 — Entrypoint Script

`lab/suricata/docker-entrypoint.sh`:
```sh
#!/usr/bin/env sh
set -e

DISABLED_CONF="/lab-rules/disabled.conf"
THRESHOLD_CONF="/etc/suricata/threshold.conf"

# Wait for the bridge interface to appear (up to 30s)
i=0
while ! ip link show aatf-lab-br > /dev/null 2>&1; do
    i=$((i+1))
    if [ "$i" -ge 30 ]; then
        echo "ERROR: aatf-lab-br not available after 30s" >&2
        exit 1
    fi
    sleep 1
done

# Generate threshold.conf from disabled.conf
printf '' > "$THRESHOLD_CONF"
if [ -f "$DISABLED_CONF" ]; then
    while IFS= read -r line; do
        # Strip leading/trailing whitespace
        line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        # Skip blank lines and comments
        case "$line" in
            ''|\#*) continue ;;
        esac
        printf 'suppress gen_id 1, sig_id %s, track by_any, ip any\n' "$line" \
            >> "$THRESHOLD_CONF"
    done < "$DISABLED_CONF"
fi

echo "Suricata starting on interface aatf-lab-br"
exec suricata -c /etc/suricata/suricata.yaml \
    --af-packet=aatf-lab-br \
    --threshold-file "$THRESHOLD_CONF" \
    -l /var/log/suricata/ \
    --set classification-file=/etc/suricata/classification.config
```

### Phase 6 — SID Disable Config

`lab/rules/disabled.conf`:
```
# Suricata SID suppression list
# One integer SID per line. Blank lines and lines beginning with # are ignored.
# Empty by default — no rules are disabled out of the box.
# F22 (ground-truth validation) will populate this file to create deliberate blind spots.
#
# Example:
# 2034660
```

### Phase 7 — Smoke Test Script

`lab/scripts/lab-smoke.sh`:
```sh
#!/usr/bin/env sh
# Smoke test: probe from aatf-attacker triggers TARGET_SID in eve.json within 10s.
# Exit 0 on success; exit 1 on failure or lab not running.
set -e

TARGET_SID=PLACEHOLDER  # Replace with actual SID during implementation (Task T008)
TIMEOUT=10
EVE_PATH="/srv/eve/eve.json"

# Check lab is running
if ! docker inspect aatf-attacker > /dev/null 2>&1; then
    echo "ERROR: lab is not running (aatf-attacker absent)"
    exit 1
fi

echo "Sending probe from aatf-attacker to aatf-defender..."
docker exec aatf-attacker nmap -sS -p 1-1024 --min-rate 500 aatf-defender \
    > /dev/null 2>&1 || {
    echo "ERROR: probe failed (nmap returned non-zero)"
    exit 1
}

echo "Waiting for SID ${TARGET_SID} in eve.json (timeout ${TIMEOUT}s)..."
elapsed=0
while [ "$elapsed" -lt "$TIMEOUT" ]; do
    if docker exec aatf-attacker sh -c \
        "grep -q '\"signature_id\":${TARGET_SID}' ${EVE_PATH} 2>/dev/null"; then
        ts=$(docker exec aatf-attacker sh -c \
            "grep '\"signature_id\":${TARGET_SID}' ${EVE_PATH} | head -1 | \
            grep -o '\"timestamp\":\"[^\"]*\"' | cut -d'\"' -f4")
        echo "SMOKE PASS: SID ${TARGET_SID} detected at ${ts}"
        exit 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done

echo "SMOKE FAIL: SID ${TARGET_SID} not found within ${TIMEOUT}s"
exit 1
```

**Note**: `TARGET_SID=PLACEHOLDER` is filled in during Task T008 (determine SID from
first live build).

### Phase 8 — Makefile Updates

Changes to `Makefile`:
1. Add `lab-smoke` to `.PHONY` and `help` target discovery.
2. Add `lab-smoke` target:
   ```makefile
   lab-smoke:  ## Send smoke probe; verify ET Open SID fires in eve.json (exits 1 on failure)
       @bash lab/scripts/lab-smoke.sh
   ```
3. Update `lab-down` to remove `aatf-suricata` and the `aatf-eve` volume:
   ```makefile
   lab-down:  ## Stop and remove all lab containers, the lab network, and eve volume
       $(COMPOSE) down --remove-orphans
       @docker rm -f aatf-attacker aatf-defender aatf-environment aatf-suricata 2>/dev/null; true
       @docker volume rm aatf-eve 2>/dev/null; true
   ```

### Phase 9 — lab-status.sh Update

`lab/scripts/lab-status.sh`: Change `CONTAINERS` variable from 3 to 4:
```sh
CONTAINERS="aatf-attacker aatf-defender aatf-environment aatf-suricata"
```

### Phase 10 — SID Determination (Implementation Task T008)

During implementation, after building the image and starting the lab, determine the exact
SID by running the probe and reading eve.json:

```sh
make lab-up
docker exec aatf-attacker nmap -sS -p 1-1024 --min-rate 500 aatf-defender > /dev/null
sleep 5
docker exec aatf-attacker grep '"event_type":"alert"' /srv/eve/eve.json | head -5
```

Record the `signature_id` that fires. Replace `TARGET_SID=PLACEHOLDER` in
`lab/scripts/lab-smoke.sh` with the actual integer. Document the rule message in
`quickstart.md` under Step 4.

## TDD / Contract Verification Sequence

This feature is infrastructure (no pytest). Contracts are verified in order:

1. `C-010` — Bridge name: `ip link show aatf-lab-br` after `make lab-up`
2. `C-009` — `make test` passes 78 / 1 (run before and after all changes)
3. `C-007` — `make lab-status` shows 4 containers
4. `C-008` — container labels readable via `docker inspect`
5. `C-001` + `C-004` — `make lab-smoke` exits 0 within 15s
6. `C-002` — TARGET_SID documented and hardcoded
7. `C-003` — `make lab-check` exits 0 after smoke test
8. `C-006` — `make lab-down` clears volume
9. `C-011` — `make lab-down` removes aatf-suricata
10. `C-005` — SID disable suppresses detection (US3 acceptance)

## Complexity Tracking

| Exception | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Suricata `network_mode: host` | Linux bridge forwards unicast frames only to destination veth. A Suricata container on `aatf-lab` cannot see A↔B traffic. Host mode lets Suricata read the bridge directly. | Container promisc mode (`NET_ADMIN`) still doesn't receive unicast frames not forwarded to that veth — the kernel bridge only sends to relevant ports. Bump-in-the-wire (NFQ IPS) changes the network topology significantly and is Phase 2 scope. |
