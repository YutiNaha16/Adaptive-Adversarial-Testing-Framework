# Implementation Plan: Report Generator (F24)

**Branch**: `023-e6-report-generator` | **Date**: 2026-07-11 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/023-e6-report-generator/spec.md`

## Summary

Implement `aatf.report` — a module that assembles experiment results into a deterministic
Markdown blind-spot report via Jinja2 templating. The single public function
`generate_report(records, registry, output_path, *, generated_at=None)` orchestrates:

1. Guard: raise `FileNotFoundError` if `output_path` parent does not exist.
2. Data assembly: sorted attacker classes, sorted seeds, episode count, detection metrics
   (F20), total_reward CI (F21), ranked explanations (F23).
3. Template render: Jinja2 fills `src/aatf/templates/report.md.j2` with the assembled
   context dict.
4. File write: write rendered string to `output_path`.
5. Return rendered string.

New pip dependency: `jinja2>=3.1`. 10 TDD contracts.

---

## Technical Context

**Language/Version**: Python 3.12 (pinned per F01 scaffold)  
**Primary Dependencies**: `jinja2>=3.1` (NEW); stdlib: `pathlib`, `datetime`; `aatf.metrics` (F20), `aatf.statistics` (F21), `aatf.explainability` (F23), `aatf.action_library` (F10)  
**Storage**: Local filesystem — writes `output_path` (caller-supplied); reads template from `src/aatf/templates/report.md.j2`  
**Testing**: pytest (already in venv); `cd src && pytest ../tests/test_report.py`  
**Target Platform**: Linux (same host as all other `aatf` modules)  
**Project Type**: Single Python package under `src/`  
**Performance Goals**: Negligible — offline report generation over ≤1000 episodes  
**Constraints**: Deterministic output (FR-003); no live defence access (FR-010); no mkdir (FR-009)  
**Scale/Scope**: One report per experiment run; template fits comfortably in memory

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Safety & Isolation | ✅ PASS | Reads logged records + writes local file; no network, no lab env |
| II. Reproducibility & Determinism | ✅ PASS | Caller-supplied timestamp + sorted collections = byte-for-byte determinism |
| III. Pluggable Defence Interface | ✅ N/A | Offline layer; consumes Defence output via EpisodeRecord, not Defence directly |
| IV. Scientific Validity / TDD | ✅ PASS | 10 contracts upfront; metrics derived from F20/F21 (already tested) |
| V. Explainability | ✅ PASS | This IS the explainability report: every blind spot paired with remediation (via F23) |
| VI. Observability & Honest Feedback | ✅ PASS | Renders from structured logs; footer states data source |
| VII. Phased Delivery | ✅ PASS | E6 feature on critical path to F25/F26 gate |

**Post-design re-check**: All principles hold. `autoescape=False` is correct for Markdown
(not HTML). Template path via `Path(__file__).parent` is stable in editable install.

---

## Project Structure

### Documentation (this feature)

```text
specs/023-e6-report-generator/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   └── report-contract.md   ← 10 contracts C-001..C-010
└── tasks.md             (Phase 2 — /sp.tasks)
```

### Source Code

```text
src/
└── aatf/
    ├── report.py                  # ~60 LOC (NEW)
    └── templates/
        └── report.md.j2           # ~35 LOC Jinja2 template (NEW)

