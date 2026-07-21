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
    skipped: bool = False  # True when criterion is not applicable in current mode


@dataclass(frozen=True)
class GateResult:
    passed: bool
    criteria: tuple[CriterionResult, ...]
    summary: str


def phase1_gate(
    records: list[EpisodeRecord],
    validation_result: ValidationResult,
    *,
    lab_mode: bool = False,
) -> GateResult:
    n = len(records)
    dr_value = detection_rate(records)
    rs_value = robustness_score(records, window=min(10, n)) if n > 0 else 0.0

    if lab_mode:
        bsp = CriterionResult(
            name="blind_spot_precision",
            threshold=0.8,
            value=validation_result.blind_spot_precision,
            passed=validation_result.blind_spot_precision >= 0.8,
        )
    else:
        bsp = CriterionResult(
            name="blind_spot_precision",
            threshold=0.8,
            value=0.0,
            passed=True,
            skipped=True,
        )

    criteria = (
        CriterionResult(name="detection_rate", threshold=0.0, value=dr_value, passed=n > 0),
        bsp,
        CriterionResult(name="robustness_score", threshold=0.0, value=rs_value, passed=n > 0),
    )

    applicable = [c for c in criteria if not c.skipped]
    passed = all(c.passed for c in applicable)
    met = sum(c.passed for c in applicable)
    total = len(applicable)

    if passed:
        summary = f"Phase 1 PASSED ({met}/{total} criteria met)"
    else:
        failing = ", ".join(c.name for c in applicable if not c.passed)
        summary = f"Phase 1 FAILED ({met}/{total} criteria met: {failing} below threshold)"

    return GateResult(passed=passed, criteria=criteria, summary=summary)
