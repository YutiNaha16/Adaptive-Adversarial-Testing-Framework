# Implementation Plan: Ground-Truth Validation Harness (F22)

**Branch**: `024-e6-ground-truth-validation` | **Date**: 2026-07-11 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/024-e6-ground-truth-validation/spec.md`

## Summary

Implement `aatf.ground_truth` — a pure offline module that classifies reported
blind spots as true positives or false positives by cross-checking them against a
caller-supplied set of deliberately disabled Suricata SIDs. The single public function
`validate_blind_spots(explanations, disabled_sids)` returns a `ValidationResult`
containing `blind_spot_precision`, which feeds the Phase 1 gate (≥ 0.8).

No new pip dependencies. Single file, ~55 LOC. 12 TDD contracts.

---

## Technical Context

**Language/Version**: Python 3.12 (pinned per F01 scaffold)  
**Primary Dependencies**: stdlib only — `dataclasses`; `aatf.explainability.ActionExplanation` (F23)  
**Storage**: N/A — pure in-memory function  
**Testing**: pytest; `cd src && pytest ../tests/test_ground_truth.py`  
**Target Platform**: Linux (same host as all other `aatf` modules)  
**Project Type**: Single Python package under `src/`  
**Performance Goals**: Negligible — O(n) over ≤1000 explanations  
**Constraints**: Pure function (FR-010); no I/O; no live Suricata; frozen result  
**Scale/Scope**: One call per experiment run; ≤1000 explanations per run

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Safety & Isolation | ✅ PASS | No network, no Docker, no file I/O — pure in-memory |
| II. Reproducibility & Determinism | ✅ PASS | Pure function; same inputs → same output always |
| III. Pluggable Defence Interface | ✅ N/A | Offline layer; consumes ActionExplanation, not Defence |
| IV. Scientific Validity / TDD | ✅ PASS | This IS the ground-truth validation mandated by Principle IV; 12 contracts first |
| V. Explainability | ✅ N/A | Consumes explainability output; doesn't produce it |
| VI. Observability & Honest Feedback | ✅ PASS | Precision is the honest metric for RQ2 |
| VII. Phased Delivery | ✅ PASS | Last E6 feature; feeds F26 gate evaluation |

**Post-design re-check**: All principles hold. Pure function with no I/O is the
simplest possible implementation consistent with Principle I.

---

## Project Structure

### Documentation (this feature)

```text
specs/024-e6-ground-truth-validation/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   └── ground-truth-contract.md   ← 12 contracts C-001..C-012
└── tasks.md             (Phase 2 — /sp.tasks)
```

### Source Code

```text
src/
└── aatf/
    └── ground_truth.py    # ~55 LOC (NEW)

tests/
└── test_ground_truth.py   # ~150 LOC, 12 tests (NEW)
```

**Structure Decision**: Single-file addition. Matches existing pattern (one module per feature).

---

## Implementation Sketch

### src/aatf/ground_truth.py (~55 LOC)

```python
"""Ground-truth validation harness — computes Blind-Spot Precision against disabled SIDs."""
from __future__ import annotations

from dataclasses import dataclass

from aatf.explainability import ActionExplanation

SURICATA_SID_CATEGORIES: dict[str, str] = {
    "2001219": "ET SCAN",
    "2008581": "ET SCAN",
    "2002087": "ET BRUTE_FORCE",
    "2019284": "ET BRUTE_FORCE",
    "2012648": "ET EXPLOIT",
    "2016778": "ET DNS",
    "2013028": "ET POLICY",
    "2014726": "ET TROJAN",
    "2010935": "ET WEB_CLIENT",
    "2009714": "ET WEB_SERVER",
}


@dataclass(frozen=True)
class ValidationResult:
    blind_spot_precision: float
    true_positives: int
    false_positives: int
    total_reported: int
    disabled_sid_count: int

    @property
    def meets_gate(self) -> bool:
        return self.blind_spot_precision >= 0.8


def validate_blind_spots(
    explanations: list[ActionExplanation],
    disabled_sids: set[str],
) -> ValidationResult:
    disabled_categories = {
        SURICATA_SID_CATEGORIES[s] for s in disabled_sids if s in SURICATA_SID_CATEGORIES
    }
    tp = sum(1 for e in explanations if e.suricata_category in disabled_categories)
    total = len(explanations)
    fp = total - tp
    precision = tp / total if total > 0 else 0.0
    return ValidationResult(
        blind_spot_precision=precision,
        true_positives=tp,
        false_positives=fp,
        total_reported=total,
        disabled_sid_count=len(disabled_sids),
    )
```

### tests/test_ground_truth.py (~150 LOC)

```python
import pytest
from dataclasses import FrozenInstanceError
from aatf.explainability import ActionExplanation
from aatf.ground_truth import (
    validate_blind_spots, ValidationResult, SURICATA_SID_CATEGORIES
)

def _expl(action_id: str, suricata_category: str) -> ActionExplanation: ...

# C-001..C-003: ValidationResult shape
# C-004..C-006: meets_gate property
# C-007..C-011: validate_blind_spots logic
# C-012: SURICATA_SID_CATEGORIES coverage
```

---

## Baseline and target

| Metric | Value |
|---|---|
| Baseline (post-F24) | 286 passed, 4 skipped, 6 failed |
| New tests | 12 (C-001..C-012) |
| Target | ≥298 passed, 4 skipped, 6 failed |

---

## Story completion order

| Story | Contracts | Notes |
|---|---|---|
| US1 (P1) Core validation | C-001..C-003, C-007..C-011 | ValidationResult + validate_blind_spots |
| US2 (P2) SID map | C-012 | SURICATA_SID_CATEGORIES coverage |
| US3 (P3) Gate | C-004..C-006 | meets_gate property |

---

## Complexity Tracking

No constitution violations. Table is empty.
