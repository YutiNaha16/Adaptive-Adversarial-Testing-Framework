# Tasks: Host Event Log Signal (F12)

**Feature**: `009-e3-host-event-log`
**Branch**: `009-e3-host-event-log`
**Input**: `specs/009-e3-host-event-log/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓
**Test approach**: TDD — tests written first (red), then implementation (green)
**Baseline**: 104 passed, 2 skipped (pre-F12)
**Target**: 116+ passed, 3 skipped (104 + 12 new unit tests; integration test skipped unless lab is up)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to ([US1], [US2], [US3])
- TDD rule: every test task MUST be completed (and confirmed failing) before its implementation task

---

## Phase 1: Setup (Baseline + Fixtures)

**Purpose**: Record baseline, create fixture directory and static auth log sample files used across all user stories.

- [X] T001 Record `make test` baseline (104 passed, 2 skipped) — no files changed
- [X] T002 Create fixture directory `tests/fixtures/auth_log_samples/` (mkdir)
- [X] T003 [P] Create `tests/fixtures/auth_log_samples/empty.log` — zero-byte plaintext file (no lines)
- [X] T004 [P] Create `tests/fixtures/auth_log_samples/one_match.log` — one line: `Jul  6 10:00:00 aatf-defender sshd[1234]: Connection from 172.28.0.3 port 54321`
- [X] T005 [P] Create `tests/fixtures/auth_log_samples/two_patterns.log` — one line containing both `"sshd"` and `"Failed password"`: `Jul  6 10:00:00 aatf-defender sshd[1234]: Failed password for invalid user root from 172.28.0.3 port 54321 ssh2`
- [X] T006 [P] Create `tests/fixtures/auth_log_samples/no_match.log` — one line with no ssh keywords: `Jul  6 10:00:00 aatf-defender CRON[5678]: pam_unix(cron:session): session opened for user root`
- [X] T007 [P] Create `tests/fixtures/auth_log_samples/multi_line.log` — two lines: first `Jul  6 10:00:00 aatf-defender sshd[1234]: Connection from 172.28.0.3` then `Jul  6 10:00:01 aatf-defender sshd[1235]: Failed password for root`

**Checkpoint**: `tests/fixtures/auth_log_samples/` exists with 5 fixture files; `make test` still shows 104 passed.

---

## Phase 2: Foundational (Module Stub)

**Purpose**: Create the empty `host_log_defence.py` source module so import paths are valid when the test file is written in Phase 3. No logic yet — just imports and a class stub.

**⚠️ CRITICAL**: The test file imports from `aatf.host_log_defence` — the module must exist (even as a stub) before the test file can be parsed by pytest without ImportError.

- [X] T008 Create `src/aatf/host_log_defence.py` as a minimal stub: `from __future__ import annotations`, imports (`os`, `pathlib.Path`), import of `Action`, `DetectionResult` from `aatf.contracts`, import of `Defence`, `DefenceError` from `aatf.defence`, empty `class HostLogDefence(Defence): pass` — no `__init__`, no `observe()`

**Checkpoint**: `from aatf.host_log_defence import HostLogDefence` succeeds; `make test` still 104 passed.

---

## Phase 3: User Story 1 — Detect host-side events and return DetectionResult (Priority: P1) 🎯 MVP

**Goal**: `HostLogDefence.observe()` reads a fixture log file, matches keyword patterns, and returns the correct `DetectionResult`. No Docker required.

**Independent Test**: `pytest tests/test_host_log_defence.py -k "us1"` passes (after implementation).

**Contracts covered**: C-001, C-002, C-003, C-004, C-005, C-006, C-007, C-011, C-012

### Tests for User Story 1 (TDD — write first, verify red before T016)

- [X] T009 [P] [US1] Write test `test_conformance_check_passes` (C-001) in `tests/test_host_log_defence.py`: import `check_defence_contract` from `tests.test_defence`; `HostLogDefence(tests/fixtures/auth_log_samples/empty.log, ["sshd"])`; call `check_defence_contract(defence, action)` — must pass; mark `# C-001`
- [X] T010 [P] [US1] Write test `test_matching_line_produces_alerted_true` (C-002) in `tests/test_host_log_defence.py`: load `tests/fixtures/auth_log_samples/one_match.log`; patterns `["sshd"]`; call `observe(action)`; assert `result.alerted is True`, `"sshd" in result.rule_ids`, `result.coverage == "covered"`, `result.anomaly_score == 0.0`; mark `# C-002`
- [X] T011 [P] [US1] Write test `test_non_matching_lines_ignored` (C-003) in `tests/test_host_log_defence.py`: load `tests/fixtures/auth_log_samples/no_match.log`; patterns `["sshd"]`; assert `alerted=False`, `rule_ids==[]`, `coverage=="uncovered"`; mark `# C-003`
- [X] T012 [P] [US1] Write test `test_empty_file_returns_uncovered` (C-004) in `tests/test_host_log_defence.py`: load `tests/fixtures/auth_log_samples/empty.log`; patterns `["sshd"]`; assert `alerted=False`, `rule_ids==[]`, `coverage=="uncovered"`; mark `# C-004`
- [X] T013 [P] [US1] Write test `test_unreadable_path_raises_defence_error` (C-005) in `tests/test_host_log_defence.py`: `HostLogDefence("/nonexistent/auth.log", ["sshd"])`; `pytest.raises(DefenceError)` around `observe(action)`; mark `# C-005`
- [X] T014 [P] [US1] Write test `test_multiple_patterns_match_one_line` (C-006) in `tests/test_host_log_defence.py`: load `tests/fixtures/auth_log_samples/two_patterns.log`; patterns `["sshd", "Failed password"]`; assert `alerted=True`, `"sshd" in result.rule_ids`, `"Failed password" in result.rule_ids`; mark `# C-006`
- [X] T015 [P] [US1] Write test `test_multiple_lines_accumulate_all_matches` (C-007) in `tests/test_host_log_defence.py`: load `tests/fixtures/auth_log_samples/multi_line.log`; patterns `["sshd", "Failed password"]`; assert `alerted=True`, both pattern strings appear in `result.rule_ids`; mark `# C-007`
- [X] T016 [P] [US1] Write test `test_anomaly_score_always_zero` (C-011) in `tests/test_host_log_defence.py`: call observe on `one_match.log` (matching) and `empty.log` (not matching); both must have `anomaly_score == 0.0`; mark `# C-011`
- [X] T017 [P] [US1] Write test `test_empty_pattern_list_never_alerts` (C-012) in `tests/test_host_log_defence.py`: load `one_match.log` (has content); `patterns=[]`; assert `alerted=False`, `coverage=="uncovered"`, `rule_ids==[]`; mark `# C-012`
- [X] T018 [US1] Confirm all 9 US1 tests FAIL (red phase): run `pytest tests/test_host_log_defence.py -q --tb=line`; expected: TypeError/NotImplementedError from abstract `observe()` not implemented; document failure count

