# Implementation Plan: Unified Blind-Spot Report (F29)

**Branch**: `029-e10-unified-report` | **Date**: 2026-07-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/029-e10-unified-report/spec.md`

## Summary

Extend `generate_report()` in `src/aatf/report.py` to auto-detect when ML anomaly scores are
present in episode records and conditionally render a new "ML Anomaly Defence Analysis" section
in the existing `report.md.j2` Jinja2 template. No new public API parameters — the ML section
appears iff `any(s.anomaly_score > 0 for r in records for s in r.steps)`. Two new private
dataclasses (`MLActionStats`, `MLAnalysisSummary`) and two private helpers
(`_has_ml_scores`, `_compute_ml_summary`) are added to `report.py`. Existing callers are
unchanged. Five new TDD contracts in `tests/test_unified_report.py` cover presence/absence,
ranking, and retraining recommendation logic. Baseline: 345. Target: ≥350.

## Technical Context

**Language/Version**: Python 3.12 (pinned)
**Primary Dependencies**: Jinja2 ≥3.1 (already in venv); stdlib `dataclasses`, `statistics`; `aatf.metrics.cumulative_anomaly_exposure` (added in F28)
**Storage**: pure in-memory computation; writes to caller-supplied `output_path` (inherited from existing generate_report)
**Testing**: pytest (from venv); `tests/test_unified_report.py` (new file)
**Target Platform**: Linux (same as project baseline)
**Project Type**: single Python package
**Performance Goals**: report generation < 2s (SC-001); no live lab access
**Constraints**: backward-compatible — all existing `generate_report()` callers work without modification; no changes to any module other than `report.py`, `report.md.j2`, and new test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|---------|
| I. Safety & Isolation | ✅ PASS | Report generation is purely offline analytics on logged records. No lab network access, no traffic emission, no live systems touched. |
| II. Reproducibility & Determinism | ✅ PASS | `generated_at` kwarg already enforces determinism. `_compute_ml_summary` is a pure function of `records` and `registry` — no runtime state, no RNG. SC-006 mandates byte-identical reruns. |
| III. Pluggable Defence Interface | ✅ PASS | `report.py` depends only on `EpisodeRecord.steps[*].anomaly_score` (a shared data contract field), not on any `Defence` subclass. The Defence interface is not touched. |
| IV. Scientific Validity & Test-First | ✅ PASS | TDD: 5 contracts written before implementation. CAE and table statistics cite `episode_count`. No single-run anecdotes — means are computed across all steps. |
| V. Explainability as First-Class | ✅ PASS | ML section names specific `action_id` and `suricata_category` values, not opaque aggregate scores alone. Retraining recommendation maps categories → training-data gap advice. |
| VI. Observability & Honest Feedback | ✅ PASS | All stats derived from logged `StepRecord.anomaly_score`; the offline layer operates on structured records, consistent with the two-layer architecture constraint. |
| VII. Phased Delivery Behind Gate | ✅ PASS | Phase 1 gate passed. F29 is a Phase 2 feature. Phase 1 content is preserved unchanged (SC-005, FR-008). |

**Result: ALL PASS — no violations, no complexity-tracking entries required.**

## Project Structure

### Documentation (this feature)

```text
specs/029-e10-unified-report/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
└── tasks.md             ← Phase 2 output (/sp.tasks)
```

### Source Code (repository root)

```text
src/aatf/
├── report.py            ← MODIFY: add MLActionStats, MLAnalysisSummary, _has_ml_scores,
│                           _compute_ml_summary; extend generate_report() body (signature unchanged)
└── templates/
    └── report.md.j2     ← MODIFY: add conditional ML section before footer line

tests/
└── test_unified_report.py  ← CREATE: C-001..C-005 (5 contracts)
```

**Structure Decision**: Single project, no new modules. All changes confined to two existing files
and one new test file.

## Complexity Tracking

> No constitution violations — table omitted per template instructions.
