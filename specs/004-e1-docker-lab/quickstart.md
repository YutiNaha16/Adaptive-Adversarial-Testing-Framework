# Quickstart: 004-e1-docker-lab

Five end-to-end scenarios. All require Docker Engine + Compose V2 installed.
Run from repo root.

---

## SC-001 — Full lifecycle (cold start → verify → teardown)

```bash
# Bring up the lab (pulls alpine:3.19, creates network, starts 3 containers)
make lab-up
# Expected: exits 0; prints container start confirmations

# Verify isolation
make lab-check
# Expected: exits 0; prints "ISOLATED: Outbound connection to 8.8.8.8:53 blocked"

# Check status
make lab-status
# Expected: exits 0; prints each container (aatf-attacker, aatf-defender, aatf-environment)
#           as "running", overall state "running"

# Tear down cleanly
make lab-down
# Expected: exits 0; no containers or network remain

# Confirm clean
docker ps -a | grep aatf    # → no output
docker network ls | grep aatf  # → no output
```

**Validates**: FR-001, FR-002, FR-003, FR-005, SC-001, SC-002, SC-005

---

## SC-002 — Isolation breach detection (deliberate misconfiguration)

This scenario tests that `make lab-check` correctly detects a misconfigured lab.

```bash
# Temporarily edit lab/docker-compose.yml — remove or comment out `internal: true`
# Then bring up the (misconfigured) lab
make lab-up

# Run isolation check — MUST detect the breach
make lab-check
# Expected: exits 1; prints "BREACH: Outbound connection to 8.8.8.8:53 succeeded"
#           to stderr. CI step MUST fail.

# Restore correct config and tear down
make lab-down
# Revert the docker-compose.yml change
```

**Validates**: FR-005, SC-002, FR-001 (breach path)

---

## SC-003 — Idempotent bring-up (start twice in a row)

```bash
make lab-up
make lab-up   # second call — must not error or create duplicate resources

make lab-status
# Expected: exits 0; still exactly 3 containers, exactly 1 network

make lab-down
```

**Validates**: FR-004, SC-003 (partial), FR-002 idempotency

---

## SC-004 — Cycle stability (up/down repeated 3 times)

```bash
for i in 1 2 3; do
    make lab-up
    make lab-check   # must exit 0 each time
    make lab-down
done

docker ps -a | grep aatf   # → no output after final teardown
docker network ls | grep aatf  # → no output
```

**Validates**: SC-003, FR-003, SC-004

---

## SC-005 — Degraded state detection

```bash
make lab-up

# Force-kill one container
docker kill aatf-defender

# Check status — must report degraded
make lab-status
# Expected: exits 2; output identifies "aatf-defender" as failed,
#           overall state "degraded"

make lab-down  # clean up even in degraded state
```

**Validates**: US3 acceptance scenario 3, FR-003 (teardown from degraded state)
