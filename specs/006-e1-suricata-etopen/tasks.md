# Tasks: Suricata + ET Open Ruleset (F05)

**Input**: Design documents from `specs/006-e1-suricata-etopen/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/lab-smoke-contract.md ✅

**Tests**: No new pytest tests (FR-011). Acceptance verified by running Make targets and
shell commands per the 11 contracts in `contracts/lab-smoke-contract.md`. `make test`
must remain 78 passed / 1 skipped throughout.

**Organization**: 3 user stories (US1 P1 = detection service, US2 P1 = smoke test, US3
P2 = SID disable hook) plus setup, foundational, and polish phases.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps task to user story (US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Create directory structure and record baseline state before any changes.

- [X] T001 Create `lab/suricata/` and `lab/rules/` directories (they do not exist yet — `mkdir -p lab/suricata lab/rules` from repo root)
- [X] T002 Record `make test` baseline: run `make test` and confirm output is `78 passed, 1 skipped` — document result before any implementation changes begin

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Makefile and lab-status.sh changes that are safe to apply before Suricata
exists and that prevent broken state if implementation is interrupted.

**⚠️ CRITICAL**: Complete before starting US1 implementation.

- [X] T003 [P] Update `Makefile`: (1) add `lab-smoke` to the `.PHONY` line; (2) update the `lab-down` target to also remove `aatf-suricata` and the `aatf-eve` volume: after the existing `@docker rm -f …` line add `@docker rm -f aatf-suricata 2>/dev/null; true` and `@docker volume rm aatf-eve 2>/dev/null; true`; (3) leave `lab-smoke` target body as a stub `@echo "lab-smoke: not yet implemented"` (body filled in T014)
- [X] T004 [P] Update `lab/scripts/lab-status.sh`: change line `CONTAINERS="aatf-attacker aatf-defender aatf-environment"` to `CONTAINERS="aatf-attacker aatf-defender aatf-environment aatf-suricata"` so the script reports 4 containers (total count increments automatically)

**Checkpoint**: `make lab-down` is now safe to run at any point; `make lab-status` counts 4 containers.

---

## Phase 3: User Story 1 — Detection Service in Lab (Priority: P1) 🎯 MVP

**Goal**: `make lab-up` starts 4 containers; Suricata monitors `aatf-lab-br`; eve.json
is written to the shared `aatf-eve` volume; pinned versions readable via container labels.

**Independent Test**:
```sh
make lab-up
make lab-status        # → "running (4/4 containers up)", exit 0
docker inspect aatf-suricata --format '{{index .Config.Labels "suricata_version"}}'  # → "7.0.5"
ip link show aatf-lab-br   # → bridge exists (C-010)
make lab-down
```

### Implementation for User Story 1

- [X] T005 [P] [US1] Create `lab/Dockerfile.attacker` with content: `FROM alpine:3.19`, `RUN apk add --no-cache nmap`, `CMD ["sleep", "infinity"]` — this replaces the bare `image: alpine:3.19` for the attacker service and adds `nmap` for the smoke test probe

- [X] T006 [P] [US1] Create `lab/rules/disabled.conf` with an explanatory comment header (no active SIDs): first line `# Suricata SID suppression list`, then `# One integer SID per line. Blank lines and lines beginning with # are ignored.`, then `# Empty by default — no rules are disabled out of the box.`, then `# F22 (ground-truth validation) will populate this file to create deliberate blind spots.`, then a blank line, then `# Example:`, then `# 2034660` — file must be committable (non-empty but no active entries)

- [X] T007 [P] [US1] Create `lab/suricata/suricata.yaml` with minimal working Suricata config: set `af-packet` interface to `aatf-lab-br` with `cluster-id: 99` and `cluster-type: cluster_flow`; set `default-log-dir: /var/log/suricata/`; enable `eve-log` output (filetype `regular`, filename `eve.json`, types `[alert]`); set `rule-files: [/etc/suricata/rules/*.rules]`; set `threshold-file: /etc/suricata/threshold.conf`; set `home-net: "[172.28.0.0/16]"` and `external-net: "!$HOME_NET"`; set `classification-file` and `reference-config-file` to the jasonish image defaults at `/etc/suricata/classification.config` and `/etc/suricata/reference.config`