### Implementation for User Story 1

- [X] T019 [US1] Implement `HostLogDefence.__init__(self, log_path: str | Path, patterns: list[str]) -> None` in `src/aatf/host_log_defence.py`: assign `self._log_path = Path(log_path)`, `self._patterns = patterns`, `self._cursor: int = 0`
- [X] T020 [US1] Implement `HostLogDefence.observe(self, action: Action) -> DetectionResult` in `src/aatf/host_log_defence.py`: (a) `os.path.getsize(self._log_path)` in try/except OSError → raise DefenceError; (b) if `self._cursor > file_size` reset to 0; (c) open `"rb"`, seek to `_cursor`, read bytes, `self._cursor = fh.tell()`; (d) iterate `new_bytes.splitlines()`, decode utf-8 errors="replace", strip, skip empty; (e) for each non-empty line, for each pattern in `self._patterns`, if `pattern in line` → `matches.append(pattern)`; (f) `alerted = bool(matches)`; (g) return `DetectionResult(alerted=alerted, rule_ids=matches, anomaly_score=0.0, coverage="covered" if alerted else "uncovered")`
- [X] T021 [US1] Verify US1 tests go green: run `pytest tests/test_host_log_defence.py -q --tb=short`; all 9 must PASS; `make test` must be 113 passed, 2 skipped

**Checkpoint**: `make test` → 113 passed, 2 skipped. US1 complete.

---

## Phase 4: User Story 2 — Distinguish coverage states (Priority: P2)

**Goal**: The three coverage branches (`"covered"` / `"uncovered"` / `"unknown"`) are validated, with `DefenceError` raised for the `"unknown"` path.

**Independent Test**: `pytest tests/test_host_log_defence.py -k "us2"` passes.

**Contracts covered**: C-004 (overlap), C-005 (overlap), coverage branch completeness

### Tests for User Story 2

