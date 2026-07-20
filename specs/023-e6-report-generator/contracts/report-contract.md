# Contracts: Report Generator (F24)

**Phase**: 1 — Design  
**Date**: 2026-07-11  
**Feature**: 023-e6-report-generator  
**Total contracts**: 10 (C-001..C-010)

Contracts map directly to test cases in `tests/test_report.py`. All contracts use
hand-crafted fixtures; no live lab required.

---

## Shared helpers

```python
FIXED_TS = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)  # deterministic timestamp

def _step(action_id: str, detected: bool) -> StepRecord: ...
def _ep(attacker_class, seed, *steps, total_reward=0.0) -> EpisodeRecord: ...
def _reg(*defs) -> ActionRegistry: ...      # ActionRegistry([*defs])
def _defn(action_id, suricata_category) -> ActionDefinition: ...
```

Tests write the report to `tmp_path / "report.md"` (pytest's `tmp_path` fixture).

---

## US1 — Report generation

### C-001: Importability

**Story**: US1 | **FR**: FR-010

```
GIVEN  the aatf.report module
WHEN   `from aatf.report import generate_report` is executed
THEN   generate_report is callable — no ImportError
```

**Test**: module-level import; `assert callable(generate_report)`.

---

### C-002: Returns string and writes file

**Story**: US1 | **FR**: FR-001, FR-002

```
GIVEN  one episode record with one evaded step and one detected step,
       a stub registry, a valid tmp_path / "report.md" output path
WHEN   generate_report(records, registry, output_path, generated_at=FIXED_TS) is called
THEN   result is a non-empty str
       (tmp_path / "report.md").read_text() == result
```

**Test**: Assert return type, non-empty, and file contents equal return value.

---

### C-003: Determinism

**Story**: US1 | **FR**: FR-003

```
GIVEN  identical records, registry, and generated_at=FIXED_TS
WHEN   generate_report is called twice (to two different tmp files)
THEN   result_a == result_b  (byte-for-byte identical strings)
```

**Test**: Call twice with same args and different tmp paths; assert string equality.

---

### C-004: Empty records — no error

**Story**: US1 | **FR**: FR-008

```
GIVEN  records=[], any registry, a valid output path
WHEN   generate_report([], registry, output_path, generated_at=FIXED_TS) is called
THEN   no exception is raised
       result is a non-empty str
       "0" appears in result (episode count)
```

**Test**: Assert no exception, len(result) > 0, "0" in result.

---

## US2 — Headline metrics

### C-005: Detection rate in report

**Story**: US2 | **FR**: FR-005

```
GIVEN  records = [
         _ep("LinUCB", 0, _step("tcp_port_scan", True),
                          _step("ssh_brute_force", False))
       ]  # 1 detected / 2 total → dr = 0.5
       registry = stub with both action_ids
WHEN   generate_report is called
THEN   "50.0%" in result   (detection rate formatted as "%.1f%%")
```

**Test**: Assert substring "50.0%" in result.

---

### C-006: Mean total_reward in report

**Story**: US2 | **FR**: FR-005

```
GIVEN  records = [
         _ep("LinUCB", 0, _step("ssh_brute_force", False), total_reward=1.0),
         _ep("LinUCB", 1, _step("ssh_brute_force", False), total_reward=-1.0),
       ]  # mean total_reward = 0.0
       registry = stub with ssh_brute_force
WHEN   generate_report is called
THEN   "0.0000" in result  (mean formatted as "%.4f")
```

**Test**: Assert substring "0.0000" in result.

---

## US3 — Blind-spots table

### C-007: Blind-spots ranked correctly

**Story**: US3 | **FR**: FR-006

```
GIVEN  records covering:
         action_a: 3 evaded / 4 total (0.75)
         action_b: 1 evaded / 4 total (0.25)
       registry = stub with both
WHEN   generate_report is called
THEN   result.index("action_a") < result.index("action_b")
       (action_a appears before action_b in the rendered string)
```

**Test**: Assert position of action_a precedes action_b in result string.

---

### C-008: No blind spots — empty-table message

**Story**: US3 | **FR**: FR-006

```
GIVEN  records where every step was detected (no evasions)
       registry = stub with the action_id
WHEN   generate_report is called
THEN   "No blind spots detected" in result  (the {% else %} branch fires)
```

**Test**: Assert substring "No blind spots detected" in result.

---

## US4 — Run metadata and footer

### C-009: Metadata contains attacker class, seeds, episode count

**Story**: US4 | **FR**: FR-004

```
GIVEN  records = [
         _ep("LinUCBAttacker", 42, _step("tcp_port_scan", True)),
         _ep("LinUCBAttacker", 99, _step("tcp_port_scan", True)),
       ]
WHEN   generate_report(records, ..., generated_at=FIXED_TS) is called
THEN   "LinUCBAttacker" in result
       "42" in result
       "99" in result
       "2" in result                # episode count
       "2024-01-01" in result       # from FIXED_TS ISO string
```

**Test**: Assert each substring present in result.

---

### C-010: Error on missing parent directory

**Story**: US4 / FR-009

```
GIVEN  output_path = "/nonexistent_dir_xyz/report.md"
       (parent directory does not exist)
WHEN   generate_report is called
THEN   FileNotFoundError is raised
       (before any rendering or file write)
```

**Test**: `pytest.raises(FileNotFoundError)` wrapping the call.

---

## Contract-to-story mapping

| Contract | Story | FR | Description |
|---|---|---|---|
| C-001 | US1 | FR-010 | Importability |
| C-002 | US1 | FR-001, FR-002 | Returns string + writes file |
| C-003 | US1 | FR-003 | Determinism |
| C-004 | US1 | FR-008 | Empty records safe |
| C-005 | US2 | FR-005 | Detection rate in report |
| C-006 | US2 | FR-005 | Mean total_reward in report |
| C-007 | US3 | FR-006 | Blind-spots ranking |
| C-008 | US3 | FR-006 | No blind spots message |
| C-009 | US4 | FR-004 | Metadata fields |
| C-010 | US4 | FR-009 | Missing parent dir error |