tests/
└── test_report.py                 # ~200 LOC, 10 tests (NEW)
```

**Structure Decision**: Single-file addition to `src/aatf/` with a co-located
`templates/` subdirectory. Matches existing pattern: one module per feature.

---

## Implementation Sketch

### src/aatf/report.py (~60 LOC)

```python
"""Report generator — renders blind-spot Markdown report from episode logs."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from aatf.action_library import ActionRegistry
from aatf.explainability import explain_evasions
from aatf.metrics import EpisodeRecord, detection_rate, robustness_score
from aatf.statistics import summarise_metric

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def generate_report(
    records: list[EpisodeRecord],
    registry: ActionRegistry,
    output_path: str | Path,
    *,
    generated_at: datetime | None = None,
) -> str:
    out = Path(output_path)
    if not out.parent.exists():
        raise FileNotFoundError(f"Output directory does not exist: {out.parent}")

    if generated_at is None:
        generated_at = datetime.now(UTC)

    attacker_classes = sorted({r.attacker_class for r in records})
    seeds = sorted({r.seed for r in records})
    episode_count = len(records)
    window = min(10, len(records))
    dr = detection_rate(records)
    rs = robustness_score(records, window=window)
    reward_values = [r.total_reward for r in records]
    reward_summary = summarise_metric("total_reward", reward_values) if reward_values else None
    explanations = explain_evasions(records, registry)

    ctx = {
        "attacker_classes": attacker_classes,
        "seeds": seeds,
        "episode_count": episode_count,
        "generated_at": generated_at.isoformat(),
        "detection_rate": dr,
        "robustness_score": rs,
        "robustness_window": window,
        "reward_mean": reward_summary.mean if reward_summary else None,
        "reward_std": reward_summary.std if reward_summary else None,
        "reward_ci_low": reward_summary.ci_low if reward_summary else None,
        "reward_ci_high": reward_summary.ci_high if reward_summary else None,
        "explanations": explanations,
    }

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = env.get_template("report.md.j2")
    rendered = template.render(**ctx)

    out.write_text(rendered, encoding="utf-8")
    return rendered
```

### src/aatf/templates/report.md.j2 (~35 LOC)

```jinja2
# Blind-Spot Report

## Run Metadata

- **Attacker**: {{ attacker_classes | join(", ") if attacker_classes else "N/A" }}
- **Seeds**: {{ seeds | join(", ") if seeds else "N/A" }}
- **Episodes**: {{ episode_count }}
- **Generated**: {{ generated_at }}

## Headline Metrics

| Metric | Value |
|--------|-------|
| Detection Rate | {{ "%.1f%%" | format(detection_rate * 100) }} |
| Robustness Score (last {{ robustness_window }} ep.) | {{ "%.1f%%" | format(robustness_score * 100) }} |
{% if reward_mean is not none %}
| Mean Total Reward | {{ "%.4f" | format(reward_mean) }} ± {{ "%.4f" | format(reward_std) }} (95% CI: {{ "%.4f" | format(reward_ci_low) }}–{{ "%.4f" | format(reward_ci_high) }}) |
{% else %}
| Mean Total Reward | N/A |
{% endif %}

## Blind Spots

{% if explanations %}
| Action | Category | Evasion Rate | Evaded | Total | Remediation |
|--------|----------|--------------|--------|-------|-------------|
{% for ex in explanations %}
| {{ ex.action_id }} | {{ ex.suricata_category }} | {{ "%.1f%%" | format(ex.evasion_rate * 100) }} | {{ ex.evasion_count }} | {{ ex.total_count }} | {{ ex.remediation }} |
{% endfor %}
{% else %}
_No blind spots detected — all actions were detected on every step._
{% endif %}

---
*Generated from logged episode records. No live defence systems were accessed.*
```

---

## Test Structure (tests/test_report.py)

```python
FIXED_TS = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

def _step(action_id, detected): ...
def _ep(attacker_class, seed, *steps, total_reward=0.0): ...
def _reg(*defs): ...
def _defn(action_id, suricata_category): ...

def test_c001_importable(): ...
def test_c002_returns_string_and_writes_file(tmp_path): ...
def test_c003_determinism(tmp_path): ...
def test_c004_empty_records(tmp_path): ...
def test_c005_detection_rate_in_report(tmp_path): ...
def test_c006_mean_reward_in_report(tmp_path): ...
def test_c007_blind_spots_ranked(tmp_path): ...
def test_c008_no_blind_spots_message(tmp_path): ...
def test_c009_metadata_fields(tmp_path): ...
def test_c010_missing_parent_raises(tmp_path): ...
```

All tests use `tmp_path` (pytest fixture) for file writes. No mocking of the
file system — real writes to pytest's temp directory.

---

## Baseline and target

| Metric | Value |
|---|---|
| Baseline (post-F23) | 276 passed, 4 skipped, 6 failed |
| New tests | 10 (C-001..C-010) |
| Target | ≥286 passed, 4 skipped, 6 failed |

---

## Story completion order

| Story | Contracts | Blocking? |
|---|---|---|
| US1 (P1) Core generation | C-001..C-004 | Yes — template + write path must work before testing content |
| US2 (P2) Headline metrics | C-005, C-006 | Yes — metrics populate template variables |
| US3 (P3) Blind spots | C-007, C-008 | Depends on US1 + explain_evasions wired |
| US4 (P4) Metadata + footer | C-009, C-010 | C-009 tests metadata; C-010 tests error guard |

---

## New pip dependency

```
requirements.in additions:
# Templating (Feature F24 / Epic E6)
jinja2>=3.1
```

Install before red phase: `pip install jinja2` in venv, then `pip-compile requirements.in -o requirements.txt`.

---

## Complexity Tracking

No constitution violations. Table is empty.