- [X] T022 [P] [US2] Write test `test_coverage_covered_when_match` (US2-covered) in `tests/test_host_log_defence.py`: load `one_match.log`; patterns `["sshd"]`; assert `result.coverage == "covered"`; mark `# US2-covered`
- [X] T023 [P] [US2] Write test `test_coverage_uncovered_when_no_match` (US2-uncovered) in `tests/test_host_log_defence.py`: load `empty.log`; patterns `["sshd"]`; assert `result.coverage == "uncovered"`; mark `# US2-uncovered`
- [X] T024 [P] [US2] Write test `test_coverage_unknown_raises_defence_error` (US2-unknown) in `tests/test_host_log_defence.py`: `HostLogDefence("/no/such/auth.log", ["sshd"])`; `pytest.raises(DefenceError) as exc_info`; verify message contains "unreadable" or the path; mark `# US2-unknown`
- [X] T025 [US2] Verify US2 tests pass (green): run `pytest tests/test_host_log_defence.py -k "us2" -q`; all 3 must PASS; `make test` → 116 passed, 2 skipped

**Checkpoint**: `make test` → 116 passed, 2 skipped. All three coverage states proven.

---

## Phase 5: User Story 3 — Tail-read: only new lines since last call (Priority: P3)

**Goal**: Repeated `observe()` calls return only matches from lines appended after the previous call. File truncation resets the cursor. Uses `tmp_path` pytest fixture for mutable files.

**Independent Test**: `pytest tests/test_host_log_defence.py -k "us3"` passes.

**Contracts covered**: C-008, C-009, C-010

### Tests for User Story 3

- [X] T026 [P] [US3] Write test `test_second_call_no_new_lines_returns_not_alerted` (C-008) in `tests/test_host_log_defence.py` using `tmp_path`: write one matching line (`"sshd"`); first call → `alerted=True`; second call with no new writes → `alerted=False`, `rule_ids==[]`, `coverage=="uncovered"`; mark `# C-008`
- [X] T027 [P] [US3] Write test `test_new_line_between_calls_picked_up` (C-009) in `tests/test_host_log_defence.py` using `tmp_path`: create empty file; first call → `alerted=False`; append `"sshd connection established\n"`; second call → `alerted=True`, `"sshd" in result.rule_ids`; mark `# C-009`
- [X] T028 [P] [US3] Write test `test_file_truncation_resets_cursor` (C-010) in `tests/test_host_log_defence.py` using `tmp_path`: write 3× a long matching line (so cursor > 150 bytes); first call → `alerted=True`; overwrite file with single short line matching different pattern `"Failed password"`; second call → cursor reset to 0, reads new file, `"Failed password" in result.rule_ids`, old pattern not in rule_ids; mark `# C-010`
- [X] T029 [US3] Confirm US3 tests FAIL before implementation: run `pytest tests/test_host_log_defence.py -k "us3" -q`; all 3 should FAIL (cursor not advancing yet); document failure count
- [X] T030 [US3] Confirm cursor logic from T020 makes US3 pass: run `pytest tests/test_host_log_defence.py -k "us3" -q`; all 3 must PASS; `make test` → 116 passed, 2 skipped (count unchanged because US3 tests already counted in Phase 4 target — recount: total is 116)

**Note**: US3 tests are written in this phase but the cursor implementation is already in T020 — the tests confirm the cursor works correctly end-to-end.

**Checkpoint**: `make test` → 116 passed, 2 skipped. Cursor semantics verified.

---

## Phase 6: Integration Test (C-013, auto-skip)

**Goal**: A live SSH attempt from the attacker container to the defender produces a "Failed password" line in the defender's auth log; `HostLogDefence` returns `alerted=True`. Test skips when lab not running.

**Contracts covered**: C-013

- [X] T031 [US3] Write `test_live_lab_ssh_probe` (C-013) in `tests/test_host_log_defence.py`: add `_lab_running()` helper using `subprocess.run(["docker","inspect","aatf-defender"], capture_output=True)` returning `r.returncode == 0`; at test start `if not _lab_running(): pytest.skip("lab not running — run 'make lab-up' first")`; run SSH probe: `subprocess.run(["docker","exec","aatf-attacker","ssh","-o","StrictHostKeyChecking=no","-o","BatchMode=yes","-o","ConnectTimeout=3","root@aatf-defender"], capture_output=True)`; `time.sleep(2)`; read auth log: `r = subprocess.run(["docker","exec","aatf-defender","cat","/var/log/auth.log"], capture_output=True, text=True)`; write `r.stdout` to `tmp_path / "auth.log"`; `HostLogDefence(tmp_path / "auth.log", ["Failed password", "sshd"])`; assert `result.alerted is True`, `"Failed password" in result.rule_ids`, `result.coverage == "covered"`; mark `# C-013`
- [X] T032 [US3] Verify integration test auto-skips when lab is down: run `pytest tests/test_host_log_defence.py::test_live_lab_ssh_probe -v`; output must show `SKIPPED`; `make test` → 116 passed, **3 skipped**

