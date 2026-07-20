# Defence Interface Contract

**Feature**: 007-e3-defence-interface
**File**: `src/aatf/defence.py`
**Contract version**: 1.0

---

## C-001 — observe() returns a valid DetectionResult

Any concrete Defence, when given a valid Action, MUST return a DetectionResult that:
- Has `alerted` set (True or False)
- Has `rule_ids` as a list (empty if `alerted = False`)
- Has `anomaly_score` in [0.0, 1.0]
- Has `coverage` as one of "covered", "uncovered", "unknown"

**Test**: Call `NullDefence().observe(action)` → assert `isinstance(result, DetectionResult)`.

---

## C-002 — NullDefence returns not-detected

`NullDefence.observe(action)` MUST return:
- `alerted = False`
- `rule_ids = []`
- `anomaly_score = 0.0`
- `coverage = "unknown"`

**Test**: Assert each field value on the return.

---

## C-003 — DefenceError is raised on internal failure

A concrete Defence that encounters an internal error MUST raise `DefenceError`, not return a
partial or default result.

**Test**: A `FailingDefence` stub that raises `DefenceError` inside `observe()`; assert the
caller receives `DefenceError`.

---

## C-004 — rule_ids is empty when alerted = False

Constructing a `DetectionResult` with `alerted = False` and non-empty `rule_ids` MUST raise
`ValidationError`.

**Test**: `DetectionResult(alerted=False, rule_ids=["2001219"], anomaly_score=0.0, coverage="covered")`
→ assert `ValidationError` raised.

---

## C-005 — Defence module has no concrete-detector imports

`src/aatf/defence.py` MUST NOT import any concrete detector module (Suricata, ML, host-event).

**Test**: Parse the AST of `defence.py` and assert no import names containing "suricata",
"eve", "auditd", "sklearn", "torch", or "tensorflow".

---

## C-006 — DetectionResult is immutable after construction

A `DetectionResult` returned by any Defence MUST be immutable.

**Test**: Attempt to assign `result.alerted = True` after construction → assert `ValidationError`
or `TypeError` (Pydantic frozen model behaviour from F03).

---

## C-007 — observe() is abstract — Defence cannot be instantiated directly

Attempting to instantiate `Defence()` directly MUST raise `TypeError`.

**Test**: `Defence()` → assert `TypeError`.

---

## C-008 — Unimplemented observe() raises TypeError at class definition

A subclass of `Defence` that does not implement `observe()` MUST raise `TypeError` when
instantiated.

**Test**: Define `class BadDefence(Defence): pass` then `BadDefence()` → assert `TypeError`.

---

## C-009 — NullDefence is safe for repeated calls

Calling `NullDefence().observe(action)` multiple times MUST return equal results with no
side effects.

**Test**: Call observe() 3 times, assert all results are equal.

---

## C-010 — observe() accepts any valid Action

The Defence interface MUST accept any Action that satisfies the F03 Action contract, regardless
of category or parameters.

**Test**: Call `NullDefence().observe()` with Actions of different categories (scan, exfil,
brute) and assert all return valid DetectionResults.

---

## C-011 — conformance helper is importable and reusable

A `check_defence_contract(defence, action)` function in `tests/test_defence.py` MUST be
importable by other test files and MUST assert all structural requirements for any Defence.

**Test**: Import the helper from test_defence; call it with `NullDefence()` — assert it passes
without assertion errors.
