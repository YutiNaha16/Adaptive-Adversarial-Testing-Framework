# Tasks: Suricata Defence Adapter (F11)

**Feature**: `008-e3-suricata-adapter`
**Branch**: `008-e3-suricata-adapter`
**Input**: `specs/008-e3-suricata-adapter/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓
**Test approach**: TDD — tests written first (red), then implementation (green)
**Baseline**: 90 passed, 1 skipped (pre-F11)
**Target**: 101+ passed, 1 skipped (90 + 11 new unit tests; integration test skipped unless lab is up)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to ([US1], [US2], [US3])
- TDD rule: every test task MUST be completed (and confirmed failing) before its implementation task

---

## Phase 1: Setup (Baseline + Fixtures)

**Purpose**: Record baseline, create fixture directory and static eve.json sample files used across all user stories.

- [X] T001 Record `make test` baseline (90 passed, 1 skipped) — no files changed
- [X] T002 Create fixture directory `tests/fixtures/eve_samples/` (mkdir, add empty `.gitkeep` placeholder)
- [X] T003 [P] Create `tests/fixtures/eve_samples/empty.json` — zero-byte JSONL file (empty, no lines)
- [X] T004 [P] Create `tests/fixtures/eve_samples/one_alert.json` — one JSONL line: `{"event_type":"alert","timestamp":"2026-07-06T10:00:00.000000+0000","alert":{"signature_id":2001219,"signature":"ET SCAN Potential SSH Scan"},"src_ip":"172.28.0.3","dest_ip":"172.28.0.2"}`
- [X] T005 [P] Create `tests/fixtures/eve_samples/two_alerts.json` — two JSONL lines: alert with SID 2001219 then alert with SID 2034660, each on its own line
- [X] T006 [P] Create `tests/fixtures/eve_samples/malformed.json` — two lines: one valid alert line (SID 9999) followed by one line containing the literal text `NOT_JSON`
- [X] T007 [P] Create `tests/fixtures/eve_samples/stats_only.json` — one JSONL line: `{"event_type":"stats","timestamp":"2026-07-06T10:00:00.000000+0000","stats":{"uptime":42}}` (no alert lines)

**Checkpoint**: `tests/fixtures/eve_samples/` exists with 5 fixture files; `make test` still shows 90 passed.

---

## Phase 2: Foundational (Module Shell)

**Purpose**: Create the empty `suricata_defence.py` source module so import paths are valid when test file is written in Phase 3. No logic yet — just the file with imports and class stub.

**⚠️ CRITICAL**: Phase 3 writes the test file first, but the test file imports from `aatf.suricata_defence` — the module must exist (even as a stub) before the test file can be parsed by pytest.

- [X] T008 Create `src/aatf/suricata_defence.py` as a minimal stub: `from __future__ import annotations`, required imports (`json`, `os`, `pathlib.Path`), import of `Action`, `DetectionResult` from `aatf.contracts`, import of `Defence`, `DefenceError` from `aatf.defence`, empty `class SuricataDefence(Defence): pass` — no logic, no `observe()` implementation

**Checkpoint**: `from aatf.suricata_defence import SuricataDefence` succeeds; `make test` still 90 passed (no new tests yet; SuricataDefence.observe not implemented so abstract method error would only fire at instantiation).

---

## Phase 3: User Story 1 — Read alert events and return DetectionResult (Priority: P1) 🎯 MVP

**Goal**: `SuricataDefence.observe()` reads a fixture eve.json, parses alert lines, extracts SIDs, and returns the correct `DetectionResult`. No Docker required.

**Independent Test**: `pytest tests/test_suricata_defence.py -k "us1"` passes (after implementation).

**Contracts covered**: C-001, C-002, C-003, C-004, C-005, C-006, C-007, C-011

### Tests for User Story 1 (TDD — write first, verify red before T013)

- [X] T009 [P] [US1] Write test `test_conformance_check_passes` (C-001) in `tests/test_suricata_defence.py`: import `check_defence_contract` from `tests.test_defence`; create `SuricataDefence` pointing at `tests/fixtures/eve_samples/empty.json`; call `check_defence_contract(defence, action)` — must pass; mark `# C-001`
- [X] T010 [P] [US1] Write test `test_alert_line_produces_alerted_true` (C-002) in `tests/test_suricata_defence.py`: load `tests/fixtures/eve_samples/one_alert.json`; create `SuricataDefence(path)`; call `observe(action)`; assert `result.alerted is True`, `"2001219" in result.rule_ids`, `result.coverage == "covered"`, `result.anomaly_score == 0.0`; mark `# C-002`
- [X] T011 [P] [US1] Write test `test_non_alert_lines_ignored` (C-003) in `tests/test_suricata_defence.py`: load `tests/fixtures/eve_samples/stats_only.json`; assert `alerted=False`, `rule_ids==[]`, `coverage=="uncovered"`; mark `# C-003`
- [X] T012 [P] [US1] Write test `test_empty_file_returns_uncovered` (C-004) in `tests/test_suricata_defence.py`: load `tests/fixtures/eve_samples/empty.json`; assert `alerted=False`, `rule_ids==[]`, `coverage=="uncovered"`; mark `# C-004`
- [X] T013 [P] [US1] Write test `test_unreadable_path_raises_defence_error` (C-005) in `tests/test_suricata_defence.py`: `SuricataDefence("/nonexistent/eve.json")`; `pytest.raises(DefenceError)` around `observe(action)`; mark `# C-005`
- [X] T014 [P] [US1] Write test `test_multiple_alerts_all_sids_returned` (C-006) in `tests/test_suricata_defence.py`: load `tests/fixtures/eve_samples/two_alerts.json`; assert `alerted=True`, `"2001219" in result.rule_ids`, `"2034660" in result.rule_ids`; mark `# C-006`
- [X] T015 [P] [US1] Write test `test_malformed_line_skipped` (C-007) in `tests/test_suricata_defence.py`: load `tests/fixtures/eve_samples/malformed.json`; assert `alerted=True`, `result.rule_ids == ["9999"]` (valid alert returned, bad line skipped, no exception); mark `# C-007`
- [X] T016 [P] [US1] Write test `test_anomaly_score_always_zero` (C-011) in `tests/test_suricata_defence.py`: call observe on `one_alert.json` (alerted) and `empty.json` (not alerted); both must have `anomaly_score == 0.0`; mark `# C-011`
- [X] T017 [US1] Confirm all 8 US1 tests FAIL (red phase): run `pytest tests/test_suricata_defence.py -q --tb=short`; expected failures: TypeError/NotImplementedError from abstract `observe()` not yet implemented; document failure count

