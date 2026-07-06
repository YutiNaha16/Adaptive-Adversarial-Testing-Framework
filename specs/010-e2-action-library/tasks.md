# Tasks: Defanged Action Library (F07)

**Input**: Design documents from `specs/010-e2-action-library/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅

**Files to create**:
- `src/aatf/action_library.py` — ActionDefinition, ActionRegistry, SafetyViolation, REGISTRY, safety_guard()
- `tests/test_action_library.py` — 15 unit tests (C-001–C-015), pure in-memory

**Baseline**: 119 passed, 3 skipped. Target: gain ≥15 new passing tests.

---

## Phase 1: Setup

**Purpose**: Record baseline and create stub file so tests can import.

- [ ] T001 Record pytest baseline by running `pytest tests/ -q` from repo root and noting count (expected: 119 passed, 3 skipped)
- [ ] T002 Create stub `src/aatf/action_library.py` with empty `ActionDefinition` dataclass, empty `ActionRegistry` class, empty `SafetyViolation` dataclass, a `REGISTRY` constant set to an empty `ActionRegistry`, and `safety_guard()` returning `[]`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Wire up all imports so test file can be created and run.

- [ ] T003 Verify `from aatf.action_library import REGISTRY, safety_guard, ActionDefinition, ActionRegistry, SafetyViolation` succeeds in a Python REPL (no ImportError); verify `from aatf.contracts import Action` is also importable

**Checkpoint**: Imports work — test file can now be written.

---

## Phase 3: User Story 1 — Action Registry (Priority: P1) 🎯 MVP

**Goal**: A queryable registry of ≥15 actions, unique IDs, all 6 categories covered, round-trip lookups.

**Independent Test**: `pytest tests/test_action_library.py -k "registry"` — all registry tests pass.

**Contracts covered**: C-001, C-002, C-003, C-004, C-013, C-014

### Tests for User Story 1 (TDD — write first, verify RED, then implement)

- [ ] T004 [US1] Write `test_registry_has_at_least_15_actions` in `tests/test_action_library.py` — asserts `len(REGISTRY.list_actions()) >= 15` (C-001); run pytest, confirm FAIL
- [ ] T005 [US1] Write `test_all_action_ids_are_unique` in `tests/test_action_library.py` — asserts `len({a.action_id for a in REGISTRY.list_actions()}) == len(REGISTRY.list_actions())` (C-002); confirm FAIL
- [ ] T006 [US1] Write `test_all_six_categories_present` in `tests/test_action_library.py` — asserts `REGISTRY.actions_by_category(cat)` is non-empty for each of `scan`, `brute`, `ssh`, `web`, `dns`, `exfil` (C-003); confirm FAIL
- [ ] T007 [US1] Write `test_get_action_round_trips` in `tests/test_action_library.py` — for every action in `REGISTRY.list_actions()`, asserts `REGISTRY.get_action(a.action_id) == a` (C-004); confirm FAIL
- [ ] T008 [US1] Write `test_get_action_raises_key_error_on_unknown_id` in `tests/test_action_library.py` — asserts `pytest.raises(KeyError)` when calling `REGISTRY.get_action("nonexistent_id")` (C-013); confirm FAIL
- [ ] T009 [US1] Write `test_actions_by_category_unknown_returns_empty_list` in `tests/test_action_library.py` — asserts `REGISTRY.actions_by_category("nonexistent_cat") == []` (C-014); confirm FAIL
- [ ] T010 [US1] Run `pytest tests/test_action_library.py` — confirm all 6 US1 tests FAIL (red phase verified)

### Implementation for User Story 1

- [ ] T011 [US1] Implement `ActionDefinition` as a `@dataclass(frozen=True)` in `src/aatf/action_library.py` with fields: `action_id: str`, `category: str`, `description: str`, `default_parameters: dict`, `suricata_category: str`; add `to_action(self, timestamp) -> Action` method that returns `Action(action_id=self.action_id, category=self.category, parameters=self.default_parameters, timestamp=timestamp)`
- [ ] T012 [US1] Implement `ActionRegistry` in `src/aatf/action_library.py` with `__init__(self, definitions: list[ActionDefinition])` that builds `_store: dict[str, ActionDefinition]` and raises `ValueError` on duplicate `action_id`; add `list_actions()`, `get_action(action_id)` (raises `KeyError` if missing), `actions_by_category(category)` (returns `[]` for unknown)
- [ ] T013 [US1] Add 15 `ActionDefinition` instances to `src/aatf/action_library.py` covering all 6 categories — scan: `tcp_port_scan`, `udp_sweep`, `icmp_ping_sweep`; brute: `ssh_brute_force`, `ftp_brute_force`, `http_basic_brute`; ssh: `ssh_user_enum`, `ssh_version_probe`; web: `http_dir_scan`, `http_sqli_probe`, `http_xss_probe`; dns: `dns_zone_transfer`, `dns_subdomain_enum`; exfil: `dns_exfil`, `http_exfil` — all `target_ip` defaults set to `"172.28.0.2"`; wire up `REGISTRY = ActionRegistry([...all 15...])` at module level
- [ ] T014 [US1] Run `pytest tests/test_action_library.py -k "registry or unique or categories or round_trip or key_error or unknown"` — confirm all 6 US1 tests PASS (green)

**Checkpoint**: US1 complete — registry functional, ≥15 actions, all 6 categories, round-trip lookups verified.

---

## Phase 4: User Story 2 — Parameterised Behaviour Descriptions (Priority: P2)

**Goal**: Every action has non-empty parameters, non-empty description, non-empty suricata_category, and `to_action()` produces a valid F03 `Action`.

**Independent Test**: `pytest tests/test_action_library.py -k "param or description or suricata or to_action"` — all US2 tests pass.

**Contracts covered**: C-005, C-006, C-007, C-008, C-009

### Tests for User Story 2 (TDD — write first, verify RED, then implement)

- [ ] T015 [US2] Write `test_all_actions_have_non_empty_parameters` in `tests/test_action_library.py` — for every action in `REGISTRY.list_actions()`, asserts `a.default_parameters != {}` (C-005); run pytest, confirm FAIL (or immediate PASS if T013 already set parameters — confirm state)
- [ ] T016 [US2] Write `test_all_actions_have_non_empty_description` in `tests/test_action_library.py` — asserts `a.description.strip() != ""` for every action (C-006); confirm FAIL or PASS
- [ ] T017 [US2] Write `test_all_actions_have_suricata_category` in `tests/test_action_library.py` — asserts `a.suricata_category.strip() != ""` for every action (C-007); confirm FAIL or PASS
- [ ] T018 [US2] Write `test_to_action_produces_valid_action` in `tests/test_action_library.py` — for the first action in `REGISTRY.list_actions()`, calls `a.to_action(datetime.now(UTC))`, then `Action.model_validate(action.model_dump())` — asserts no ValidationError (C-008); confirm FAIL
- [ ] T019 [US2] Write `test_to_action_preserves_fields` in `tests/test_action_library.py` — asserts `action.action_id == a.action_id`, `action.category == a.category`, `action.parameters == a.default_parameters` (C-009); confirm FAIL
- [ ] T020 [US2] Run `pytest tests/test_action_library.py` — confirm all 5 US2 tests FAIL or note which pass due to T013 already providing data

### Implementation for User Story 2

- [ ] T021 [US2] Verify each of the 15 `ActionDefinition` instances in `src/aatf/action_library.py` has: a non-empty `default_parameters` dict with at least one tunable (e.g. `rate_pps`, `attempts`, `interval_ms`), a non-empty `description` string stating behaviour and rule family, a non-empty `suricata_category` string (e.g. `"ET SCAN"`, `"ET BRUTE_FORCE"`) — fix any that are missing
- [ ] T022 [US2] Run `pytest tests/test_action_library.py` — confirm all 11 tests (US1 + US2) PASS

**Checkpoint**: US2 complete — all actions fully described with tunables and Suricata mappings; `to_action()` produces valid F03 Actions.

---

## Phase 5: User Story 3 — Safety Guard (Priority: P3)

**Goal**: `safety_guard()` detects external IPs and empty parameters; library itself passes the guard; no I/O at import.

**Independent Test**: `pytest tests/test_action_library.py -k "safety or guard or io"` — all US3 tests pass.

**Contracts covered**: C-010, C-011, C-012, C-015

### Tests for User Story 3 (TDD — write first, verify RED, then implement)

- [ ] T023 [US3] Write `test_safety_guard_clean_on_registered_library` in `tests/test_action_library.py` — asserts `safety_guard(REGISTRY) == []` (C-010); run pytest, confirm FAIL
- [ ] T024 [US3] Write `test_safety_guard_flags_external_ip` in `tests/test_action_library.py` — constructs a one-action `ActionRegistry` with `ActionDefinition(action_id="bad", category="scan", description="x", default_parameters={"target": "8.8.8.8"}, suricata_category="ET SCAN")`; asserts `len(safety_guard(bad_registry)) >= 1` (C-011); confirm FAIL
- [ ] T025 [US3] Write `test_safety_guard_flags_empty_parameters` in `tests/test_action_library.py` — constructs an `ActionDefinition` with `default_parameters={}` in a one-action registry; asserts `len(safety_guard(empty_registry)) >= 1` (C-012); confirm FAIL
- [ ] T026 [US3] Write `test_no_io_at_import` in `tests/test_action_library.py` — monkeypatches `socket.socket` and `subprocess.Popen` to raise `AssertionError("IO attempted at import")`; imports `importlib.reload(aatf.action_library)`; asserts no error raised (C-015); confirm FAIL
- [ ] T027 [US3] Run `pytest tests/test_action_library.py -k "safety or guard or io"` — confirm all 4 US3 tests FAIL (red phase verified)

### Implementation for User Story 3

- [ ] T028 [US3] Implement `SafetyViolation` as a `@dataclass` in `src/aatf/action_library.py` with fields: `action_id: str`, `field: str`, `reason: str`
- [ ] T029 [US3] Implement `safety_guard(registry: ActionRegistry) -> list[SafetyViolation]` in `src/aatf/action_library.py` — iterates `registry.list_actions()`; for each action: (1) flags empty `default_parameters` as a violation; (2) for each string value in `default_parameters.values()`, attempts `ipaddress.ip_address(value)` and flags if the address is global (not private/link-local/loopback) using `addr.is_global`; returns collected violations
- [ ] T030 [US3] Run `pytest tests/test_action_library.py` — confirm all 15 tests PASS

**Checkpoint**: US3 complete — safety guard operational, all 15 contracts green.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Lint, final count verification, commit.

- [ ] T031 Run `ruff check src/aatf/action_library.py tests/test_action_library.py --fix` and resolve any remaining lint errors
- [ ] T032 Run `pytest tests/ -q` from repo root — confirm ≥134 passed (119 baseline + 15 new), 3 skipped; record final count
- [ ] T033 Stage and commit: `git add src/aatf/action_library.py tests/test_action_library.py` with message `feat(e2): F07 defanged action library — 15 actions, ActionRegistry, safety_guard, 15 contracts`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (stub file must exist)
- **US1 (Phase 3)**: Depends on Phase 2 — BLOCKS US2 and US3 (ActionDefinition and ActionRegistry must exist)
- **US2 (Phase 4)**: Depends on US1 (needs populated REGISTRY with 15 actions)
- **US3 (Phase 5)**: Depends on US1 (needs ActionRegistry for safety_guard parameter); independent of US2
- **Polish (Phase 6)**: Depends on all US phases complete

### Within Each User Story

- Tests MUST be written and FAIL before implementation tasks
- T011 (ActionDefinition) before T012 (ActionRegistry) before T013 (15 instances)
- T028 (SafetyViolation) before T029 (safety_guard implementation)

### Parallel Opportunities

- T015–T019 (US2 tests) can all be written in parallel — different test functions, same file
- T023–T026 (US3 tests) can all be written in parallel
- T021 (verify descriptions) and T028 (SafetyViolation dataclass) can run in parallel

---

## Parallel Example: User Story 1 Tests

```bash
# Write all 6 US1 tests in one pass (same file, sequential functions):
T004: test_registry_has_at_least_15_actions
T005: test_all_action_ids_are_unique
T006: test_all_six_categories_present
T007: test_get_action_round_trips
T008: test_get_action_raises_key_error_on_unknown_id
T009: test_actions_by_category_unknown_returns_empty_list
# Then run once to confirm all 6 FAIL → T010
```

---

## Implementation Strategy

### MVP First (US1 only — registry functional)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003)
3. Complete Phase 3: US1 (T004–T014)
4. **STOP and VALIDATE**: `pytest tests/test_action_library.py -k "registry"` — all pass

### Incremental Delivery

1. Setup + Foundational → stub importable
2. US1 → registry with 15 actions, all 6 categories, lookups work
3. US2 → all actions fully described, `to_action()` round-trips
4. US3 → safety guard operational, full clean pass

---

## Notes

- All tests are pure in-memory — no Docker, no fixture files, no external network calls
- `SafetyViolation` dataclass does NOT need `frozen=True` (it is output-only, not stored in registry)
- `ActionDefinition` MUST be `frozen=True` so instances are hashable and equality-comparable
- The `ipaddress.ip_address()` call in safety_guard must be wrapped in `try/except ValueError` — non-IP strings are silently skipped
- `172.28.0.2` is `is_private=True` in Python's ipaddress module — it will NOT be flagged by the guard
