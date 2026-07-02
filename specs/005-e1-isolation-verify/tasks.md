---
description: "Task list for 005-e1-isolation-verify"
---

# Tasks: Isolation Verification (F06)

**Input**: Design documents from `specs/005-e1-isolation-verify/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/isolation-api.md

**Tests**: TDD — tests written before implementation. US1 tests are self-contained (parse
lab/docker-compose.yml from F04; no new implementation file). US2 tests go RED first because
`src/aatf/isolation.py` doesn't exist yet, then GREEN after implementation. US3 tests always
skip when lab is down and pass when lab is up.

**Organization**: Three user stories, each independently testable. US1 and US2 are both P1
and can proceed sequentially (US1 first since it needs no source module). US3 (P2) is added
last as it requires Docker.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US3 per spec.md

## Path Conventions

All new source files: `src/aatf/isolation.py` (new module). All new tests: `tests/test_isolation.py`
(new file). Config change: `pyproject.toml` (add pytest marker). No changes to any other file.

---

## Phase 1: Setup

**Purpose**: Confirm prerequisites and verify no blocked dependencies.

- [X] T001 Confirm `lab/docker-compose.yml` exists (from F04) and `make test` is currently
  green at 63 tests: run `make test` and record baseline pass count. No code changes yet.

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Register the `docker` pytest marker in `pyproject.toml` so US3 tests can use
`@pytest.mark.docker` without triggering `PytestUnknownMarkWarning`. Must be done before any
test file is written.

- [X] T002 Add `markers` entry under `[tool.pytest.ini_options]` in `pyproject.toml`:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  addopts = "-ra"
  markers = [
      "docker: marks tests that require Docker and a running lab (skipped otherwise)",
  ]
  ```
  Verify: run `make test` — no `PytestUnknownMarkWarning` in output (63 tests still pass).

**Checkpoint**: `pyproject.toml` updated; `make test` still 63/63.

---

## Phase 3: User Story 1 — Structural Config Test (Priority: P1) 🎯 MVP

**Goal**: A Docker-free test that parses `lab/docker-compose.yml` and asserts the lab
network is structurally isolated (`internal: true`, no published ports). Runs in `make test`.

**Independent Test**: Run `make test` on a machine without Docker; new structural tests pass.
Temporarily removing `internal: true` from docker-compose.yml causes the test to fail.

### Implementation for User Story 1

- [X] T003 [US1] Create `tests/test_isolation.py` with the US1 structural tests section.
  The file must start with this block and nothing else yet (US2/US3 tests added later):

  ```python
  from __future__ import annotations

  import ipaddress
  import pathlib
  import subprocess

  import pytest
  import yaml

  # ---------------------------------------------------------------------------
  # Helpers
  # ---------------------------------------------------------------------------
  _COMPOSE_FILE = pathlib.Path("lab/docker-compose.yml")


  def _load_compose() -> dict:
      return yaml.safe_load(_COMPOSE_FILE.read_text())


  # ---------------------------------------------------------------------------
  # US1: Structural isolation tests (Docker-free)
  # ---------------------------------------------------------------------------

  def test_lab_config_declares_internal() -> None:
      """C-012: lab network must declare internal: true."""
      cfg = _load_compose()
      assert cfg["networks"]["lab"]["internal"] is True, (
          "lab network must declare 'internal: true' — isolation NOT enforced"
      )


  def test_lab_config_network_name() -> None:
      """C-013: lab network name must be aatf-lab."""
      cfg = _load_compose()
      assert cfg["networks"]["lab"]["name"] == "aatf-lab"


  def test_no_host_ports_on_experiment_containers() -> None:
      """C-014: no experiment container may publish host ports."""
      cfg = _load_compose()
      for role in ("attacker", "defender", "environment"):
          svc = cfg["services"][role]
          assert "ports" not in svc, (
              f"Service '{role}' must not publish host ports"
          )


  def test_lab_subnet_is_nonroutable() -> None:
      """C-015: lab subnet must be RFC1918 or link-local (not publicly routable)."""
      cfg = _load_compose()
      subnet_str = cfg["networks"]["lab"]["ipam"]["config"][0]["subnet"]
      network = ipaddress.ip_network(subnet_str, strict=False)
      assert network.is_private, (
          f"Lab subnet {subnet_str} is publicly routable — must be RFC1918 or link-local"
      )
  ```