### Implementation for User Story 1

- [X] T018 [US1] Implement `SuricataDefence.__init__(self, eve_path: str | Path) -> None` in `src/aatf/suricata_defence.py`: assign `self._eve_path = Path(eve_path)`, `self._cursor: int = 0`
- [X] T019 [US1] Implement `SuricataDefence.observe(self, action: Action) -> DetectionResult` in `src/aatf/suricata_defence.py`: (a) call `os.path.getsize(self._eve_path)` in try/except OSError → raise DefenceError on failure; (b) if `self._cursor > file_size` reset to 0; (c) open file in `"rb"`, seek to `_cursor`, read remaining bytes, `self._cursor = fh.tell()`; (d) iterate `new_bytes.splitlines()`, decode utf-8 errors="replace", skip empty, json.loads in try/except JSONDecodeError → continue; (e) collect `str(event["alert"]["signature_id"])` for lines where `event.get("event_type") == "alert"` and `signature_id is not None`; (f) return `DetectionResult(alerted=bool(sids), rule_ids=sids, anomaly_score=0.0, coverage="covered" if sids else "uncovered")`
- [X] T020 [US1] Verify US1 tests go green: run `pytest tests/test_suricata_defence.py -q --tb=short`; all 8 must PASS; `make test` count must be 98 passed, 1 skipped

**Checkpoint**: `make test` → 98 passed, 1 skipped. US1 complete. SuricataDefence correctly parses fixture eve.json files.

---

## Phase 4: User Story 2 — Distinguish coverage states (Priority: P2)

**Goal**: The three coverage branches (`"covered"` / `"uncovered"` / `"unknown"`) are validated against distinct fixture scenarios, with `DefenceError` raised for the `"unknown"` path.

**Independent Test**: `pytest tests/test_suricata_defence.py -k "us2"` passes (after implementation — coverage logic is already in T019; these tests verify the complete state machine).

**Contracts covered**: C-004 (partial overlap with US1), C-005 (overlap), coverage branch completeness check

### Tests for User Story 2

- [X] T021 [P] [US2] Write test `test_coverage_covered_when_alert` (US2 branch: covered) in `tests/test_suricata_defence.py`: load `one_alert.json`; assert `result.coverage == "covered"`; mark `# US2-covered`
- [X] T022 [P] [US2] Write test `test_coverage_uncovered_when_no_alert` (US2 branch: uncovered) in `tests/test_suricata_defence.py`: load `empty.json`; assert `result.coverage == "uncovered"`; mark `# US2-uncovered`
- [X] T023 [P] [US2] Write test `test_coverage_unknown_raises_defence_error` (US2 branch: unknown) in `tests/test_suricata_defence.py`: `SuricataDefence("/no/such/file.json")`; `pytest.raises(DefenceError)`; verify the exception carries a message mentioning "unreadable" or the path; mark `# US2-unknown`

