# Data Model: Report Generator (F24)

**Phase**: 1 — Design  
**Date**: 2026-07-11  
**Feature**: 023-e6-report-generator

## Entities

### ReportContext (internal — not user-facing)

Deterministically-assembled bundle passed to the Jinja2 template. All collections are
pre-sorted so template rendering is order-stable. Built from episode records + computed
metrics before the template is called.

```python
# Not a dataclass — just the dict passed to template.render(**ctx)
ctx = {
    "attacker_classes": list[str],     # sorted unique attacker_class values
    "seeds":            list[int],      # sorted unique seed values
    "episode_count":    int,            # len(records)
    "generated_at":     str,            # ISO 8601 timestamp string
    "detection_rate":   float,          # from aatf.metrics.detection_rate
    "robustness_score": float,          # from aatf.metrics.robustness_score(window)
    "robustness_window": int,           # min(10, len(records))
    "reward_mean":      float | None,   # MultiSeedResult.mean  (None if no records)
    "reward_std":       float | None,   # MultiSeedResult.std
    "reward_ci_low":    float | None,   # MultiSeedResult.ci_low
    "reward_ci_high":   float | None,   # MultiSeedResult.ci_high
    "explanations":     list[ActionExplanation],  # from explain_evasions, already sorted
}
```

**Invariants**:
- `attacker_classes` and `seeds` are sorted ascending
- `reward_*` fields are all None together (when records is empty) or all float
- `explanations` is sorted by (-evasion_rate, action_id) — guaranteed by explain_evasions
- `generated_at` is always an ISO 8601 string (pre-formatted before template call)

---

## Files

```text
src/aatf/
├── report.py                  # generate_report function (~60 LOC)
└── templates/
    └── report.md.j2           # Jinja2 Markdown template (~35 LOC)

tests/
└── test_report.py             # ~200 LOC, 10 contracts C-001..C-010
```

---

## Consumed entities (read-only)

### EpisodeRecord (from `aatf.metrics`, F20)

Fields accessed: `.attacker_class`, `.seed`, `.total_reward`, `.steps` (via explain_evasions)

### ActionRegistry (from `aatf.action_library`, F10)

Passed through to `explain_evasions` — not accessed directly by `generate_report`.

### ActionExplanation (from `aatf.explainability`, F23)

Fields rendered in template: `.action_id`, `.suricata_category`, `.evasion_rate`,
`.evasion_count`, `.total_count`, `.remediation`

### MultiSeedResult (from `aatf.statistics`, F21)

Fields accessed: `.mean`, `.std`, `.ci_low`, `.ci_high`

---

## Data flow

```
list[EpisodeRecord]  +  ActionRegistry
         │
         ▼ data assembly (generate_report)
  sorted attacker_classes
  sorted seeds
  episode_count
  detection_rate()  ─────────────────────┐
  robustness_score(window) ──────────────┤
  summarise_metric("total_reward", ...) ─┤  ReportContext dict
  explain_evasions() ────────────────────┘
         │
         ▼ Jinja2 template.render(**ctx)
  Markdown string
         │
         ├─▶ written to output_path
         └─▶ returned to caller
```

---

## Template variable contract

Every variable the template references MUST be present in the context dict. Template
uses `{{ var }}` (not `{{ var | default(...) }}`), so missing keys raise `UndefinedError`
at render time — this is intentional (fail loud, not silently).

Exception: `reward_mean`, `reward_std`, `reward_ci_low`, `reward_ci_high` may be `None`
when records is empty. Template uses `{% if reward_mean is not none %}` guard.

---

## Module layout

```python
# src/aatf/report.py
from __future__ import annotations
from datetime import UTC, datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from aatf.action_library import ActionRegistry
from aatf.explainability import explain_evasions
from aatf.metrics import EpisodeRecord, detection_rate, robustness_score
from aatf.statistics import summarise_metric

def generate_report(
    records: list[EpisodeRecord],
    registry: ActionRegistry,
    output_path: str | Path,
    *,
    generated_at: datetime | None = None,
) -> str: ...
```