- [X] T008 [P] [US1] Create `lab/suricata/docker-entrypoint.sh` as a POSIX sh script (`#!/usr/bin/env sh`, `set -e`): (1) wait loop for `aatf-lab-br` — poll `ip link show aatf-lab-br` every 1 second, abort with error after 30s if never appears; (2) generate `/etc/suricata/threshold.conf` from `/lab-rules/disabled.conf` — read the file line by line, skip blank lines and lines starting with `#`, for each integer SID write `suppress gen_id 1, sig_id <SID>, track by_any, ip any` to the threshold file; (3) exec `suricata -c /etc/suricata/suricata.yaml --af-packet=aatf-lab-br --threshold-file /etc/suricata/threshold.conf -l /var/log/suricata/`; mark script executable with `chmod +x`

- [X] T009 [US1] Create `lab/Dockerfile.suricata` (depends on T007 + T008): `FROM jasonish/suricata:7.0.5`; add `LABEL suricata_version="7.0.5"`; add a `RUN` step that: installs `curl` if not present, downloads `https://rules.emergingthreats.net/open/suricata-7.0.5/emerging.rules.tar.gz` to `/tmp/emerging.rules.tar.gz`, creates `/etc/suricata/rules/` and `/etc/suricata/threshold.d/`, extracts the tarball (`tar -xzf … -C /etc/suricata/rules --strip-components=1`), removes the tarball, writes a `RULESET_DATE=$(date +%Y%m%d)` to `/etc/suricata/ruleset-version.txt`; add `LABEL ruleset_version_note="see /etc/suricata/ruleset-version.txt"`; `COPY lab/suricata/suricata.yaml /etc/suricata/suricata.yaml`; `COPY lab/suricata/docker-entrypoint.sh /docker-entrypoint.sh`; `RUN mkdir -p /lab-rules && touch /lab-rules/disabled.conf`; `RUN chmod +x /docker-entrypoint.sh`; `ENTRYPOINT ["/docker-entrypoint.sh"]`

- [X] T010 [US1] Update `lab/docker-compose.yml` (depends on T005 + T009): (1) add `driver_opts: {com.docker.network.bridge.name: aatf-lab-br}` under the `lab` network's existing definition; (2) add a top-level `volumes: {aatf-eve: {}}` section; (3) add `suricata` service: `build: {context: ., dockerfile: lab/Dockerfile.suricata}`, `container_name: aatf-suricata`, `network_mode: host`, `volumes: [aatf-eve:/var/log/suricata]`, `restart: "no"`, `depends_on: [attacker, defender, environment]`; (4) change `attacker` service from `image: alpine:3.19` to `build: {context: ., dockerfile: lab/Dockerfile.attacker}`; (5) add `volumes: [aatf-eve:/srv/eve]` to the `attacker`, `defender`, and `environment` services

- [X] T011 [US1] Build images and verify US1 contracts (depends on T003 + T004 + T010): run `make lab-up` (first run triggers `docker compose build` for attacker + suricata images — this downloads ET Open rules, may take 2–5 min); after all 4 containers reach running state, verify: `make lab-status` exits 0 and shows 4/4; `docker inspect aatf-suricata --format '{{index .Config.Labels "suricata_version"}}'` returns `7.0.5`; `ip link show aatf-lab-br` succeeds on the host; `docker exec aatf-attacker which nmap` confirms nmap installed; `docker exec aatf-attacker ls /srv/eve/` confirms volume mounted. If Suricata fails to start, inspect logs: `docker logs aatf-suricata`.

**Checkpoint**: US1 complete. `make lab-up` starts 4 containers; Suricata is running on `aatf-lab-br`; version labels readable; eve.json volume mounted.

---

## Phase 4: User Story 2 — Smoke Test (Priority: P1)

**Goal**: `make lab-smoke` sends an nmap probe from `aatf-attacker` to `aatf-defender`,
waits up to 10 seconds for a specific ET SCAN SID to appear in `eve.json`, and exits 0
on success or 1 on failure/lab-not-running.

**Independent Test** (requires lab running from US1 checkpoint):
```sh
make lab-smoke    # → exits 0, stdout contains "SMOKE PASS: SID <N>"
make lab-check    # → exits 0 (isolation intact after probe)
```

### Implementation for User Story 2

- [X] T012 [US2] **Mandatory SID determination** (depends on T011 — lab must be running): with `make lab-up` active, run the raw probe: `docker exec aatf-attacker nmap -sS -p 1-1024 --min-rate 500 aatf-defender`; wait 5 seconds; then run `docker exec aatf-attacker sh -c "grep '\"event_type\":\"alert\"' /srv/eve/eve.json | head -10"` to inspect which SIDs fired; pick the first reliably-fired integer `signature_id` from the output and its corresponding `alert.signature` message string — record both values (needed for T013 and T015)