- [X] T024 [US2] Verify US2 tests pass (green): run `pytest tests/test_suricata_defence.py -k "us2" -q`; all 3 must PASS; no regressions in existing tests; `make test` count must be 101 passed, 1 skipped

**Checkpoint**: `make test` → 101 passed, 1 skipped. All three coverage states proven by distinct test cases.

---

## Phase 5: User Story 3 — Tail-read: only new lines since last call (Priority: P3)

**Goal**: Repeated `observe()` calls return only alerts from lines appended after the previous call. File truncation resets the cursor.

**Independent Test**: `pytest tests/test_suricata_defence.py -k "us3"` passes (uses `tmp_path` pytest fixture for mutable files).

**Contracts covered**: C-008, C-009, C-010

### Tests for User Story 3

- [X] T025 [P] [US3] Write test `test_second_call_no_new_lines_returns_not_alerted` (C-008) in `tests/test_suricata_defence.py` using `tmp_path`: write one alert to temp file; first call → `alerted=True`; second call with no new writes → `alerted=False`, `rule_ids==[]`, `coverage=="uncovered"`; mark `# C-008`
- [X] T026 [P] [US3] Write test `test_new_line_between_calls_picked_up` (C-009) in `tests/test_suricata_defence.py` using `tmp_path`: create empty temp file; first call → `alerted=False`; append one alert line (SID 7777); second call → `alerted=True`, `"7777" in result.rule_ids`; mark `# C-009`
- [X] T027 [P] [US3] Write test `test_file_truncation_resets_cursor` (C-010) in `tests/test_suricata_defence.py` using `tmp_path`: write 80-byte content (alert line, SID 1111); first call → cursor advances past 0; overwrite same path with shorter content (alert SID 2222, <80 bytes); second call → cursor was > file size so reset to 0 → reads whole new file → `"2222" in result.rule_ids`, `"1111" not in result.rule_ids`; mark `# C-010`

- [X] T028 [US3] Confirm US3 tests FAIL before cursor logic exists: run `pytest tests/test_suricata_defence.py -k "us3" -q`; T025 should FAIL (cursor not yet advanced after first call in stub), T026/T027 should FAIL similarly; document failure count
- [X] T029 [US3] Confirm cursor advancement is already in T019 implementation: re-run `pytest tests/test_suricata_defence.py -k "us3" -q`; all 3 must PASS; `make test` → 104 passed, 1 skipped

**Checkpoint**: `make test` → 104 passed, 1 skipped. Cursor semantics verified.

---

## Phase 6: User Story 3 — Integration Test (C-012, auto-skip)

**Goal**: A live nmap probe from the attacker container fires SID 2001219; `SuricataDefence` reading the Docker volume returns `alerted=True`. Test skips automatically when lab is not running.

**Independent Test**: `pytest tests/test_suricata_defence.py::test_live_lab_probe -v` — passes if `make lab-up` was run; skips cleanly otherwise.

**Contracts covered**: C-012

### Tests for Integration

- [X] T030 [US3] Write `test_live_lab_probe` (C-012) in `tests/test_suricata_defence.py`: add `_lab_running()` helper using `subprocess.run(["docker","inspect","aatf-suricata"], capture_output=True)` returning `r.returncode == 0`; at test start `if not _lab_running(): pytest.skip("lab not running — run 'make lab-up' first")`; run `subprocess.run(["docker","exec","aatf-attacker","nmap","-sS","-p","22","--min-rate","1000","aatf-defender"], check=True)`; `time.sleep(2)`; create `SuricataDefence("/var/lib/docker/volumes/aatf-eve/_data/eve.json")`; assert `result.alerted is True`, `"2001219" in result.rule_ids`, `result.coverage == "covered"`; mark `# C-012`
- [X] T031 [US3] Verify integration test auto-skips when lab is down: run `pytest tests/test_suricata_defence.py::test_live_lab_probe -v`; output must show `SKIPPED`; `make test` total must remain 104 passed, **2 skipped** (old isolation skip + new integration skip)

**Checkpoint**: `make test` → 104 passed, 2 skipped. Integration test wired and auto-skipping.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Lint, final test count validation, commit.

