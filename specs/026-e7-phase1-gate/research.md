# Research: Automated Phase 1 Gate Evaluation (F26)

**Date**: 2026-07-11
**Feature**: 026-e7-phase1-gate

## API Inspection Results

12 decisions made from reading actual source files.

---

### D-001: `detection_rate` empty-list behavior

- **Decision**: Returns `0.0` (not raises)
- **Rationale**: `total = sum(len(r.steps) for r in [])` = 0; early return `0.0`
- **Source**: `src/aatf/metrics.py:20-25`

---

### D-002: `robustness_score` zero-window behavior

- **Decision**: `robustness_score(records, window=0)` returns `0.0` (window ≤ 0 check)
- **Rationale**: `if window <= 0: return 0.0` — so for empty records where `min(10, 0) = 0`, RS = 0.0
- **Source**: `src/aatf/metrics.py:28-31`

---

### D-003: `robustness_score` for non-empty records with window > 0

- **Decision**: `robustness_score(records, window=min(10, n)) = detection_rate(records[-window:])`
- **Rationale**: Window slices the last N records; with NullDefence and no alerts, RS = 0.0
- **Source**: `src/aatf/metrics.py:31`

---

### D-004: `ValidationResult` field access

- **Decision**: `validation_result.blind_spot_precision` is a plain `float` field
- **Rationale**: Frozen dataclass; BSP set at construction time
- **Source**: `src/aatf/ground_truth.py:22-31`

---

### D-005: Default ValidationResult construction

- **Decision**: `ValidationResult(blind_spot_precision=0.0, true_positives=0, false_positives=0, total_reported=0, disabled_sid_count=0)`
- **Rationale**: All 5 fields required (no defaults); explicit construction avoids `validate_blind_spots` import in run_experiment
- **Source**: `src/aatf/ground_truth.py:22-28`

---

### D-006: `write_manifest` current signature

- **Decision**: Add `extra_metadata: dict | None = None` as keyword-only parameter
- **Rationale**: Existing signature uses `*` for keyword-only; `extra_metadata` extends without breaking existing callers
- **Source**: `src/aatf/manifest.py:42-48`

---

### D-007: `criteria` field type in `GateResult`

- **Decision**: `tuple[CriterionResult, ...]` instead of `list[CriterionResult]`
- **Rationale**: `GateResult` is `frozen=True`; a `list` field would still be mutable (frozen only prevents reassignment); `tuple` enforces true immutability
- **Alternatives**: `list[CriterionResult]` (simpler but mutable), `frozenset` (loses ordering)

---

### D-008: Phase 1 gate criterion for DR

- **Decision**: `passed = n > 0` (not `value >= 0.0`)
- **Rationale**: DR ≥ 0.0 is trivially true for any float ≥ 0; the meaningful check is "did the experiment run at all?" — i.e., at least one episode. DR = 0.0 with n=1 is fine (NullDefence detects nothing).
- **Alternatives**: `passed = (value >= 0.0)` — always True, meaningless gate

---

### D-009: Phase 1 gate criterion for RS

- **Decision**: `passed = n > 0` (symmetric with DR)
- **Rationale**: RS = 0.0 for n=0 due to window=0 path; the check is "did the experiment run?" With NullDefence, RS = 0.0 even for n > 0, and that's a PASS because the threshold is 0.0.
- **Wait** — if `passed = (n > 0)` then RS criterion passes whenever episodes > 0, regardless of RS value. But threshold=0.0 means RS ≥ 0.0 which is always true for n > 0. So `passed = n > 0` is correct.

---

### D-010: Summary string format

- **Decision**: `"Phase 1 PASSED (3/3 criteria met)"` / `"Phase 1 FAILED (1/3 criteria met: blind_spot_precision, robustness_score below threshold)"`
- **Rationale**: Matches spec Assumptions section; parseable by CI (PASSED/FAILED as keywords)

---

### D-011: Test approach for C-009 (stdout contains gate lines)

- **Decision**: Reuse `_write_config(tmp_path, episodes=2)` helper from `test_run_experiment.py`; add similar helper in `test_gate.py` or import; use `capsys.readouterr().out`
- **Rationale**: Consistent with existing test patterns in test_run_experiment.py

---

### D-012: `run_experiment.py` integration ordering

- **Decision**: Compute gate BEFORE writing manifest; pass gate data via `extra_metadata` to `write_manifest()`
- **Rationale**: Manifest should contain the gate result; gate must be computed first
- **Implementation order in main()**: records → gate_result → dr/rs summary print → gate block print → generate_report → write_manifest(extra_metadata=gate_data)
