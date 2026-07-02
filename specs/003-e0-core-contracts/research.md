# Research: Core Data Contracts

**Feature**: 003-e0-core-contracts | **Date**: 2026-07-02

No external unknowns — all technology is already in use from F01/F02. This document records
the eight design decisions made during planning.

---

## D1 — Pydantic V2 `Annotated` for bounded list elements

**Decision**: Use `list[Annotated[float, Field(ge=0.0, le=1.0)]]` for `alert_history`.

**Rationale**: Pydantic V2 validates `Annotated` constraints inside list elements
automatically. This is the standard Pydantic V2 idiom and requires no custom validator.

**Alternatives considered**:
- `list[float]` with `@field_validator` — more code, same effect.
- `list[int]` constrained to {0, 1} — too rigid; Phase 2 needs intermediate float scores.

---

## D2 — `Annotated` dict values for `technique_detection_rates`

**Decision**: Use `dict[str, Annotated[float, Field(ge=0.0, le=1.0)]]`.

**Rationale**: Pydantic V2 validates `Annotated` constraints on dict values. Keeps
validation in the schema, not in the caller. Consistent with D1 (same pattern).

**Alternatives considered**:
- `dict[str, float]` with doc-only constraint — caller can silently pass bad values.
- `@model_validator` post-init — works but more code and less readable.

---

## D3 — `Literal["covered", "uncovered", "unknown"]` for `DetectionResult.coverage`

**Decision**: Use `Literal` type, not a `StrEnum`.

**Rationale**: Three values that won't grow. Pydantic V2 validates `Literal` directly —
no Enum class needed. Cleaner import surface for downstream consumers.

**Alternatives considered**:
- `StrEnum` — adds a class, requires callers to import it; unnecessary at this scale.
- `str` unconstrained — loses all schema-level validation.

---

## D4 — UTC-aware `datetime` for all timestamp fields

**Decision**: All `datetime` fields are `datetime` with no default; callers pass
`datetime.now(UTC)`. `model_dump(mode="json")` serialises them as ISO 8601 strings;
`model_validate` reconstructs them as timezone-aware `datetime` objects.

**Rationale**: Consistent with F02 manifest timestamps. Pydantic V2 handles the
datetime↔ISO-string round-trip automatically when `mode="json"` is used.

**Alternatives considered**:
- Store as Unix timestamp (float) — less readable in JSONL output.
- Store as plain string — loses type information; no validation.

---

## D5 — `ConfigDict(frozen=True)` on all five types

**Decision**: All five types are frozen (immutable after construction).

**Rationale**: Contract objects represent a snapshot of state at a point in time; they
must never be mutated after creation. Frozen models also have stable hashes, enabling
use as dict keys if needed. Consistent with F02's `ExperimentConfig`.

**Alternatives considered**:
- Mutable models — risk of accidental mutation in the feedback loop silently corrupting
  episode records before they are logged.

---

## D6 — JSONL round-trip via `model_dump(mode="json")` + `model_validate()`

**Decision**: `EpisodeRecord.model_dump(mode="json")` → `json.dumps()` → write line;
read line → `json.loads()` → `EpisodeRecord.model_validate(data)`.

**Rationale**: `mode="json"` forces Pydantic to serialise all non-JSON-native types
(datetime → ISO string, Path → str). `model_validate` accepts the dict and reconstructs
the full typed object. This is the idiomatic Pydantic V2 round-trip pattern.

**Alternatives considered**:
- `model_dump_json()` / `model_validate_json()` — also valid; slightly more convenient
  but less explicit about the dict intermediate step needed for JSONL.

---

## D7 — `current_stage: int` validated in [0, 3] on `ContextVector`

**Decision**: Add explicit `current_stage: int = Field(ge=0, le=3)` field.

**Rationale**: The attack graph has 4 discrete stages. Inferring stage from
`attack_progress` (a continuous float) would be fragile and require the attacker brain
to perform `int(progress * 4)` — which breaks at progress=1.0 (returns 4, out of range).
Explicit int is unambiguous and directly usable for legal-action lookup.

**Alternatives considered**:
- Infer from `attack_progress` — fragile; breaks at boundary values.
- `StageEnum` IntEnum — adds a new exported type; the raw int suffices at this stage;
  F13 (context vector builder) can introduce named constants if needed.

---

## D8 — Single flat `src/aatf/contracts.py`, not a sub-package

**Decision**: All five types in one file.

**Rationale**: ~120–150 lines with five types is well within a readable single-file
threshold. A `contracts/` sub-package with five individual files would require an
`__init__.py` exporting everything, adding indirection with no benefit.

**Alternatives considered**:
- Sub-package with one file per type — useful if types grew to 50+ lines each, or if
  types had conflicting imports; neither applies here.
