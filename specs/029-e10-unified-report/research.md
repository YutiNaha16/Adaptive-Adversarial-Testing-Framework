# Research: Unified Blind-Spot Report (F29)

**Date**: 2026-07-13
**Branch**: `029-e10-unified-report`

## Source Verification Findings

All unknowns from the technical context were resolved by reading the actual source files.
No NEEDS CLARIFICATION items remain.

---

### Decision 1: generate_report() signature — auto-detect vs explicit parameter

**Question**: Should the ML section be triggered by a new `ml_summary=` kwarg (caller-supplied)
or auto-detected from `records` contents?

**Decision**: Auto-detect from `records`. No new public parameter.

**Rationale**:
- `any(s.anomaly_score > 0 for r in records for s in r.steps)` is always computable from the
  existing argument; no caller needs to know about ML at the call site.
- Existing callers (`run_experiment.py`, `test_report.py`) pass zero-score records
  (NullDefence) → ML section stays absent automatically, satisfying SC-005 (backward
  compatibility) with zero code changes at call sites.
- An explicit kwarg would require updating `run_experiment.py` to pass `ml_summary=` and would
  force every test that calls `generate_report()` to be aware of ML state. That is unnecessary
  coupling.

**Alternatives considered**:
- `ml_summary: MLAnalysisSummary | None = None` kwarg: rejected — see above.
- Separate `generate_ml_report()` function: rejected — FR-001 requires a single output file;
  split functions violate the "one unified document" goal.

---

### Decision 2: Where to insert ML section in template

**Question**: Before or after the `---` footer separator in `report.md.j2`?

**Decision**: Add the ML block between the "## Blind Spots" closing and the existing `---` footer.
The existing footer (`---\n*Generated from logged episode records...*`) becomes the document's
final line, appearing after the ML section when present.

**Rationale**:
- The footer is a provenance statement that should close every report regardless of ML state;
  it must appear last.
- The ML section logically follows the Suricata blind-spot analysis as a second analytical lens.
- Inserting a new `---` separator before the ML heading and keeping the existing footer after
  maintains visual document structure (each major section separated by `---`).

**Confirmed from source**: `report.md.j2` currently ends:
```
{% endif %}

---
*Generated from logged episode records. No live defence systems were accessed.*
```
The insertion point is the blank line between `{% endif %}` (end of Blind Spots block) and
the `---` footer separator.

---

### Decision 3: suricata_category lookup path

**Question**: How to map `action_id` → `suricata_category` for `MLActionStats.category`?

**Decision**: `registry.get_action(action_id).suricata_category`

**Confirmed from source** (`src/aatf/action_library.py`):
- `ActionDefinition` dataclass has `action_id: str` (line 13) and `suricata_category: str`
  (line 17).
- `ActionRegistry.get_action(action_id: str) -> ActionDefinition` (line 46).
- `REGISTRY` is the global singleton populated with 15 action definitions.

**Fallback**: If `get_action(action_id)` raises `KeyError` (should not happen with valid
records), catch and use `"UNKNOWN"` as category to prevent report generation from crashing on
malformed test data.

---

### Decision 4: "undetected" definition for MLActionStats

**Question**: What does "undetected" mean for per-action stats?

**Decision**: `StepRecord.detected == False` → undetected.

**Confirmed from source** (`src/aatf/episode.py` line 21):
- `StepRecord.detected: bool` — True when Suricata/ML triggered an alert; False when the step
  evaded detection.
- `undetected_steps` = count of steps for this action_id where `not step.detected`.
- `mean_anomaly_undetected` = mean of `step.anomaly_score` over those steps (0.0 if none).

**Note**: An action can have `detected=False` and `anomaly_score=0.0` (under NullDefence). In
that regime `_has_ml_scores` returns False and `_compute_ml_summary` is never called, so the
0.0-score-undetected case only appears when ML scores are genuinely present.

---

### Decision 5: cumulative_anomaly_exposure() import

**Confirmed from source** (`src/aatf/metrics.py` line 54):
```python
def cumulative_anomaly_exposure(records: list[EpisodeRecord]) -> float:
```
Already imported via `from aatf.metrics import EpisodeRecord, detection_rate, robustness_score`
in `report.py`. Will add `cumulative_anomaly_exposure` to the same import line.

---

### Decision 6: EVASION_THRESHOLD value and location

**Decision**: `EVASION_THRESHOLD: float = 0.3` as a module-level constant in `report.py`.

**Rationale**: The spec explicitly fixes this at 0.3 and states YAML configurability is out of
scope for F29. A module-level constant is the simplest correct placement — it is visible to
tests and can be patched via `monkeypatch` if a future feature needs configurability.

---

### Decision 7: Jinja2 number formatting in template

**Question**: Can Jinja2 use Python `%`-style `format()` filter as `"%.4f" | format(value)`?

**Confirmed**: Yes. Jinja2's `format` filter applies Python `%`-style formatting. The existing
template already uses `"%.1f%%" | format(detection_rate * 100)` (line 12 of report.md.j2) and
`"%.4f" | format(reward_mean)` (line 17). The same pattern applies to `ml_summary.cae` and
action scores.

---

## No Outstanding Unknowns

All 7 decisions are resolved. The implementation is fully specified and can proceed to
data-model.md and tasks.md without further clarification.
