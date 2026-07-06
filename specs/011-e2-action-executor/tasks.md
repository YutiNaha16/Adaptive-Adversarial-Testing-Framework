# Tasks: Action Executor (F08)

**Feature**: `011-e2-action-executor` | **Branch**: `011-e2-action-executor`
**Input**: Design documents from `specs/011-e2-action-executor/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/action-executor-contract.md ✅

**Tests**: TDD approach — write tests first, verify red, implement, verify green.
**Baseline**: 134 passed, 3 skipped. Target: ≥148 passed, 4 skipped (+14 unit tests; C-015 auto-skip adds 1 skip).

**File to create**:
- `src/aatf/action_executor.py` — ExternalTargetError, ExecutionResult, ActionExecutor, SendFn/SleepFn/HandlerFn aliases, 15 handlers
- `tests/test_action_executor.py` — 14 unit tests + 1 integration auto-skip

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- US2 guard is implemented before US1 handlers (structural prerequisite — guard runs in execute() before handlers)

---

## Phase 1: Setup

**Purpose**: Record baseline and create empty stub so imports work before any tests.

- [X] T001 Record pytest baseline: `cd src && python -m pytest --tb=no -q` → confirm 134 passed, 3 skipped
- [X] T002 Create `src/aatf/action_executor.py` stub — empty module with only `from __future__ import annotations` and a module docstring (no classes yet); run `python -c "import aatf.action_executor"` to confirm importable

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data structures that ALL user stories depend on. No user story phase begins until complete.

**⚠️ CRITICAL**: Complete all T003–T009 before any Phase 3+ work.

- [X] T003 Add `SendFn`, `SleepFn`, `HandlerFn` type aliases to `src/aatf/action_executor.py`: `SendFn = Callable[[str, int, bytes], None]`; `SleepFn = Callable[[float], None]`; `HandlerFn = Callable[[Action, random.Random, SendFn, SleepFn], int]`
- [X] T004 Add `ExternalTargetError(ValueError)` class to `src/aatf/action_executor.py` — one `__init__(self, ip: str)` that sets `self.args` to `(f"target_ip {ip!r} is outside lab network 172.28.0.0/16",)`; no other logic yet
- [X] T005 Add `ExecutionResult` dataclass to `src/aatf/action_executor.py` — five fields: `action_id: str`, `category: str`, `success: bool`, `emitted_count: int`, `error: str | None = None`; `@dataclass` decorator (NOT frozen)
- [X] T006 Add `ActionExecutor.__init__(self, seed: int, send_fn: SendFn | None = None, sleep_fn: SleepFn | None = None)` to `src/aatf/action_executor.py` — stores `self._rng = random.Random(seed)`, `self._send_fn = send_fn or _default_send_fn`, `self._sleep_fn = sleep_fn or time.sleep`, `self._handlers: dict[str, HandlerFn] = {}` (empty for now)
- [X] T007 Add `ActionExecutor.execute(self, action: Action) -> ExecutionResult` stub that raises `NotImplementedError` — required so the class is importable and the guard can be added incrementally
- [X] T008 Add `_default_send_fn(host: str, port: int, payload: bytes) -> None` to `src/aatf/action_executor.py` — opens a `socket.socket(socket.AF_INET, socket.SOCK_STREAM)`, calls `connect_ex((host, port))`, sends payload, closes; catches all `OSError` silently (lab connections are expected to refuse)
- [X] T009 Verify module imports cleanly: `cd src && python -c "from aatf.action_executor import ActionExecutor, ExternalTargetError, ExecutionResult; print('OK')"` — must print `OK`

**Checkpoint**: Foundation ready — all data structures importable, execute() raises NotImplementedError.

---

## Phase 3: User Story 2 — Internal-Target Guard (Priority: P2) ⚠️ Structural prerequisite

**Goal**: ExternalTargetError raised before any traffic for addresses outside 172.28.0.0/16. Must be complete before US1 handlers, because the guard runs at the top of execute().

**Independent Test**: `pytest tests/test_action_executor.py -k "external or guard or private"` — 4 tests pass; no network calls recorded.

### Tests for US2 — write first, verify red ⚠️

> **NOTE: Write ALL tests below, run pytest, confirm they FAIL before T014.**

- [X] T010 [US2] Write `test_external_ip_raises` in `tests/test_action_executor.py` — contracts C-003: construct `ActionExecutor(seed=42, send_fn=recording, sleep_fn=noop)` with a recording stub; build `Action(action_id="tcp_port_scan", category="scan", parameters={"target_ip": "8.8.8.8", "port_range": "80-80", "rate_pps": 1, "timing_ms": 0}, timestamp=...)` via `contracts.py`; assert `pytest.raises(ExternalTargetError)`
- [X] T011 [US2] Write `test_no_traffic_before_external_error` in `tests/test_action_executor.py` — contract C-004: same setup as T010; after catching ExternalTargetError, assert `len(calls) == 0` where `calls` is the recording stub's list
- [X] T012 [US2] Write `test_private_non_lab_ip_raises` in `tests/test_action_executor.py` — contract C-005: repeat T010 with `target_ip = "192.168.1.1"` (RFC-1918 but not 172.28/16); assert `ExternalTargetError`
- [X] T013 [US2] Write `test_external_target_error_is_value_error` in `tests/test_action_executor.py` — contract C-014: `assert issubclass(ExternalTargetError, ValueError)`
- [X] T014 [US2] Run `cd src && python -m pytest tests/test_action_executor.py -v` — confirm T010–T013 test functions appear and **FAIL** (expected: `NotImplementedError` from stub); if any PASS without implementation, fix the test

### Implementation for US2

- [X] T015 [US2] Implement guard at top of `ActionExecutor.execute()` in `src/aatf/action_executor.py`: extract `target_ip = action.parameters.get("target_ip", "172.28.0.2")`; check `ipaddress.ip_address(target_ip) in ipaddress.ip_network("172.28.0.0/16")`; raise `ExternalTargetError(target_ip)` if not in subnet
- [X] T016 [US2] Verify guard tests pass: `cd src && python -m pytest tests/test_action_executor.py::test_external_ip_raises tests/test_action_executor.py::test_no_traffic_before_external_error tests/test_action_executor.py::test_private_non_lab_ip_raises tests/test_action_executor.py::test_external_target_error_is_value_error -v` — all 4 must PASS

**Checkpoint**: Guard is live. execute() raises ExternalTargetError for all non-172.28/16 targets. US1 handler work can now begin.

---

## Phase 4: User Story 1 — Traffic Emission (Priority: P1) 🎯 MVP

**Goal**: All 15 action handlers emit defanged lab traffic via injectable SendFn; ExecutionResult returned for every registered action.

**Independent Test**: `pytest tests/test_action_executor.py` with recording send_fn — 13 unit tests pass (C-001 through C-013 except C-006); no real socket opened.

### Tests for US1 — write first, verify red ⚠️

> **NOTE: Write ALL tests T017–T026 first, verify they ALL FAIL, then implement.**

- [X] T017 [US1] Write `test_execute_returns_execution_result_for_all_actions` in `tests/test_action_executor.py` — contract C-001: loop over `REGISTRY.list_actions()`, build each Action with `defn.to_action(datetime.now(UTC))`, call `executor.execute(action)`, assert `isinstance(result, ExecutionResult)` for each
- [X] T018 [US1] Write `test_success_and_emitted_count_for_lab_action` in `tests/test_action_executor.py` — contract C-002: execute `tcp_port_scan` with `target_ip="172.28.0.2"` and recording SendFn; assert `result.success is True` and `result.emitted_count >= 1`
- [X] T019 [US1] Write `test_execution_result_fields_match_action` in `tests/test_action_executor.py` — contract C-007: execute any action; assert `result.action_id == action.action_id` and `result.category == action.category`
- [X] T020 [US1] Write `test_error_is_none_on_success` in `tests/test_action_executor.py` — contract C-008: execute valid action; assert `result.success is True` implies `result.error is None`
- [X] T021 [US1] Write `test_unknown_action_id_returns_failure` in `tests/test_action_executor.py` — contract C-009: build `Action(action_id="unknown_action_xyz", category="scan", parameters={"target_ip": "172.28.0.2"}, timestamp=...)` (construct manually, not from REGISTRY); assert `result.success is False`, `result.emitted_count == 0`, `result.error is not None`
- [X] T022 [US1] Write `test_rate_zero_promoted_to_one` in `tests/test_action_executor.py` — contract C-010: execute `ssh_brute_force` with `parameters={"target_ip": "172.28.0.2", "target_port": 22, "attempts": 0, "timing_ms": 0}`; assert `result.emitted_count >= 1`
- [X] T023 [US1] Write `test_all_15_action_ids_have_handlers` in `tests/test_action_executor.py` — contract C-011: loop over `REGISTRY.list_actions()`, execute each, assert `not (result.success is False and result.error is not None and "no handler" in (result.error or "").lower())`
- [X] T024 [US1] Write `test_no_real_socket_in_unit_tests` in `tests/test_action_executor.py` — contract C-012: execute `tcp_port_scan` with a recording send_fn (not `_default_send_fn`); verify recording stub was called at least once and no `socket.socket` constructor was invoked (use monkeypatch to replace `socket.socket` with a sentinel that raises `AssertionError`; verify no exception)
- [X] T025 [US1] Write `test_execution_result_is_dataclass_with_five_fields` in `tests/test_action_executor.py` — contract C-013: `import dataclasses`; `field_names = {f.name for f in dataclasses.fields(ExecutionResult)}`; assert `field_names == {"action_id", "category", "success", "emitted_count", "error"}`
- [X] T026 [US1] Run `cd src && python -m pytest tests/test_action_executor.py -v` — confirm T017–T025 test functions appear and **FAIL** (execute() still raises NotImplementedError for valid actions after guard passes); record failure count

### Implementation for US1

- [X] T027 [US1] Add execute() dispatch skeleton to `src/aatf/action_executor.py` — after guard passes: look up `handler = self._handlers.get(action.action_id)`; if missing, return `ExecutionResult(action_id=action.action_id, category=action.category, success=False, emitted_count=0, error=f"no handler for {action.action_id!r}")` ; else call `count = handler(action, self._rng, self._send_fn, self._sleep_fn)` wrapped in try/except and return appropriate ExecutionResult
- [X] T028 [US1] Implement scan handlers in `src/aatf/action_executor.py`: `_handle_tcp_port_scan` (parse `port_range` like "1-1024", call send_fn for each port with `b"SYN"`), `_handle_udp_sweep` (same port iteration, `socket.SOCK_DGRAM` equivalent payload `b"UDP"`), `_handle_icmp_ping_sweep` (send_fn to port 7 once per `rate_pps`, payload `b"PING"`) — each returns `emitted_count`; promote rate=0 to 1 for all
- [X] T029 [US1] Implement brute handlers in `src/aatf/action_executor.py`: `_handle_ssh_brute_force` (call send_fn to port 22 × `max(1, attempts)` times with `b"SSH-2.0-test"`), `_handle_ftp_brute_force` (port 21 × `max(1, attempts)` with `b"USER test\r\n"`), `_handle_http_basic_brute` (port `target_port` × `max(1, attempts)` with HTTP GET + `Authorization: Basic` header bytes) — apply `_sleep_fn(_rng.uniform(0, timing_ms/1000))` between iterations
- [X] T030 [US1] Implement ssh handlers in `src/aatf/action_executor.py`: `_handle_ssh_user_enum` (send_fn to port 22 once per username in `usernames` list with `b"SSH-2.0-OpenSSH_7.4"` payload), `_handle_ssh_version_probe` (send_fn to `target_port` once with `b"SSH-2.0-OpenSSH_7.4"` + read-back bytes) — both return emitted_count
- [X] T031 [US1] Implement web handlers in `src/aatf/action_executor.py`: `_handle_http_dir_scan` (port `target_port`, send GET for each of `wordlist_size` paths like `/admin`, `/config`, etc. as bytes), `_handle_http_sqli_probe` (`/?q=1+UNION+SELECT+1--` payload × `rate_rps`, port `target_port`), `_handle_http_xss_probe` (`/?q=<script>alert(1)</script>` payload, port `target_port`) — HTTP requests as bytes via `send_fn`
- [X] T032 [US1] Implement dns handlers in `src/aatf/action_executor.py`: `_handle_dns_zone_transfer` (port 53, build DNS AXFR query bytes via `struct.pack(">HHHHHH", ...)` — 12-byte header + 0 question AXFR query for `aatf.lab`), `_handle_dns_subdomain_enum` (port 53, send simple A-record query bytes × `wordlist_size` — generate query via struct.pack for each label like `b"\x04mail\x04aatf\x03lab\x00"`)
- [X] T033 [US1] Implement exfil handlers in `src/aatf/action_executor.py`: `_handle_dns_exfil` (port 53, encode `b"A" * chunk_size` as hex-label DNS query × `chunks` parameter, default chunk_size=16), `_handle_http_exfil` (port `target_port`, HTTP POST with `Content-Type: application/octet-stream` and `b"EXFIL:" + b"X" * payload_size` body)
- [X] T034 [US1] Wire all 15 handlers into `self._handlers` in `ActionExecutor.__init__` in `src/aatf/action_executor.py` — dict keyed by exact action_id strings matching REGISTRY entries: `{"tcp_port_scan": _handle_tcp_port_scan, "udp_sweep": _handle_udp_sweep, "icmp_ping_sweep": _handle_icmp_ping_sweep, "ssh_brute_force": _handle_ssh_brute_force, "ftp_brute_force": _handle_ftp_brute_force, "http_basic_brute": _handle_http_basic_brute, "ssh_user_enum": _handle_ssh_user_enum, "ssh_version_probe": _handle_ssh_version_probe, "http_dir_scan": _handle_http_dir_scan, "http_sqli_probe": _handle_http_sqli_probe, "http_xss_probe": _handle_http_xss_probe, "dns_zone_transfer": _handle_dns_zone_transfer, "dns_subdomain_enum": _handle_dns_subdomain_enum, "dns_exfil": _handle_dns_exfil, "http_exfil": _handle_http_exfil}`
- [X] T035 [US1] Verify US1 tests pass: `cd src && python -m pytest tests/test_action_executor.py -v -k "not integration and not seed and not determinism"` — T017–T025 (9 tests) must all PASS

**Checkpoint**: All 15 handlers wired; recording SendFn pattern confirmed; ExecutionResult returned for every action.

---

## Phase 5: User Story 3 — Deterministic Execution Under Seed (Priority: P3)

**Goal**: Same seed + same Action → identical emitted_count on repeated calls. _rng.uniform() used for jitter, not random.random().

**Independent Test**: `pytest tests/test_action_executor.py -k "seed or determinism"` — 1 test passes.

### Tests for US3 — write first, verify red ⚠️

- [X] T036 [US3] Write `test_same_seed_produces_identical_emitted_count` in `tests/test_action_executor.py` — contract C-006: create `calls_a: list = []`, `calls_b: list = []`; create `executor_a = ActionExecutor(seed=42, send_fn=lambda h,p,d: calls_a.append((h,p,d)), sleep_fn=lambda _: None)`; same for executor_b with calls_b; build `ssh_brute_force` Action with `attempts=5, timing_ms=100`; execute on both; assert `len(calls_a) == len(calls_b)` and `result_a.emitted_count == result_b.emitted_count`
- [X] T037 [US3] Run `cd src && python -m pytest tests/test_action_executor.py::test_same_seed_produces_identical_emitted_count -v` — confirm **FAILS** before implementation (or verify it already PASSES due to seeded RNG in T006 — if PASSES, the test is valid and this task is a no-op)

### Implementation for US3

- [X] T038 [US3] Audit all 15 handlers in `src/aatf/action_executor.py` to confirm every jitter call uses `rng.uniform(...)` (the passed-in rng argument) and NOT `random.uniform(...)` or `random.random()` (module-level global random) — fix any handlers that use the global random module instead of the injected `rng`
- [X] T039 [US3] Verify determinism test passes: `cd src && python -m pytest tests/test_action_executor.py::test_same_seed_produces_identical_emitted_count -v` — must PASS

**Checkpoint**: Seeded reproducibility confirmed. All 3 user stories are now fully tested and implemented.

---

## Phase 6: Integration Test + Polish

**Purpose**: Add auto-skip integration test, run linters, final count verification, commit.

- [X] T040 Write `test_scan_triggers_suricata_alert` integration test in `tests/test_action_executor.py` — contract C-015: decorate with `@pytest.mark.skipif(subprocess.run(["docker", "inspect", "aatf-attacker"], capture_output=True).returncode != 0, reason="lab not running")`; execute `tcp_port_scan` with no send_fn override (uses real socket); `time.sleep(2)`; read `docker exec aatf-defender cat /var/log/suricata/eve.json`; assert at least one line parsed contains `"alert"` and `emitted_count >= 1`
- [X] T041 Run `ruff check src/aatf/action_executor.py tests/test_action_executor.py` — fix any lint errors (E501 line-too-long: wrap long strings with implicit concatenation; F401 unused imports: remove any)
- [X] T042 Run `ruff format src/aatf/action_executor.py tests/test_action_executor.py` — apply formatting
- [X] T043 Run full test suite: `cd src && python -m pytest --tb=short -q` — confirm ≥148 passed, 4 skipped (134 baseline + ≥14 new unit tests passing; C-015 integration adds 1 skip to baseline 3)
- [X] T044 Commit: `git add src/aatf/action_executor.py tests/test_action_executor.py && git commit -m "feat(F08): add ActionExecutor with 15 defanged handlers, ExternalTargetError guard, injectable SendFn/SleepFn"`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US2 Guard)**: Depends on Phase 2 — must complete BEFORE Phase 4 (guard is called at top of execute() before handlers)
- **Phase 4 (US1 Handlers)**: Depends on Phase 3 (guard must be live so green tests pass cleanly)
- **Phase 5 (US3 Seed)**: Depends on Phase 4 (handlers must exist to test determinism meaningfully)
- **Phase 6 (Polish)**: Depends on Phases 3–5 complete

### Within Each Phase

- Tests MUST be written and verified **red** before implementation
- Implement, then verify **green**
- Do not advance to next phase until current phase is green

### Parallel Opportunities

Within Phase 4 implementation: T027–T033 each write different handler groups (all within the same file but distinct functions). These can be drafted in parallel mentally but must be committed to the same file sequentially.

---

## Parallel Example: Phase 4 Test Writing

```bash
# All 9 US1 test functions (T017–T025) can be written in one pass to tests/test_action_executor.py
# before any implementation. Run once after all are written:
cd src && python -m pytest tests/test_action_executor.py -v --tb=no -q
# Expect: 9 FAILED, 4 PASSED (the US2 tests from Phase 3)
```

---

## Implementation Strategy

### MVP First (US2 guard + US1 core handlers)

1. Complete Phase 1: Setup + Phase 2: Foundational
2. Complete Phase 3: US2 Guard (4 tests green)
3. Complete Phase 4 through T027 dispatch skeleton: verify C-009 unknown-handler test passes
4. **STOP and VALIDATE**: guard + unknown-handler path working — core contract met
5. Continue T028–T035: add all 15 handlers

### Incremental Delivery

1. Setup → Foundational → Guard → verify 4+1 contract tests
2. Add scan handlers (T028) → run C-001 for scan category
3. Add brute handlers (T029) → run C-001 for brute category
4. Continue per handler group through T035
5. Seed phase → Polish → commit

---

## Notes

- Recording stub pattern: `calls: list[tuple] = []; send_fn = lambda h, p, d: calls.append((h, p, d))` — use this consistently across all unit tests
- `sleep_fn=lambda _: None` must be injected in every unit test (never use default `time.sleep`)
- Promote rate=0 to 1 with `max(1, value)` — apply in every handler that uses a count parameter
- `_default_send_fn` uses `socket.SOCK_STREAM` for TCP and `socket.SOCK_DGRAM` for UDP/DNS — two helper functions if needed, or single function with a `sock_type` arg
- C-015 integration test: import `subprocess` at top of test file with `TYPE_CHECKING` guard or unconditionally — either is fine since subprocess is stdlib
- Ruff E501: any reason string or handler comment over 88 chars must be split with implicit string concatenation
- After T044 commit, the user will run `git push origin 011-e2-action-executor` manually
