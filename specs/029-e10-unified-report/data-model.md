# Data Model: Unified Blind-Spot Report (F29)

**Date**: 2026-07-13
**Branch**: `029-e10-unified-report`

All entities live in `src/aatf/report.py`. They are in-memory, pure Python dataclasses
(frozen=True for immutability and hashability). No persistence; no DB schema.

---

## New Entities

### MLActionStats

Per-action anomaly summary derived from episode records.

```python
@dataclasses.dataclass(frozen=True)
class MLActionStats:
    action_id: str                 # unique action identifier (from StepRecord.action_id)
    category: str                  # suricata_category from ActionRegistry.get_action(action_id)
    mean_anomaly_all: float        # mean(s.anomaly_score) across ALL steps for this action_id
    mean_anomaly_undetected: float # mean(s.anomaly_score) for steps where not s.detected (0.0 if none)
    total_steps: int               # count of all steps for this action_id
    undetected_steps: int          # count of steps where not s.detected
```

**Validation rules**:
- `total_steps >= 1` (only actions that actually appear in records are included)
- `undetected_steps <= total_steps`
- `mean_anomaly_all >= 0.0`, `mean_anomaly_undetected >= 0.0`
- `mean_anomaly_undetected == 0.0` when `undetected_steps == 0`

---

### MLAnalysisSummary

The full ML section payload passed to the Jinja2 template as `ml_summary`.

```python
@dataclasses.dataclass(frozen=True)
class MLAnalysisSummary:
    cae: float                   # cumulative_anomaly_exposure(records) from metrics.py
    episode_count: int           # len(records)
    evasive: list[MLActionStats] # top-5 by ascending mean_anomaly_undetected; only where undetected_steps > 0
    suspicious: list[MLActionStats]  # top-5 by descending mean_anomaly_all
    retrain_categories: list[str]    # sorted unique suricata_category where mean_anomaly_undetected < EVASION_THRESHOLD
                                     # AND undetected_steps > 0
```

**Validation rules**:
- `len(evasive) <= 5`, `len(suspicious) <= 5`
- `evasive` sorted ascending by `mean_anomaly_undetected`
- `suspicious` sorted descending by `mean_anomaly_all`
- `retrain_categories` is sorted alphabetically (determinism guarantee)
- `episode_count >= 0` (0 only if records is empty — but _has_ml_scores would return False, so
  _compute_ml_summary is never called with empty records in practice)

---

## Constant

```python
EVASION_THRESHOLD: float = 0.3
# Actions with mean_anomaly_undetected < EVASION_THRESHOLD (and undetected_steps > 0)
# have their suricata_category added to retrain_categories.
```

---

## Helper Functions (private)

### _has_ml_scores

```python
def _has_ml_scores(records: list[EpisodeRecord]) -> bool:
    return any(s.anomaly_score > 0 for r in records for s in r.steps)
```

Called once in `generate_report()` to gate the ML computation. Returns False when all
anomaly_scores are 0.0 (NullDefence runs), ensuring zero performance overhead for Phase 1 reports.

---

### _compute_ml_summary

```python
def _compute_ml_summary(records: list[EpisodeRecord], registry: ActionRegistry) -> MLAnalysisSummary:
```

**Algorithm**:
1. Flatten all steps: iterate over every `r.steps` in `records`.
2. Group by `step.action_id`: accumulate a list of `(anomaly_score, is_undetected)` tuples.
3. For each action_id, compute:
   - `mean_anomaly_all` = mean of all anomaly_scores in the group
   - `mean_anomaly_undetected` = mean of anomaly_scores for undetected steps (0.0 if none)
   - `total_steps` = len(group)
   - `undetected_steps` = count where not step.detected
4. Look up `suricata_category` via `registry.get_action(action_id).suricata_category`; use
   `"UNKNOWN"` on KeyError.
5. Construct `MLActionStats` for each action_id.
6. Build `evasive`: filter to `undetected_steps > 0`, sort ascending by
   `mean_anomaly_undetected`, take first 5.
7. Build `suspicious`: sort all actions descending by `mean_anomaly_all`, take first 5.
8. Build `retrain_categories`: sorted unique categories from actions where
   `undetected_steps > 0` and `mean_anomaly_undetected < EVASION_THRESHOLD`.
9. Return `MLAnalysisSummary(cae=cumulative_anomaly_exposure(records), episode_count=len(records), ...)`.

---

## Relationship to Existing Entities

```
EpisodeRecord (metrics.py)
  └── steps: list[StepRecord]  (episode.py)
        ├── action_id: str       → key for grouping
        ├── detected: bool       → determines undetected_steps
        └── anomaly_score: float → basis for all ML stats

ActionRegistry (action_library.py)
  └── get_action(action_id) → ActionDefinition
        └── suricata_category: str → MLActionStats.category

MLActionStats (report.py, NEW)
  └── per-action summary

MLAnalysisSummary (report.py, NEW)
  ├── aggregates MLActionStats
  └── passed as "ml_summary" context variable to report.md.j2
```

---

## Template Context Extension

The following key is added to the existing Jinja2 `ctx` dict in `generate_report()`:

```python
ctx["ml_summary"] = _compute_ml_summary(records, registry) if _has_ml_scores(records) else None
```

When `ml_summary is None`, the `{% if ml_summary %}` block in the template is skipped entirely.
No other context keys are changed or removed.
