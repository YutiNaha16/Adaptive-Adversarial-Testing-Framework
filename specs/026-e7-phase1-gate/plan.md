# Implementation Plan: Automated Phase 1 Gate Evaluation (F26)

**Branch**: `026-e7-phase1-gate` | **Date**: 2026-07-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/026-e7-phase1-gate/spec.md`

## Summary

Implement `aatf.gate` module (`src/aatf/gate.py`) with `phase1_gate()`, `GateResult`, and
`CriterionResult`. Integrate the gate call into `src/run_experiment.py` (stdout + manifest).
Extend `write_manifest()` with `extra_metadata` to carry the gate result. 10 TDD contracts.
No new pip dependencies.

---

## Technical Context

**Language/Version**: Python 3.12 (pinned per F01)
**Primary Dependencies**: stdlib only — `dataclasses`, `typing`; existing: `aatf.metrics`
(F20), `aatf.ground_truth` (F22), `aatf.manifest` (F02), `src/run_experiment.py` (F25)
**Storage**: no file I/O in `gate.py`; manifest extended via `extra_metadata` kwarg
**Testing**: pytest; `pytest tests/test_gate.py`
**Target Platform**: Linux (same host as all other aatf modules)
**Project Type**: Single Python package under `src/`
**Performance Goals**: gate completes in <10ms (pure in-memory arithmetic)
**Constraints**: Constitution Principles II (determinism), IV (scientific validity), VI (observability)
**Scale/Scope**: one call per experiment run; 3 criteria, always O(N episodes)

---

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| I. Safety & Isolation | ✅ PASS | Pure function — no network, no file I/O, no external dependencies |
| II. Reproducibility & Determinism | ✅ PASS | Gate is purely deterministic: same inputs → same GateResult |
| III. Pluggable Defence Interface | ✅ N/A | Gate consumes metrics only; does not touch the Defence interface |
| IV. Scientific Validity / TDD | ✅ PASS | 10 contracts written first; gate verifies the 3 Phase 1 criteria |
| V. Explainability | ✅ N/A | Gate consumes ValidationResult (BSP) from F22 — does not produce explanations |
| VI. Observability | ✅ PASS | Gate result printed to stdout and included in run manifest |
| VII. Phased Delivery | ✅ PASS | F26 is the final E7 feature; completes Phase 1 gate machinery |

**Post-design re-check**: All principles hold.

---

## API Verification (from actual source)

Verified against actual files before writing plan:

| Symbol | Module | Signature |
|---|---|---|
| `EpisodeRecord` | `aatf.metrics` | `@dataclass(frozen=True)` with `steps, total_reward, completed, episode_index, attacker_class, seed` |
| `detection_rate` | `aatf.metrics` | `(records: list[EpisodeRecord]) -> float` — returns 0.0 for empty list |
| `robustness_score` | `aatf.metrics` | `(records: list[EpisodeRecord], window: int) -> float` — returns 0.0 if window ≤ 0 |
| `ValidationResult` | `aatf.ground_truth` | `@dataclass(frozen=True)` with `blind_spot_precision: float` |
| `validate_blind_spots` | `aatf.ground_truth` | `(explanations: list[ActionExplanation], disabled_sids: set[str]) -> ValidationResult` |
| `write_manifest` | `aatf.manifest` | `(config, seed, *, suricata_version, ruleset_version) -> Path` |

**Key decision**: `robustness_score([], window=min(10, 0)) = robustness_score([], 0) = 0.0`
because `window <= 0` path returns 0.0. So for empty records, RS value = 0.0.

**Key decision**: `detection_rate([])` = 0.0 (total steps = 0, returns 0.0 early).

**Empty-records gate logic**:
- DR: value=0.0, passed=(0.0 >= 0.0 AND len([]) > 0) = False (len check fails)
- BSP: value=validation_result.blind_spot_precision, passed=(value >= 0.8)
- RS: value=0.0, passed=(len([]) > 0) = False

---

## Project Structure

### Source Code

```text
src/aatf/
└── gate.py              # ~50 LOC (NEW) — GateResult, CriterionResult, phase1_gate()
src/
└── run_experiment.py    # +15 LOC (MODIFIED) — gate call, stdout, manifest integration
src/aatf/
└── manifest.py          # +4 LOC (MODIFIED) — add extra_metadata kwarg

tests/
└── test_gate.py         # ~120 LOC, 10 tests (NEW)
```

---

## Implementation Sketch

### src/aatf/gate.py (~50 LOC)

```python
"""Phase 1 gate evaluator — pure function, no I/O."""
from __future__ import annotations
from dataclasses import dataclass
from aatf.ground_truth import ValidationResult
from aatf.metrics import EpisodeRecord, detection_rate, robustness_score


@dataclass(frozen=True)
class CriterionResult:
    name: str
    passed: bool
    value: float
    threshold: float


@dataclass(frozen=True)
class GateResult:
    passed: bool
    criteria: tuple[CriterionResult, ...]
    summary: str