- [X] T004 [US1] Verify T003: run `make test` and confirm all 4 new structural tests pass
  (67 total). No Docker required. Confirm output contains:
  ```
  tests/test_isolation.py::test_lab_config_declares_internal PASSED
  tests/test_isolation.py::test_lab_config_network_name PASSED
  tests/test_isolation.py::test_no_host_ports_on_experiment_containers PASSED
  tests/test_isolation.py::test_lab_subnet_is_nonroutable PASSED
  ```

**Checkpoint**: US1 complete — `make test` passes with 4 new Docker-free structural tests.

---

## Phase 4: User Story 2 — Fail-Closed External Target Guard (Priority: P1)

**Goal**: A Python guard function `assert_lab_internal(target, allowed_networks)` in
`src/aatf/isolation.py` that raises `ExternalTargetError` on any externally routable target.
Tested in `make test` without Docker (11 tests covering contracts C-001–C-011).

**TDD sequence**: Write 11 tests first → RED (import fails). Create `isolation.py` → GREEN.

**Independent Test**: Run `make test` — all 11 guard tests pass with no Docker.

### TDD Red Phase for User Story 2

- [X] T005 [US2] Append the US2 guard test section to `tests/test_isolation.py` immediately
  after the US1 block:

  ```python
  # ---------------------------------------------------------------------------
  # US2: Fail-closed external target guard tests (Docker-free)
  # ---------------------------------------------------------------------------
  from aatf.isolation import ExternalTargetError, assert_lab_internal


  def test_external_target_error_is_value_error() -> None:
      """C-001: ExternalTargetError must be a ValueError subclass."""
      err = ExternalTargetError("8.8.8.8", "publicly routable")
      assert isinstance(err, ValueError)
      assert err.target == "8.8.8.8"
      assert err.reason == "publicly routable"


  def test_guard_rejects_public_ip() -> None:
      """C-002: public IPv4 must be rejected."""
      with pytest.raises(ExternalTargetError):
          assert_lab_internal("8.8.8.8")


  def test_guard_rejects_public_ipv6() -> None:
      """C-003: public IPv6 must be rejected."""
      with pytest.raises(ExternalTargetError):
          assert_lab_internal("2001:4860:4860::8888")


  def test_guard_rejects_rfc1918_outside_lab_subnet() -> None:
      """C-004: RFC1918 address outside the lab subnet must be rejected."""
      with pytest.raises(ExternalTargetError):
          assert_lab_internal("192.168.1.1")


  def test_guard_passes_lab_internal_ip() -> None:
      """C-005: address inside lab subnet must pass."""
      assert assert_lab_internal("172.28.0.5") is None


  def test_guard_passes_loopback_ip() -> None:
      """C-006: loopback IPv4 must pass."""
      assert assert_lab_internal("127.0.0.1") is None


  def test_guard_passes_localhost_hostname() -> None:
      """C-007: localhost hostname must pass (resolves to loopback)."""
      assert assert_lab_internal("localhost") is None


  def test_guard_custom_allowed_networks_pass() -> None:
      """C-008: address in custom allowed_networks must pass."""
      assert assert_lab_internal("10.0.0.5", allowed_networks=["10.0.0.0/8"]) is None


  def test_guard_custom_allowed_networks_reject() -> None:
      """C-009: address outside custom allowed_networks must be rejected."""
      with pytest.raises(ExternalTargetError):
          assert_lab_internal("172.28.0.5", allowed_networks=["10.0.0.0/8"])


  def test_guard_subnet_boundary_address_passes() -> None:
      """C-010: network address of lab subnet must pass."""
      assert assert_lab_internal("172.28.0.0") is None


  def test_guard_address_just_outside_subnet_rejected() -> None:
      """C-011: address just outside lab subnet must be rejected."""
      with pytest.raises(ExternalTargetError):
          assert_lab_internal("172.29.0.1")
  ```