- [X] T032 Run `ruff check src/aatf/suricata_defence.py tests/test_suricata_defence.py` and fix any violations (common: UP007 `Union` → `|`, I001 import order, UP017 `timezone.utc` → `UTC`, UP024 `IOError` → `OSError`, UP037 quoted annotations)
- [X] T033 Run `make test` one final time and record counts: must show exactly **104 passed, 2 skipped** (or 104 passed, 1 skipped if lab is down — integration test accounts for the variable)
- [X] T034 Verify `make lint` exits 0 — no ruff violations remaining
- [X] T035 Commit with message: `feat(e3): F11 SuricataDefence adapter — byte-offset cursor, 3 coverage states, 12 contracts` including all new/modified files: `src/aatf/suricata_defence.py`, `tests/test_suricata_defence.py`, `tests/fixtures/eve_samples/*.json`, `specs/008-e3-suricata-adapter/tasks.md`

**Checkpoint**: Branch `008-e3-suricata-adapter` committed; all 12 contracts covered by tests; no regressions.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational stub)**: Depends on Phase 1 — module must exist before test file can import it
- **Phase 3 (US1 — alert parsing)**: Depends on Phase 2 stub + Phase 1 fixtures
- **Phase 4 (US2 — coverage states)**: Depends on Phase 3 implementation (coverage logic lives in `observe()`)
- **Phase 5 (US3 — tail-read unit)**: Depends on Phase 3 implementation (cursor logic lives in `observe()`)
- **Phase 6 (US3 — integration)**: Depends on Phase 5; lab optional
- **Phase 7 (Polish)**: Depends on all prior phases

### User Story Dependencies

- **US1 (P1)**: Foundation — all other stories depend on `observe()` being implemented
- **US2 (P2)**: Can be written in parallel with US1 tests; implementation needs T019 complete
- **US3 (P3)**: Tail-read tests written in parallel; implementation relies on cursor logic from T018/T019

### Within Each User Story

```
Test tasks [P] → written first → confirmed FAIL → implementation → confirmed PASS
```

### Contract → Task Mapping

| Contract | Task(s) |
|----------|---------|
| C-001 | T009, T019 |
| C-002 | T010, T019 |
| C-003 | T011, T019 |
| C-004 | T012, T019 |
| C-005 | T013, T019 |
| C-006 | T014, T019 |
| C-007 | T015, T019 |
| C-008 | T025, T019 (cursor) |
| C-009 | T026, T019 (cursor) |
| C-010 | T027, T019 (cursor) |
| C-011 | T016, T019 |
| C-012 | T030, T031 |

---

## Parallel Opportunities

### Phase 1 (Fixtures)

```
T003 empty.json     ─┐
T004 one_alert.json  ├─ all parallel (different files)
T005 two_alerts.json ├─
T006 malformed.json  ├─
T007 stats_only.json ─┘
```

### Phase 3 (US1 tests — write in parallel, then implement sequentially)

```
T009 C-001 test  ─┐
T010 C-002 test  ├─ all parallel (same file, different functions — write sequentially if solo)
T011 C-003 test  ├─
T012 C-004 test  ├─
T013 C-005 test  ├─
T014 C-006 test  ├─
T015 C-007 test  ├─
T016 C-011 test  ─┘
        ↓
T017 (verify red)
        ↓
T018 __init__ ──→ T019 observe() (sequential — T019 depends on T018)
        ↓
T020 (verify green)
```

### Phase 5 (US3 tests — parallel)

```
T025 C-008 test ─┐
T026 C-009 test ├─ parallel
T027 C-010 test ─┘
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 (fixtures) + Phase 2 (stub module)
2. Complete Phase 3 (US1 alert parsing): write 8 tests → red → implement `observe()` → green
3. **STOP and VALIDATE**: `make test` shows 98 passed — MVP done
4. Every subsequent call to `observe()` on a fixture file works

### Incremental Delivery

1. Phase 1 + 2 → fixture files + module stub ready
2. Phase 3 (US1) → `SuricataDefence` can parse alerts → 98 passed
3. Phase 4 (US2) → coverage state assertions pass → 101 passed
4. Phase 5 (US3) → tail-read and truncation proven → 104 passed
5. Phase 6 (C-012 integration) → lab probe wired → 104 passed, 2 skipped
6. Phase 7 → clean lint, commit

---

## Notes

- [P] tasks involve different output files and can run in parallel when working in a team or parallel agent setup
- TDD rule strictly enforced: confirm test FAILS before writing implementation
- `tmp_path` (pytest built-in) is the correct fixture for US3 mutable file tests — no tempfile module
- Integration test (T030/T031) must use exact container names: `aatf-suricata`, `aatf-attacker`, `aatf-defender`
- Eve volume host path: `/var/lib/docker/volumes/aatf-eve/_data/eve.json`
- No new entries needed in `requirements.in` — stdlib only (`json`, `os`, `pathlib`)
- No changes to `src/aatf/contracts.py`, `src/aatf/defence.py`, or any existing test file
- After T035 commit, branch is ready for merge to main and tagging as part of `e3`