def phase1_gate(
    records: list[EpisodeRecord],
    validation_result: ValidationResult,
) -> GateResult:
    n = len(records)
    dr_value = detection_rate(records)
    rs_value = robustness_score(records, window=min(10, n)) if n > 0 else 0.0

    criteria = (
        CriterionResult(
            name="detection_rate",
            threshold=0.0,
            value=dr_value,
            passed=n > 0,  # DR ≥ 0.0 AND at least one episode
        ),
        CriterionResult(
            name="blind_spot_precision",
            threshold=0.8,
            value=validation_result.blind_spot_precision,
            passed=validation_result.blind_spot_precision >= 0.8,
        ),
        CriterionResult(
            name="robustness_score",
            threshold=0.0,
            value=rs_value,
            passed=n > 0,  # RS ≥ 0.0 AND at least one episode
        ),
    )

    passed = all(c.passed for c in criteria)
    met = sum(c.passed for c in criteria)
    total = len(criteria)

    if passed:
        summary = f"Phase 1 PASSED ({met}/{total} criteria met)"
    else:
        failing = ", ".join(c.name for c in criteria if not c.passed)
        summary = f"Phase 1 FAILED ({met}/{total} criteria met: {failing} below threshold)"

    return GateResult(passed=passed, criteria=criteria, summary=summary)
```

### src/aatf/manifest.py — add extra_metadata kwarg

```python
def write_manifest(
    config: ExperimentConfig,
    seed: int,
    *,
    suricata_version: str = "unknown",
    ruleset_version: str = "unknown",
    extra_metadata: dict | None = None,   # NEW
) -> Path:
    ...
    manifest = { ... }
    if extra_metadata:
        manifest.update(extra_metadata)   # NEW
    ...
```

### src/run_experiment.py — gate integration (~+15 LOC)

After `records` list is built, before printing summary:
```python
from aatf.gate import phase1_gate
from aatf.ground_truth import ValidationResult

# Default: no explanations available in F25 pipeline; BSP = 0.0
validation_result = ValidationResult(
    blind_spot_precision=0.0,
    true_positives=0,
    false_positives=0,
    total_reported=0,
    disabled_sid_count=0,
)
gate_result = phase1_gate(records, validation_result)

# Print gate result block
print("-" * 38)
for c in gate_result.criteria:
    status = "PASS" if c.passed else "FAIL"
    print(f"  {c.name:<22}: {c.value:.4f} (≥{c.threshold:.4f}) [{status}]")
print(gate_result.summary)

# Include in manifest
manifest_path = write_manifest(
    config, config.seed,
    extra_metadata={
        "phase1_gate": {
            "passed": gate_result.passed,
            "summary": gate_result.summary,
            "criteria": [
                {"name": c.name, "passed": c.passed, "value": c.value, "threshold": c.threshold}
                for c in gate_result.criteria
            ],
        }
    },
)
```

---

## Research Decisions

| Decision | Choice | Rationale |
|---|---|---|
| `criteria` field type | `tuple[CriterionResult, ...]` | Frozen dataclass; tuple is truly immutable; list would allow mutation despite frozen |
| Empty records handling | `passed = n > 0` for DR and RS | DR and RS are semantically undefined for 0 episodes; failing the gate is correct |
| BSP threshold | `>= 0.8` | Exact match to constitution Principle VII gate criteria |
| DR/RS threshold | `>= 0.0` with `n > 0` check | Lenient threshold; gate ensures experiment ran, not that it evaded |
| Manifest extension | `extra_metadata: dict | None = None` kwarg | Non-breaking; existing callers unchanged; avoids coupling manifest to gate types |
| ValidationResult in run_experiment | Hardcoded default with BSP=0.0 | F23 explainability needed to compute real BSP; for now, gate always fails BSP |
| Gate summary format | "Phase 1 PASSED/FAILED (N/3 criteria met)" | Matches spec Assumptions; unambiguous for operator and CI parsing |

---

## Data Model

### GateResult (frozen dataclass)

| Field | Type | Description |
|---|---|---|
| `passed` | `bool` | `True` iff all 3 criteria pass |
| `criteria` | `tuple[CriterionResult, ...]` | Exactly 3 entries: DR, BSP, RS |
| `summary` | `str` | Human-readable one-liner |

### CriterionResult (frozen dataclass)

| Field | Type | Description |
|---|---|---|
| `name` | `str` | `"detection_rate"`, `"blind_spot_precision"`, `"robustness_score"` |
| `passed` | `bool` | Whether this criterion passed |
| `value` | `float` | Actual measured value |
| `threshold` | `float` | The gate threshold |

---

## Baseline and Target

| Metric | Value |
|---|---|
| Baseline (post-F25) | 312 passed, 4 skipped |
| New tests | 10 (C-001..C-010) |
| Target | ≥322 passed, 4 skipped |

---

## Complexity Tracking

No constitution violations. Table is empty.
