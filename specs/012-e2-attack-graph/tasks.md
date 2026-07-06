# Tasks: Attack Graph Staging (F09)

**Feature**: `012-e2-attack-graph` | **Branch**: `012-e2-attack-graph`
**Input**: Design documents from `specs/012-e2-attack-graph/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/attack-graph-contract.md ✅

**Tests**: TDD — write tests first, verify red, implement, verify green.
**Baseline**: 148 passed, 4 skipped. Target: ≥160 passed, 4 skipped (+12 unit tests).

**Files to create**:
- `src/aatf/attack_graph.py` — `AttackGraph` frozen dataclass, `ATTACK_GRAPH` constant
- `tests/test_attack_graph.py` — 12 unit tests (C-001 to C-012)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Record baseline, create importable stub.

- [ ] T001 Record pytest baseline: run `python -m pytest --tb=no -q` from repo root (with venv activated) → confirm 148 passed, 4 skipped
- [ ] T002 Create `src/aatf/attack_graph.py` stub — empty module with `from __future__ import annotations` and a docstring; verify `python -c "import aatf.attack_graph"` prints nothing and exits 0

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `AttackGraph` class skeleton with `__post_init__` validation — must exist before any test can import it.

**⚠️ CRITICAL**: Complete T003–T005 before any user story phase.

- [ ] T003 Add `AttackGraph` frozen dataclass to `src/aatf/attack_graph.py`: `@dataclass(frozen=True)` decorator, two fields — `entry_points: frozenset[str]` and `edges: dict[str, frozenset[str]]`; imports: `from __future__ import annotations`, `from collections.abc import Callable`, `from dataclasses import dataclass`
- [ ] T004 Add `AttackGraph.__post_init__` validation to `src/aatf/attack_graph.py`: import `REGISTRY` from `aatf.action_library`; collect all action_ids referenced (entry_points + all values in edges); for each unknown id raise `ValueError(f"unknown action_id in attack graph: {id!r}")`; also verify every REGISTRY action_id appears in entry_points or in at least one frozenset in edges.values(), raising `ValueError` if not
- [ ] T005 Add `AttackGraph.available_actions(self, completed: set[str]) -> list[str]` to `src/aatf/attack_graph.py`: `return sorted(self.entry_points | {s for aid in completed for s in self.edges.get(aid, frozenset())})`
- [ ] T006 Add `ATTACK_GRAPH` module-level constant to `src/aatf/attack_graph.py` with the canonical v1 topology: `entry_points=frozenset({"tcp_port_scan", "udp_sweep", "icmp_ping_sweep", "dns_subdomain_enum"})`, `edges={"tcp_port_scan": frozenset({"ssh_brute_force", "ftp_brute_force", "http_dir_scan", "ssh_user_enum"}), "udp_sweep": frozenset({"dns_zone_transfer"}), "icmp_ping_sweep": frozenset({"ssh_version_probe"}), "dns_subdomain_enum": frozenset({"dns_zone_transfer"}), "ssh_brute_force": frozenset({"ssh_version_probe"}), "http_dir_scan": frozenset({"http_sqli_probe", "http_xss_probe", "http_basic_brute"}), "http_sqli_probe": frozenset({"http_exfil"}), "dns_zone_transfer": frozenset({"dns_exfil"})}`
- [ ] T007 Verify import: `python -c "from aatf.attack_graph import ATTACK_GRAPH, AttackGraph; print('OK')"` → must print `OK`

**Checkpoint**: Foundation ready — `AttackGraph` importable, `ATTACK_GRAPH` constructed and validated.

---

## Phase 3: User Story 1 — Entry-Point Actions Always Available (Priority: P1) 🎯 MVP

**Goal**: `available_actions(set())` returns exactly the 4 entry-point action_ids; `ATTACK_GRAPH` accessible as module-level constant.

**Independent Test**: `pytest tests/test_attack_graph.py -k "entry or constant or sorted"` — 4 tests pass.

### Tests for US1 ⚠️

> **Write all tests below, run pytest, verify they PASS (implementation already in place from Phase 2).**

- [ ] T008 [US1] Write `test_empty_completed_returns_entry_points` in `tests/test_attack_graph.py` — C-001: `assert set(ATTACK_GRAPH.available_actions(set())) == {"tcp_port_scan", "udp_sweep", "icmp_ping_sweep", "dns_subdomain_enum"}`
- [ ] T009 [US1] Write `test_empty_completed_returns_only_entry_points` in `tests/test_attack_graph.py` — C-002: `result = ATTACK_GRAPH.available_actions(set())`; assert no id in result that is not one of the 4 entry-points (e.g. `"ssh_brute_force" not in result`)
- [ ] T010 [US1] Write `test_available_actions_is_sorted` in `tests/test_attack_graph.py` — C-011: `result = ATTACK_GRAPH.available_actions(set())`; `assert result == sorted(result)`
- [ ] T011 [US1] Write `test_attack_graph_is_module_level_constant` in `tests/test_attack_graph.py` — C-012: `from aatf.attack_graph import ATTACK_GRAPH, AttackGraph`; `assert isinstance(ATTACK_GRAPH, AttackGraph)`
- [ ] T012 [US1] Run `python -m pytest tests/test_attack_graph.py -v` — confirm T008–T011 (4 tests) PASS

**Checkpoint**: Entry-point baseline verified.

---

## Phase 4: User Story 2 — Completing Actions Unlocks Successors (Priority: P2)

**Goal**: Each completed action_id unlocks its direct successors; unknown ids silently ignored; result is non-destructive.

**Independent Test**: `pytest tests/test_attack_graph.py -k "unlock or successor or ignore or idempotent"` — 6 tests pass.

### Tests for US2 ⚠️

- [ ] T013 [US2] Write `test_tcp_port_scan_unlocks_successors` in `tests/test_attack_graph.py` — C-003: `result = ATTACK_GRAPH.available_actions({"tcp_port_scan"})`; assert all of `{"ssh_brute_force", "ftp_brute_force", "http_dir_scan", "ssh_user_enum"}` are in `result`
- [ ] T014 [US2] Write `test_dns_subdomain_enum_unlocks_dns_zone_transfer` in `tests/test_attack_graph.py` — C-004: `assert "dns_zone_transfer" in ATTACK_GRAPH.available_actions({"dns_subdomain_enum"})`
- [ ] T015 [US2] Write `test_http_sqli_probe_unlocks_http_exfil` in `tests/test_attack_graph.py` — C-005: `assert "http_exfil" in ATTACK_GRAPH.available_actions({"http_sqli_probe"})`
- [ ] T016 [US2] Write `test_dns_zone_transfer_unlocks_dns_exfil` in `tests/test_attack_graph.py` — C-006: `assert "dns_exfil" in ATTACK_GRAPH.available_actions({"dns_zone_transfer"})`
- [ ] T017 [US2] Write `test_unknown_completed_id_ignored` in `tests/test_attack_graph.py` — C-008: `result_unknown = ATTACK_GRAPH.available_actions({"nonexistent_xyz"})`; `result_empty = ATTACK_GRAPH.available_actions(set())`; `assert result_unknown == result_empty` (no exception raised)
- [ ] T018 [US2] Write `test_available_actions_is_non_destructive` in `tests/test_attack_graph.py` — C-010: call `ATTACK_GRAPH.available_actions({"tcp_port_scan"})` twice; assert both calls return identical lists
- [ ] T019 [US2] Run `python -m pytest tests/test_attack_graph.py -v` — confirm T013–T018 (6 new tests) PASS

**Checkpoint**: Unlock semantics verified. Entry-points + unlocks both green.

---

## Phase 5: User Story 3 — Full Graph Coverage (Priority: P3)

**Goal**: All 15 action_ids returned when all 15 completed; no unknown action_ids in graph.

**Independent Test**: `pytest tests/test_attack_graph.py -k "coverage or validation or all_15"` — 2 tests pass.

### Tests for US3 ⚠️

- [ ] T020 [US3] Write `test_all_15_actions_available_when_all_completed` in `tests/test_attack_graph.py` — C-007: `from aatf.action_library import REGISTRY`; `all_ids = {d.action_id for d in REGISTRY.list_actions()}`; `assert set(ATTACK_GRAPH.available_actions(all_ids)) == all_ids`
- [ ] T021 [US3] Write `test_invalid_action_id_raises_at_construction` in `tests/test_attack_graph.py` — C-009: `with pytest.raises(ValueError, match="unknown action_id"): AttackGraph(entry_points=frozenset({"nonexistent_id"}), edges={})`
- [ ] T022 [US3] Run `python -m pytest tests/test_attack_graph.py -v` — confirm T020–T021 (2 new tests) PASS

**Checkpoint**: All 12 tests green. All 3 user stories verified.

---

## Phase 6: Polish

**Purpose**: Lint, format, final count, commit.

- [ ] T023 Run `ruff check src/aatf/attack_graph.py tests/test_attack_graph.py` — fix any issues (UP035: use `collections.abc` instead of `typing`; F401: remove unused imports; E501: wrap long lines)
- [ ] T024 Run `ruff format src/aatf/attack_graph.py tests/test_attack_graph.py` — apply formatting
- [ ] T025 Run full test suite `python -m pytest --tb=short -q` — confirm ≥160 passed, 4 skipped
- [ ] T026 Commit: `git add src/aatf/attack_graph.py tests/test_attack_graph.py && git commit -m "feat(F09): add AttackGraph with v1 topology, ATTACK_GRAPH constant, import-time validation"`

---

## Dependencies & Execution Order

- **Phase 1 (Setup)**: Start immediately
- **Phase 2 (Foundational)**: After Phase 1 — BLOCKS all user stories
- **Phase 3–5 (US1–US3)**: After Phase 2 — sequential (US2 needs US1 test file; US3 needs US2)
- **Phase 6 (Polish)**: After all user story phases complete

---

## Notes

- The implementation (Phase 2) is written BEFORE the tests (Phases 3–5) because `AttackGraph.__post_init__` raises at import time if the topology is wrong — tests can only import after the module is valid
- C-009 test requires `pytest.raises(ValueError)` — import `pytest` in test file
- C-010 non-destructive test: `frozen=True` guarantees this structurally, but the test verifies the contract explicitly
- After T026 commit, merge `012-e2-attack-graph` to `main`, tag `e2`, create PHR