- [X] T006 [US2] Verify RED phase: run `make test` and confirm the 11 guard tests fail with
  `ImportError` (cannot import from `aatf.isolation` — module does not exist yet). The 4 US1
  tests from T003 must still pass.

### TDD Green Phase for User Story 2

- [X] T007 [US2] Create `src/aatf/isolation.py` with the `ExternalTargetError` class and
  `assert_lab_internal` function:

  ```python
  from __future__ import annotations

  import ipaddress
  import socket

  LAB_NETWORKS_DEFAULT: list[str] = ["172.28.0.0/16"]
  _LOOPBACK_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
      ipaddress.ip_network("127.0.0.0/8"),
      ipaddress.ip_network("::1/128"),
  ]


  class ExternalTargetError(ValueError):
      """Raised when a target address is not within the permitted lab network."""

      def __init__(self, target: str, reason: str) -> None:
          self.target = target
          self.reason = reason
          super().__init__(f"External target rejected — {target}: {reason}")


  def assert_lab_internal(
      target: str,
      allowed_networks: list[str] | None = None,
  ) -> None:
      """Raise ExternalTargetError if target is not lab-internal or loopback.

      Args:
          target: IP address string or hostname to validate.
          allowed_networks: CIDR strings of permitted networks.
              Defaults to LAB_NETWORKS_DEFAULT (172.28.0.0/16).
              Loopback is always permitted regardless of this parameter.
      """
      nets = [ipaddress.ip_network(n, strict=False) for n in (allowed_networks or LAB_NETWORKS_DEFAULT)]

      try:
          addr = ipaddress.ip_address(target)
          _check_address(addr, target, nets)
      except ValueError:
          # Not a bare IP — treat as hostname; resolve and check all addresses.
          try:
              results = socket.getaddrinfo(target, None)
          except socket.gaierror as exc:
              raise ExternalTargetError(target, f"hostname resolution failed — failing closed: {exc}") from exc
          for _family, _type, _proto, _canonname, sockaddr in results:
              addr = ipaddress.ip_address(sockaddr[0])
              _check_address(addr, target, nets)


  def _check_address(
      addr: ipaddress.IPv4Address | ipaddress.IPv6Address,
      target: str,
      allowed_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
  ) -> None:
      if any(addr in lb for lb in _LOOPBACK_NETWORKS):
          return
      if any(addr in net for net in allowed_networks):
          return
      raise ExternalTargetError(
          target,
          f"{addr} is not within permitted lab networks {[str(n) for n in allowed_networks]}",
      )
  ```

- [X] T008 [US2] Verify GREEN phase: run `make test` — all 11 guard tests pass. Total should
  be 63 (baseline) + 4 (US1) + 11 (US2) = 78 tests passing. Confirm output contains all
  guard test names as PASSED.

**Checkpoint**: US2 complete — `assert_lab_internal` is implemented and all 11 guard tests
pass in `make test` without Docker.

---

## Phase 5: User Story 3 — Live Egress Probe (Priority: P2)

**Goal**: A `@pytest.mark.docker` test that, when the lab is running, calls
`lab/scripts/check-isolation.sh` via subprocess and asserts it exits 0 with "ISOLATED" in
stdout. Skips gracefully when the lab is not running.

**Independent Test**: With lab down → `make test` skips the Docker test. With lab up →
`pytest -m docker` passes in under 10 seconds.

### Implementation for User Story 3

- [X] T009 [US3] Append the US3 live egress test section to `tests/test_isolation.py`:

  ```python
  # ---------------------------------------------------------------------------
  # US3: Live egress probe (Docker-dependent — skips when lab is not running)
  # ---------------------------------------------------------------------------

  def _lab_is_running() -> bool:
      result = subprocess.run(
          ["docker", "inspect", "aatf-attacker"],
          capture_output=True,
      )
      return result.returncode == 0


  @pytest.mark.docker
  def test_live_egress_blocked() -> None:
      """C-016: outbound connection from lab network must be blocked."""
      if not _lab_is_running():
          pytest.skip("lab not running — run 'make lab-up' first")
      result = subprocess.run(
          ["bash", "lab/scripts/check-isolation.sh"],
          capture_output=True,
          text=True,
      )
      assert result.returncode == 0, (
          f"Isolation BREACH detected!\nstdout: {result.stdout}\nstderr: {result.stderr}"
      )
      assert "ISOLATED" in result.stdout
  ```

  Note: C-017 (skip behaviour) is exercised by running `make test` while the lab is down —
  the skip path in `test_live_egress_blocked` covers it. No separate test function needed.