- [X] T013 [US2] Create `lab/scripts/lab-smoke.sh` (depends on T012 — TARGET_SID must be known): write a POSIX sh script (`#!/usr/bin/env sh`, `set -e`) with: `TARGET_SID=<integer from T012>` as a top-level constant; check `docker inspect aatf-attacker > /dev/null 2>&1` → exit 1 with `"ERROR: lab is not running (aatf-attacker absent)"` if it fails; echo `"Sending probe from aatf-attacker to aatf-defender..."`; run `docker exec aatf-attacker nmap -sS -p 1-1024 --min-rate 500 aatf-defender > /dev/null 2>&1` — exit 1 with `"ERROR: probe failed"` if nmap fails; echo `"Waiting for SID ${TARGET_SID} in eve.json (timeout 10s)..."`; poll `/srv/eve/eve.json` via `docker exec aatf-attacker sh -c "grep -q '\"signature_id\":${TARGET_SID}' /srv/eve/eve.json 2>/dev/null"` once per second for up to 10 seconds; if found: extract the timestamp from the matching line and echo `"SMOKE PASS: SID ${TARGET_SID} detected at <timestamp>"`, exit 0; if timeout reached: echo `"SMOKE FAIL: SID ${TARGET_SID} not found within 10s"`, exit 1; mark script executable (`chmod +x`)

- [X] T014 [US2] Update `Makefile` — replace the stub `lab-smoke` target body (added in T003) with: `@bash lab/scripts/lab-smoke.sh` and a `## Send smoke probe; verify ET Open SID fires in eve.json (exits 1 on failure)` doc comment

- [X] T015 [US2] Verify US2 contracts and update quickstart.md (depends on T013 + T014): run `make lab-smoke` → must exit 0 and print `SMOKE PASS`; run `make lab-check` → must exit 0 confirming isolation intact (C-003); verify `make lab-smoke` completes within 15 seconds total (C-004); then update `specs/006-e1-suricata-etopen/quickstart.md` Step 4 — replace `<TARGET_SID>` placeholder with the actual integer from T012, and replace `<ET SCAN rule message>` with the actual `alert.signature` string recorded in T012 (C-002)

**Checkpoint**: US2 complete. `make lab-smoke` reliably exits 0; specific SID documented; isolation verified.

---

## Phase 5: User Story 3 — SID Enable/Disable Hook (Priority: P2)

**Goal**: Adding a SID to `lab/rules/disabled.conf` and restarting the lab suppresses
detection for that SID. Removing it and restarting restores detection.

**Independent Test** (requires US2 complete — TARGET_SID must be known):
```sh
echo "<TARGET_SID>" >> lab/rules/disabled.conf
make lab-down && make lab-up
make lab-smoke    # → exits 1, SMOKE FAIL (SID suppressed)
# Restore:
# Remove the line from lab/rules/disabled.conf
make lab-down && make lab-up
make lab-smoke    # → exits 0, SMOKE PASS
```

### Implementation for User Story 3

- [X] T016 [US3] Verify SID disable hook end-to-end (depends on T015 — smoke test must work first): (1) append `<TARGET_SID from T012>` as a new line to `lab/rules/disabled.conf`; (2) run `make lab-down && make lab-up`; (3) run `make lab-smoke` → must exit 1 with `"SMOKE FAIL: SID <N> not found"` (C-005 contract verified); (4) remove that SID line from `lab/rules/disabled.conf` (restore empty state); (5) run `make lab-down && make lab-up`; (6) run `make lab-smoke` → must exit 0 with `"SMOKE PASS"` (re-enable verified); confirm `lab/rules/disabled.conf` is back to its original comment-only state before committing

**Checkpoint**: US3 complete. SID disable/re-enable cycle works. `disabled.conf` restored to empty (comment-only).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification sweep, sha256 hardening, and commit.

- [X] T017 Run `make test` — confirm output is exactly `78 passed, 1 skipped` with no new failures or errors (C-009 contract); no Python files were changed during F05, so this should be identical to the T002 baseline

- [X] T018 [P] Verify `make lab-down` cleanup contracts: run `make lab-down`; then verify: `docker inspect aatf-suricata 2>&1` exits non-zero (C-011 — container absent); `docker volume ls | grep aatf-eve` returns empty (C-006 — volume removed); `docker inspect aatf-attacker 2>&1` exits non-zero (existing F04 behavior preserved)

