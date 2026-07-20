# Research: Pluggable Defence Interface (F10)

## Decision 1 — ABC vs Protocol for the Defence interface

**Decision**: Use `abc.ABC` + `@abstractmethod`.

**Rationale**:
- `abc.ABC` raises `TypeError` at class-definition time if the abstract method is not
  implemented — errors appear early, not at call time.
- Explicit inheritance signals intent: a class that subclasses `Defence` *means* to be a
  Defence, not merely happens to have an `observe` method.
- IDE tooling (jump-to-definition, find-all-implementations) works reliably with ABC.
- The existing codebase uses Pydantic `BaseModel` (class-based OOP); ABC is consistent.

**Alternatives considered**:
- `typing.Protocol` — structural subtyping (duck typing). Rejected because any class that
  happens to have an `observe(action)` method would satisfy it accidentally, making
  unintentional implementations invisible until runtime.

---

## Decision 2 — Where to enforce `rule_ids non-empty ↔ alerted = True`

**Decision**: Add a Pydantic `@model_validator(mode='after')` to `DetectionResult` in
`src/aatf/contracts.py`.

**Rationale**:
- The invariant belongs on the data shape, not on individual Defence implementations — if it
  lives on the interface it must be re-checked by every future concrete class.
- Pydantic validators run at construction time and raise `ValidationError` with a clear
  message; this is consistent with how the other contracts already enforce constraints
  (anomaly_score bounds, etc.).
- This is an additive, non-breaking tightening of F03 — existing valid data still passes;
  only previously-invalid combinations (rule_ids populated without alert) are now rejected.

**Alternatives considered**:
- Enforce in `Defence.observe()` base method — rejected because it would require a concrete
  `observe()` body in the ABC, defeating the "single abstract method" design.
- Leave unenforced / document only — rejected per Principle IV (contract tests must lock the
  contract, not just document it).

---

## Decision 3 — NullDefence location

**Decision**: `NullDefence` lives in `src/aatf/defence.py` alongside the interface.

**Rationale**:
- It is the canonical test double for the interface; shipping it with the interface means
  every future test file gets a free, standard stub with one import.
- It has zero logic — it cannot drift or need updating as the interface evolves.
- Keeping it in `tests/` would force duplication across test files for F11, F12, F15, etc.

**Alternatives considered**:
- Separate `src/aatf/stubs.py` — over-engineering; there is only one stub at this stage.
- In `tests/conftest.py` — pytest-scoped, not importable from other src modules if needed.

---

## Decision 4 — Conformance test helper design

**Decision**: A module-level function `check_defence_contract(defence: Defence, action: Action)`
in `tests/test_defence.py` that asserts structural and behavioural correctness.

**Rationale**:
- Makes conformance testing trivially reusable: F11 (Suricata adapter) and F12 (host log
  adapter) import and call this function in their own tests.
- Centralises the "what counts as a valid Defence" logic; if the contract tightens, one edit
  propagates everywhere.

**No alternatives considered** — this pattern is standard for interface contract testing.

---

## No NEEDS CLARIFICATION items

All technical decisions above are resolved. No new pip dependencies required:
- `abc` — Python standard library
- `pydantic` — already pinned in requirements.txt
