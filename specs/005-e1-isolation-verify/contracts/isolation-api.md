# Contracts: Isolation Verification API (F06)

**Feature**: 005-e1-isolation-verify  
**Date**: 2026-07-02

These contracts define the exact behaviour the implementation must satisfy. Each contract
maps to one or more pytest test assertions.

---

## Module: `src/aatf/isolation.py`

### Contract C-001: ExternalTargetError is a ValueError subclass

```
ExternalTargetError(ValueError)
    .target: str    # the rejected address/hostname
    .reason: str    # human-readable cause
```

**Test**: `isinstance(ExternalTargetError("x", "y"), ValueError)` → `True`

---

### Contract C-002: assert_lab_internal — public IP rejected

**Given** `target = "8.8.8.8"` (publicly routable IPv4)  
**When** `assert_lab_internal("8.8.8.8")` is called  
**Then** raises `ExternalTargetError`

---

### Contract C-003: assert_lab_internal — public IPv6 rejected

**Given** `target = "2001:4860:4860::8888"` (Google public DNS IPv6)  
**When** `assert_lab_internal("2001:4860:4860::8888")` is called  
**Then** raises `ExternalTargetError`

---

### Contract C-004: assert_lab_internal — RFC1918 outside lab subnet rejected

**Given** `target = "192.168.1.1"` (RFC1918 but not in `172.28.0.0/16`)  
**When** `assert_lab_internal("192.168.1.1")` is called  
**Then** raises `ExternalTargetError`

---

### Contract C-005: assert_lab_internal — lab-internal IP passes

**Given** `target = "172.28.0.5"` (within the default lab subnet `172.28.0.0/16`)  
**When** `assert_lab_internal("172.28.0.5")` is called  
**Then** returns `None` without raising

---

### Contract C-006: assert_lab_internal — loopback passes

**Given** `target = "127.0.0.1"` (loopback)  
**When** `assert_lab_internal("127.0.0.1")` is called  
**Then** returns `None` without raising

---

### Contract C-007: assert_lab_internal — loopback hostname passes

**Given** `target = "localhost"` (resolves to `127.0.0.1` or `::1`)  
**When** `assert_lab_internal("localhost")` is called  
**Then** returns `None` without raising

---

### Contract C-008: assert_lab_internal — custom allowed_networks respected

**Given** `target = "10.0.0.5"`, `allowed_networks = ["10.0.0.0/8"]`  
**When** `assert_lab_internal("10.0.0.5", allowed_networks=["10.0.0.0/8"])` is called  
**Then** returns `None` without raising

---

### Contract C-009: assert_lab_internal — target outside custom allowed_networks rejected

**Given** `target = "172.28.0.5"`, `allowed_networks = ["10.0.0.0/8"]`  
**When** `assert_lab_internal("172.28.0.5", allowed_networks=["10.0.0.0/8"])` is called  
**Then** raises `ExternalTargetError` (172.28.x is not in 10.0.0.0/8)

---

### Contract C-010: assert_lab_internal — lab subnet boundary — subnet address passes

**Given** `target = "172.28.0.0"` (network address of `172.28.0.0/16`)  
**When** `assert_lab_internal("172.28.0.0")` is called  
**Then** returns `None` without raising

---

### Contract C-011: assert_lab_internal — lab subnet boundary — address just outside rejected

**Given** `target = "172.29.0.1"` (just outside `172.28.0.0/16`)  
**When** `assert_lab_internal("172.29.0.1")` is called  
**Then** raises `ExternalTargetError`

---

## Module: `tests/test_isolation.py` — US1 structural tests

### Contract C-012: Lab config declares internal:true

**Given** `lab/docker-compose.yml` exists and is valid YAML  
**When** parsed and `networks.lab.internal` is read  
**Then** value is `True` (Python bool, not string `"true"`)

---

### Contract C-013: Lab config has correct network name

**Given** `lab/docker-compose.yml` exists  
**When** parsed and `networks.lab.name` is read  
**Then** value is `"aatf-lab"`

---

### Contract C-014: No experiment container publishes host ports

**Given** `lab/docker-compose.yml` exists  
**When** `services.attacker`, `services.defender`, `services.environment` are inspected  
**Then** none has a `ports:` key

---

### Contract C-015: Lab subnet is in a non-routable range

**Given** `lab/docker-compose.yml` exists  
**When** `networks.lab.ipam.config[0].subnet` is parsed  
**Then** the subnet is an RFC1918 or link-local range (not publicly routable)

---

## Module: `tests/test_isolation.py` — US3 live egress tests (Docker-dependent)

### Contract C-016: Live egress blocked — check-isolation.sh exits 0

**Given** the lab is running (`aatf-attacker` container exists and is running)  
**When** `lab/scripts/check-isolation.sh` is called via subprocess  
**Then** exit code is `0` and stdout contains "ISOLATED"

**Marker**: `@pytest.mark.docker` — skips when lab is not running

---

### Contract C-017: Live egress check skips gracefully when lab is down

**Given** the lab is not running (`aatf-attacker` container absent)  
**When** the live egress test runs  
**Then** `pytest.skip()` is called with a message containing "lab not running"

---

## Test count summary

| Story | Contracts | Docker required |
|-------|-----------|-----------------|
| US1 (structural) | C-012 – C-015 | No |
| US2 (fail-closed guard) | C-001 – C-011 | No |
| US3 (live egress) | C-016 – C-017 | Yes (skips if absent) |
| **Total** | **17** | — |
