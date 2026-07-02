# Research: Isolation Verification (F06)

**Feature**: 005-e1-isolation-verify  
**Date**: 2026-07-02

No NEEDS CLARIFICATION markers existed in the spec. All decisions below are based on existing
project constraints (Python 3.12, no new pip deps) and stdlib capabilities.

---

## Decision 1: IP address classification library

**Decision**: Python stdlib `ipaddress` module (no new dependency).

**Rationale**: `ipaddress.ip_network()` and `ip_address().is_loopback`,
`.is_private`, `.is_global` cover all classification needs. `ip_network(...).supernet_of()` /
`ip_address() in ip_network()` handles subnet containment. Already available in Python 3.12.

**Alternatives considered**:
- `netaddr` (PyPI) — richer API but adds a dependency; stdlib is sufficient here.
- Manual CIDR arithmetic — fragile, no benefit over stdlib.

---

## Decision 2: Hostname resolution in the guard

**Decision**: Use `socket.getaddrinfo(host, None)` for hostname → IP resolution, then
classify the resulting IP(s). If *any* resolved address is external, raise.

**Rationale**: Fails safe — a hostname that resolves to even one external IP is rejected.
`getaddrinfo` respects system DNS and returns all address families.

**Alternatives considered**:
- `socket.gethostbyname()` — resolves only one A record; misses multi-homed hostnames.
- Skip resolution — would allow `evil.com` to pass the guard if DNS isn't resolved.

**Edge case**: If hostname resolution fails (DNS unavailable inside test), the guard raises
`ExternalTargetError` with a "cannot verify" message — fail closed, never fail open.

---

## Decision 3: Guard function vs guard class

**Decision**: A single module-level function `assert_lab_internal(target, allowed_networks)`.
No class. The allowed networks default to the F04 lab subnet (`172.28.0.0/16`) plus loopback.

**Rationale**: F06 only creates and tests the guard. F08 (action executor) will wire it in.
A function is the simplest unit F08 can import and call. A class would add indirection with
no benefit at this stage.

**Alternatives considered**:
- `IsolationGuard` class — rejected; premature abstraction. Three similar calls become a
  class for no reason yet.

---

## Decision 4: Parsing docker-compose.yml for US1

**Decision**: Use PyYAML (already in `requirements.txt`) to parse `lab/docker-compose.yml`
and assert `networks.<name>.internal == true` and `networks.<name>.name == "aatf-lab"`.

**Rationale**: PyYAML is already a project dependency. Parsing the actual compose file means
the test directly reflects the real configuration — no coupling to a stub.

**Test approach**: The test imports the YAML, walks to `networks → lab → internal`, and
asserts `True`. It also checks that no service has a `ports:` key (no published host ports
on experiment containers).

**Alternatives considered**:
- `docker compose config` (CLI) — requires Docker installed; breaks the Docker-free
  constraint for US1.
- Regex on raw YAML text — fragile; YAML allows multiple representations of `true`.

---

## Decision 5: pytest marker for Docker-dependent tests (US3)

**Decision**: Register a custom `docker` marker in `pyproject.toml` under
`[tool.pytest.ini_options] markers`. US3 tests use `@pytest.mark.docker`. The test itself
calls `docker inspect aatf-attacker` via subprocess; if it fails, the test calls
`pytest.skip("lab not running — run make lab-up first")`.

**Rationale**: Skip (not xfail, not error) is correct — the test is not expected to fail,
it is conditionally runnable. The marker keeps US3 discoverable and filterable (`pytest -m
docker` runs only live tests; `pytest -m "not docker"` excludes them).

**Alternatives considered**:
- Separate test file `tests/test_isolation_live.py` — works but no marker means no
  `make test-docker` target can filter cleanly.
- `pytest.importorskip("docker")` — wrong approach; Docker is a CLI binary, not a Python
  package.

---

## Decision 6: Where the guard lives in the source tree

**Decision**: `src/aatf/isolation.py` — new module alongside `config.py`, `seeding.py`,
`manifest.py`, `contracts.py`.

**Rationale**: Follows the existing flat `src/aatf/` layout. F08 (action executor) will
`from aatf.isolation import assert_lab_internal` — short, discoverable path.

**No changes** to `src/aatf/contracts.py` or any existing module.

---

## Decision 7: No new pip dependencies

**Decision**: Confirmed — `ipaddress`, `socket`, `subprocess`, `yaml` (PyYAML already in
requirements.txt) are sufficient. `requirements.in` and `requirements.txt` are unchanged.

---

## Summary table

| Decision | Chosen | Key reason |
|----------|--------|------------|
| IP classification | stdlib `ipaddress` | No new deps; covers all cases |
| Hostname resolution | `socket.getaddrinfo` | Fail-closed on multi-homed |
| Guard shape | Function `assert_lab_internal` | Simplest; F08 imports and calls |
| Compose parsing | PyYAML (existing dep) | Already present; no Docker needed |
| Docker-dep tests | `@pytest.mark.docker` + skip | Filterable; `make test` stays green |
| Guard location | `src/aatf/isolation.py` | Matches existing flat module layout |
| New pip deps | None | All stdlib or existing deps |