- [X] T019 [P] Harden `lab/Dockerfile.suricata` sha256 pin: with the Suricata image already built in T011, extract the sha256 of the ET Open tarball from the build cache or by re-downloading with `curl -fsSL <url> | sha256sum`; add a `sha256sum` verification line to the `RUN` step in `lab/Dockerfile.suricata` immediately after the `curl` download (before extract): `echo "<HASH>  /tmp/emerging.rules.tar.gz" | sha256sum -c -`; rebuild with `docker compose -f lab/docker-compose.yml build suricata` to confirm the check passes

- [X] T020 Stage and commit all F05 implementation files: `git add lab/Dockerfile.suricata lab/Dockerfile.attacker lab/suricata/ lab/rules/ lab/scripts/lab-smoke.sh lab/docker-compose.yml lab/scripts/lab-status.sh Makefile specs/006-e1-suricata-etopen/quickstart.md`; commit with message `feat(F05): add Suricata 7.0.5 + ET Open to lab (make lab-smoke, SID disable hook)`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user story work
- **Phase 3 (US1)**: Depends on Phase 2 — T005–T008 can run in parallel; T009 depends on T007+T008; T010 depends on T005+T009; T011 depends on T010
- **Phase 4 (US2)**: Depends on T011 (lab must be running) — T012 must run before T013
- **Phase 5 (US3)**: Depends on T015 (smoke test verified) — one sequential verification task
- **Phase 6 (Polish)**: Depends on T016 — T017, T018, T019 can run in parallel; T020 depends on T017+T018+T019

### User Story Dependencies

- **US1 (P1)**: No story dependencies. Requires Foundational phase. Delivers running lab.
- **US2 (P1)**: Depends on US1 (lab must be running for SID determination). Delivers smoke test.
- **US3 (P2)**: Depends on US2 (TARGET_SID must be known for disable test). Delivers SID hook.

### Parallel Opportunities

- **T003 + T004** (Phase 2): Different files (Makefile + lab-status.sh) — run in parallel
- **T005 + T006** (Phase 3): Different files (Dockerfile.attacker + disabled.conf) — run in parallel
- **T007 + T008** (Phase 3): Different files (suricata.yaml + docker-entrypoint.sh) — run in parallel
- **T017 + T018 + T019** (Phase 6): Independent verification tasks — run in parallel

---

## Parallel Example: User Story 1

```bash
# Parallel group A (both are independent file creations):
Task T005: Create lab/Dockerfile.attacker
Task T006: Create lab/rules/disabled.conf

# Parallel group B (both feed into T009, independent from each other):
Task T007: Create lab/suricata/suricata.yaml
Task T008: Create lab/suricata/docker-entrypoint.sh

# Sequential after B:
Task T009: Create lab/Dockerfile.suricata (depends on T007 + T008 COPY targets)
Task T010: Update lab/docker-compose.yml (depends on T005 + T009)
Task T011: make lab-up + verify (depends on T010)
```

---

## Implementation Strategy

### MVP First (US1 + US2 — both P1)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T004)
3. Complete Phase 3: US1 (T005–T011) — 4-container lab running
4. **STOP and VALIDATE**: `make lab-status` exits 0, 4/4
5. Complete Phase 4: US2 (T012–T015) — smoke test working
6. **STOP and VALIDATE**: `make lab-smoke` exits 0

### Incremental Delivery

1. Setup + Foundational → safe Makefile/status baseline
2. US1 → Suricata in lab, eve.json volume, version labels (Detection Service)
3. US2 → Smoke test end-to-end, specific SID documented (Detection Verified)
4. US3 → SID disable hook verified (F22 compatibility)
5. Polish → sha256 hardening, make test regression check, commit

### Key Implementation Note — T012 (SID Determination)

T012 is not a code-writing task — it is a live discovery step. The lab must be running
from T011. The output of T012 (an integer SID and a rule message string) is a required
input to T013 and T015. Do not write `lab/scripts/lab-smoke.sh` until T012 is complete.
Attempting to guess the SID without running the probe risks a broken smoke test.

---

## Notes

- [P] tasks = different files, no dependencies — safe to run in parallel
- No pytest tasks — this feature is all shell/Docker infrastructure (FR-011)
- `make test` is a regression check run in T017, NOT a new test suite
- T002 (baseline) and T017 (regression) bracket the implementation: same output = no regressions
- T012 is a DISCOVERY task — run commands, read output, record values — before writing code
- T016 (US3) modifies `lab/rules/disabled.conf` and MUST restore it to empty before T020 commit
- T019 (sha256) causes a second Docker build; cache reuse means it's fast if layers are unchanged