- [X] T010 [US3] Verify skip behaviour (lab down): run `make test` — confirm
  `test_live_egress_blocked` shows as `SKIPPED` with the message
  `"lab not running — run 'make lab-up' first"`. Total: 78 passed, 1 skipped.

- [ ] T011 [US3] Verify live probe (lab up): run `make lab-up`, then
  `.venv/bin/pytest tests/test_isolation.py -m docker -v`. Confirm:
  - `test_live_egress_blocked` PASSED
  - Completes in under 10 seconds
  Then run `make lab-down` to clean up.

**Checkpoint**: US3 complete — live egress probe works, skips cleanly without Docker, passes
with lab running.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T012 Run `make test` — confirm full suite passes: 78 tests (63 baseline + 4 US1 +
  11 US2) with 1 skipped (US3 docker test). No regressions in existing tests.

- [X] T013 [P] Run `make lint` — confirm `ruff check .` and `ruff format --check .` pass
  with no violations on `src/aatf/isolation.py` and `tests/test_isolation.py`.

- [X] T014 [P] Update `README.md` status line to reflect F06 complete:
  change "E1 in progress: isolated Docker lab (F04) is operational" to
  "E1 in progress: isolated Docker lab (F04) operational; isolation verification (F06) automated."

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001 immediately.
- **Foundational (Phase 2)**: T001 must complete (confirms baseline); T002 is independent.
- **US1 (Phase 3)**: T002 must complete (marker registered) before T003 writes the test file.
- **US2 (Phase 4)**: T003 must complete (test file exists) before T005 appends to it.
  T006 (red verification) before T007 (implementation). T007 before T008 (green verification).
- **US3 (Phase 5)**: T008 must complete (test file and isolation.py both exist) before T009
  appends the live egress test. T010 (skip verification) before T011 (live verification).
- **Polish (Phase 6)**: All US phases complete.

### Parallel Opportunities

- T001 and T002 are independent (different files) — can run together.
- T012, T013, T014 in Polish are independent — can run together.
- US1 and US2 share the same file (`tests/test_isolation.py`) so their write tasks must be
  sequential: T003 (create file) → T005 (append). T007 (`isolation.py`) can start in
  parallel with T005 since it is a different file, but T008 (green verification) must wait
  for both T005 and T007.

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Phase 1 Setup → Phase 2 Foundational (T001–T002)
2. Phase 3 US1: structural config tests (T003–T004) — immediately green, no source module
3. Phase 4 US2: guard tests red → implementation → green (T005–T008)
4. **STOP and VALIDATE**: `make test` passes with 78 tests; `make lint` clean.
   Constitution Principle I is now provably enforced in the automated test suite.

### Incremental Delivery

US1 (config assertion) → US2 (fail-closed guard + tests) → US3 (live egress probe) → Polish.
Each phase adds a distinct verification layer without breaking the previous.

---

## Notes

- `tests/test_isolation.py` is a SINGLE file built in three phases: T003 creates it (US1),
  T005 appends to it (US2), T009 appends to it (US3). Never overwrite; always append.
- The `from aatf.isolation import ...` line in T005 is placed at the top of the US2 block,
  not at the top of the file — this avoids a module-level ImportError that would break the
  already-passing US1 tests during the red phase.
- `make test` must stay Docker-free throughout. The docker-dependent test uses `pytest.skip()`
  (not `xfail`) — it is conditionally runnable, not expected to fail.
- T011 requires Docker and a running lab — it is the only task that cannot be verified
  without `make lab-up`.