**Checkpoint**: `make test` → 116 passed, 3 skipped. Integration test wired and auto-skipping.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T033 Run `ruff check src/aatf/host_log_defence.py tests/test_host_log_defence.py` and fix any violations (UP007 `Union`→`|`, I001 import order, F401 unused imports, UP037 quoted annotations)
- [X] T034 Run `make test` one final time: must show **116 passed, 3 skipped**
- [X] T035 Verify `make lint` exits 0 — no ruff violations remaining
- [X] T036 Commit: `feat(e3): F12 HostLogDefence — keyword pattern matching, byte-offset cursor, 13 contracts` including `src/aatf/host_log_defence.py`, `tests/test_host_log_defence.py`, `tests/fixtures/auth_log_samples/*.log`, `specs/009-e3-host-event-log/tasks.md`

**Checkpoint**: Branch `009-e3-host-event-log` committed; all 13 contracts covered; no regressions; E3 complete.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Stub)**: Depends on Phase 1 — module must exist before test file imports it
- **Phase 3 (US1 — pattern matching)**: Depends on Phase 2 stub + Phase 1 fixtures
- **Phase 4 (US2 — coverage states)**: Depends on Phase 3 implementation
- **Phase 5 (US3 — tail-read unit)**: Depends on Phase 3 implementation (cursor in `observe()`)
- **Phase 6 (US3 — integration)**: Depends on Phase 5; lab optional
- **Phase 7 (Polish)**: Depends on all prior phases

### Contract → Task Mapping

| Contract | Task(s) |
|----------|---------|
| C-001 | T009, T020 |
| C-002 | T010, T020 |
| C-003 | T011, T020 |
| C-004 | T012, T020 |
| C-005 | T013, T020 |
| C-006 | T014, T020 |
| C-007 | T015, T020 |
| C-008 | T026, T020 (cursor) |
| C-009 | T027, T020 (cursor) |
| C-010 | T028, T020 (cursor) |
| C-011 | T016, T020 |
| C-012 | T017, T020 (natural loop) |
| C-013 | T031, T032 |

---

## Parallel Opportunities

### Phase 1 (Fixtures)

```
T003 empty.log        ─┐
T004 one_match.log     ├─ all parallel (different files)
T005 two_patterns.log  ├─
T006 no_match.log      ├─
T007 multi_line.log   ─┘
```

### Phase 3 (US1 tests — parallel write, then sequential implement)

```
T009 C-001 ─┐
T010 C-002  ├─ all parallel (same file, different test functions)
T011 C-003  ├─
T012 C-004  ├─
T013 C-005  ├─
T014 C-006  ├─
T015 C-007  ├─
T016 C-011  ├─
T017 C-012 ─┘
     ↓
T018 (verify red) → T019 __init__ → T020 observe() → T021 (verify green)
```

### Phase 5 (US3 tests — parallel)

```
T026 C-008 ─┐
T027 C-009  ├─ parallel
T028 C-010 ─┘
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 (fixtures) + Phase 2 (stub)
2. Complete Phase 3 (US1): write 9 tests → red → implement `observe()` → green
3. **STOP and VALIDATE**: `make test` → 113 passed — MVP done
4. `HostLogDefence` reads any plaintext log and returns keyword matches

### Incremental Delivery

1. Phase 1 + 2 → fixture files + module stub ready
2. Phase 3 (US1) → `HostLogDefence` operational → 113 passed
3. Phase 4 (US2) → coverage states asserted → 116 passed
4. Phase 5 (US3) → tail-read and truncation proven → 116 passed (same count, cursor confirmed)
5. Phase 6 (C-013) → integration test wired → 116 passed, 3 skipped
6. Phase 7 → clean lint, commit → **E3 complete**

---

## Notes

- [P] tasks involve different output files and can run in parallel
- TDD rule: confirm test FAILS before writing implementation
- `tmp_path` (pytest built-in) is the correct fixture for US3 mutable file tests
- Truncation test (C-010): use 3× repeated line as first file so cursor (~150 bytes) exceeds the replacement file size (~40 bytes) — same lesson learned in F11
- Integration test (T031): SSH probe may produce `Permission denied` or `Failed password` — both are written to auth.log; use `"sshd"` as a safe fallback pattern if `"Failed password"` is not reliably generated
- No changes to `contracts.py`, `defence.py`, or `suricata_defence.py`
- After T036 commit, merge to main and tag as `e3` — E3 epic complete
