# Contract: lab-smoke Shell Protocol

**Feature**: F05 — Suricata + ET Open Ruleset  
**Branch**: `006-e1-suricata-etopen`  
**Date**: 2026-07-02  
**FR source**: FR-005, FR-006 from [spec.md](../spec.md)

---

## Contract C-001 — Smoke Test Exit Codes

**What it tests**: `make lab-smoke` / `lab/scripts/lab-smoke.sh` exit codes are correct
in all terminal states.

| Scenario | Expected exit code | Expected stdout |
|----------|--------------------|----------------|
| Lab running, SID fires within 10s | `0` | Contains `SMOKE PASS: SID <N>` |
| Lab not running (container absent) | `1` | Contains `ERROR: lab is not running` |
| SID not found within timeout | `1` | Contains `SMOKE FAIL: SID <N> not found` |
| Probe command errors | `1` | Contains `ERROR: probe failed` |

**Verification**: Run `make lab-smoke` in each scenario; check `$?` and `stdout`.

---

## Contract C-002 — Specific SID Is Documented and Hardcoded

**What it tests**: The smoke test targets exactly one documented SID, not a category search.

- The `TARGET_SID` constant in `lab/scripts/lab-smoke.sh` MUST be an integer matching a
  rule in the pinned ET Open ruleset.
- The SID MUST be documented in [quickstart.md](../quickstart.md) alongside the rule
  message string so a researcher can look it up independently.
- `grep "TARGET_SID=" lab/scripts/lab-smoke.sh` MUST return a non-empty line.

**Verification**: Run grep; cross-reference SID with ET Open rule database; confirm the
rule message appears in the quickstart.

---

## Contract C-003 — Probe Stays Lab-Internal

**What it tests**: The nmap probe targets only the lab-internal address of `aatf-defender`
and not any external IP or hostname.

- The target in `lab/scripts/lab-smoke.sh` MUST be the container name `aatf-defender`
  (resolved inside Docker to `172.28.x.x`), never a public hostname or IP.
- `aatf-defender` resolves to an IP within `172.28.0.0/16` (verified by `docker inspect`).
- No traffic leaves the `aatf-lab` network during `make lab-smoke` (verified by running
  `make lab-check` after `make lab-smoke` — isolation MUST remain intact).

**Verification**: Run `make lab-smoke && make lab-check`; both must exit 0.

---

## Contract C-004 — Timeout Bound

**What it tests**: The smoke test waits at most 10 seconds for the SID to appear in
`eve.json` (FR-005); it MUST NOT hang indefinitely.

- The polling loop in `lab/scripts/lab-smoke.sh` MUST have a hard timeout of 10 seconds.
- The script exits `1` with `SMOKE FAIL` if the timeout is reached without the SID.
- The overall `make lab-smoke` runtime MUST complete within 15 seconds (SC-002 allows 15s
  from invocation, including probe transmission time + 10s wait).

**Verification**: Manually stop Suricata mid-test; `make lab-smoke` must exit within 15s
total with exit code 1.

---

## Contract C-005 — SID Disable Suppresses Detection

**What it tests**: Adding a SID to `lab/rules/disabled.conf` and restarting the lab
results in zero eve.json alerts for that SID when the matching probe is sent.

**Precondition**: Run `make lab-smoke`; confirm TARGET_SID appears in eve.json (exit 0).

**Steps**:
1. Add `TARGET_SID` to `lab/rules/disabled.conf`
2. `make lab-down && make lab-up`
3. Run `make lab-smoke`

**Expected**: `make lab-smoke` exits `1` with `SMOKE FAIL` (TARGET_SID suppressed).

**Post-condition**: Remove `TARGET_SID` from `disabled.conf`; repeat `make lab-down && make lab-up && make lab-smoke` → must exit `0` again.

**Verification**: Manual run of the 3-step sequence.

---

## Contract C-006 — eve.json Cleared on Lab Restart

**What it tests**: The `aatf-eve` volume is destroyed on `make lab-down`, so each lab
session starts with a clean `eve.json`.

- After `make lab-down`, `docker volume ls | grep aatf-eve` MUST return empty.
- After `make lab-up`, `/var/log/suricata/eve.json` either does not exist or is empty
  until Suricata emits its first event.

**Verification**: Run `make lab-down`; verify volume absent; run `make lab-up`; verify
eve.json starts clean.

---

## Contract C-007 — lab-status Reports 4 Containers

**What it tests**: `make lab-status` reports Suricata alongside the three original
containers (FR-009).

- `make lab-status` stdout MUST include `aatf-suricata` with state `running`.
- The total count MUST be 4 (not 3 as in F04).
- `make lab-status` MUST exit `0` when all 4 are running.

**Verification**: Run `make lab-up && make lab-status`; grep output for `aatf-suricata`.

---

## Contract C-008 — Suricata Version Readable

**What it tests**: The Suricata version can be queried without starting an experiment
(FR-010, SC-004).

- `docker inspect aatf-suricata --format '{{index .Config.Labels "suricata_version"}}'`
  MUST return a non-empty string equal to `7.0.5`.
- `docker inspect aatf-suricata --format '{{index .Config.Labels "ruleset_version"}}'`
  MUST return a non-empty string (the build-date stamp).
- Both labels MUST be documented in [quickstart.md](../quickstart.md).

**Verification**: Run the inspect commands against a running lab.

---

## Contract C-009 — make test Unaffected

**What it tests**: The existing test suite (78 passed, 1 skipped) continues to pass with
no changes to Python source, tests, or pyproject.toml (FR-011, SC-005).

- Running `make test` after F05 implementation MUST produce exactly `78 passed, 1 skipped`.
- No new `.py` test files are introduced.
- No changes to `src/aatf/`, `tests/`, or `pyproject.toml`.

**Verification**: `make test` after all F05 changes; compare output to baseline.

---

## Contract C-010 — Bridge Name Fixed

**What it tests**: The `aatf-lab` Docker network always has bridge interface `aatf-lab-br`
on the host after `make lab-up`.

- After `make lab-up`, `ip link show aatf-lab-br` on the host (or inside the Suricata
  container via `network_mode: host`) MUST succeed.
- Suricata config (`lab/suricata/suricata.yaml`) MUST reference `aatf-lab-br` as the
  af-packet interface.

**Verification**: Run `make lab-up`; run `ip link show aatf-lab-br`; run
`docker exec aatf-suricata suricata --build-info`.

---

## Contract C-011 — Lab-Down Cleans Suricata Container

**What it tests**: `make lab-down` removes `aatf-suricata` alongside the original three
containers.

- After `make lab-down`, `docker inspect aatf-suricata` MUST exit non-zero (container
  absent).
- The `aatf-eve` volume MUST be removed.

**Verification**: Run `make lab-down`; run inspect commands; verify both absent.
