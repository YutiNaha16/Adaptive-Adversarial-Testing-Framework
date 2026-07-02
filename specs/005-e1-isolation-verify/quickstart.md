# Quickstart: Isolation Verification (F06)

**Feature**: 005-e1-isolation-verify  
**Date**: 2026-07-02

Quick verification guide for each user story after implementation.

---

## Prerequisites

- `make setup` already run (`.venv` exists with pinned deps)
- For US3 only: Docker Engine + Compose V2, lab not running yet

---

## SC-001: All Docker-free isolation tests pass in `make test`

```bash
make test
```

Expected output includes:
```
tests/test_isolation.py::test_lab_config_declares_internal PASSED
tests/test_isolation.py::test_lab_config_network_name PASSED
tests/test_isolation.py::test_no_host_ports_on_experiment_containers PASSED
tests/test_isolation.py::test_lab_subnet_is_nonroutable PASSED
tests/test_isolation.py::test_guard_rejects_public_ip PASSED
tests/test_isolation.py::test_guard_rejects_public_ipv6 PASSED
tests/test_isolation.py::test_guard_rejects_rfc1918_outside_lab_subnet PASSED
tests/test_isolation.py::test_guard_passes_lab_internal_ip PASSED
tests/test_isolation.py::test_guard_passes_loopback PASSED
... (all isolation tests green, Docker test skipped)
```

Total: existing 63 tests + new isolation tests all green.

---

## SC-002: Misconfiguration caught automatically

Temporarily break the config:
```bash
# Comment out internal: true in lab/docker-compose.yml
sed -i 's/internal: true/# internal: true/' lab/docker-compose.yml
make test
# Expect: test_lab_config_declares_internal FAILED with clear message
# Restore:
sed -i 's/# internal: true/internal: true/' lab/docker-compose.yml
```

---

## SC-003: Guard test coverage verified

```bash
.venv/bin/pytest tests/test_isolation.py -v -m "not docker"
```

Expected: tests covering public IP (raises), public IPv6 (raises), RFC1918-outside-subnet
(raises), lab-internal (passes), loopback (passes), boundary addresses — all PASSED.

---

## SC-004: Live egress probe with lab running

```bash
make lab-up
.venv/bin/pytest tests/test_isolation.py -v -m docker
```

Expected:
```
tests/test_isolation.py::test_live_egress_blocked PASSED   (completes in <10s)
```

Then tear down:
```bash
make lab-down
```

---

## SC-005: Docker tests skip cleanly without lab

```bash
make lab-down   # ensure lab is down
make test
```

Expected: Docker-marked tests show as `SKIPPED` with message
`"lab not running — run make lab-up first"`. No failures.

---

## Full verification sequence (after implementation)

```bash
make test                                        # SC-001, SC-005: all pass, docker skipped
make lab-up && .venv/bin/pytest -m docker        # SC-004: live egress blocked
make lab-down
```

Time: under 30 seconds total (excluding image pull, which was done in F04).
