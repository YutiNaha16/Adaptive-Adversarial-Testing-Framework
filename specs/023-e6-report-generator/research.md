# Research: Report Generator (F24)

**Phase**: 0 — Pre-design research  
**Date**: 2026-07-11  
**Feature**: 023-e6-report-generator

## Summary

No external research required. All design questions resolved from existing codebase and
spec. Key findings: Jinja2 not installed (must add to requirements.in); robustness_score
handles window=0 safely (returns 0.0); template loading via `Path(__file__).parent` is
simpler than importlib.resources for Phase 1.

---

## Decision 1: Template loading mechanism

**Decision**: `Path(__file__).parent / "templates" / "report.md.j2"` passed to
`FileSystemLoader`.

**Rationale**: Direct path reference is simple, zero-config, and works identically in
tests and production. No `MANIFEST.in`, no `package_data` in `pyproject.toml` required.
The template file is co-located with the module in `src/aatf/templates/`.

**Alternatives considered**:
- `importlib.resources.files("aatf") / "templates" / "report.md.j2"`: correct for
  installed packages; overkill for Phase 1 editable install where the path is always
  the literal source tree. Rejected.
- Inline template string: loses the ability to view/edit the report layout without
  touching Python; rejected.

---

## Decision 2: Jinja2 autoescape setting

**Decision**: `autoescape=False`.

**Rationale**: Output is Markdown, not HTML. Autoescaping would turn `>=` into `&gt;=`
and corrupt Markdown table content. FR-003 (determinism) requires that rendered output
be stable — autoescaping introduces no non-determinism, but the bug risk is high.

**Alternatives considered**:
- `autoescape=True`: wrong for Markdown; rejected.
- `select_autoescape(["html"])`: cleaner but still wrong since `.j2` template isn't
  listed as HTML; functionally equivalent to False for `.md.j2`; rejected for clarity.

---

## Decision 3: Empty-records guard for robustness_score

**Decision**: `window = min(10, len(records)); rs = robustness_score(records, window=window)`.
When `len(records) == 0`, `window=0` and `robustness_score` returns `0.0` (confirmed
by reading `metrics.py` line 29-30). No special-case needed.

**Alternatives considered**:
- Explicit `if not records: rs = 0.0 else: ...`: adds a branch for something already
  handled by the callee; rejected.

---

## Decision 4: reward_summary when records is empty

**Decision**: `summarise_metric` raises `ValueError` for empty values list (confirmed
by F21 spec). Guard: `reward_summary = summarise_metric("total_reward", reward_values) if reward_values else None`. Template renders "N/A" when `reward_summary is None`.

**Rationale**: Avoids ValueError propagating to the caller; the empty case is
legitimately "no data" not "an error."

**Alternatives considered**:
- Always call summarise_metric and catch ValueError: try/except in hot path; rejected.
- Sentinel MultiSeedResult with zeros: adds a dummy object of false precision; rejected.

---

## Decision 5: Jinja2 format filter for floats

**Decision**: Use `"%.1f%%" | format(value * 100)` for percentages and
`"%.4f" | format(value)` for raw floats in the template.

**Rationale**: Jinja2's `format` filter wraps Python's `%` string formatting, which is
deterministic for the same float value. `"%.1f"` gives one decimal place for rates;
`"%.4f"` gives four for rewards. Both are stable across runs with the same inputs.

**Alternatives considered**:
- `{{ value | round(4) }}`: produces varying decimal places for trailing zeros; rejected.
- Python `f"{value:.4f}"` in data assembly before template: moves formatting logic to
  Python but loses template flexibility; rejected.

---

## Decision 6: Generated-at timestamp parameter

**Decision**: `generated_at: datetime | None = None`; default is `datetime.now(UTC)`.
Tests always supply a fixed `datetime(2024, 1, 1, tzinfo=UTC)`.

**Rationale**: Determinism (constitution Principle II, FR-003) requires that two calls
with the same data produce identical strings. Wall-clock time breaks this. Caller-supplied
default follows the same pattern as NumPy's `rng_seed` in F21.

**Alternatives considered**:
- Always use wall-clock: non-deterministic; rejected.
- Accept a string: loses type safety; rejected.

---

## Integration contracts confirmed

| Symbol | Location | Used for |
|---|---|---|
| `EpisodeRecord` | `aatf.metrics` | input list type + `.steps`, `.total_reward`, `.attacker_class`, `.seed` |
| `detection_rate` | `aatf.metrics` | headline metrics |
| `robustness_score` | `aatf.metrics` | headline metrics (window=10) |
| `summarise_metric` | `aatf.statistics` | reward CI computation |
| `explain_evasions` | `aatf.explainability` | blind-spots section |
| `ActionRegistry` | `aatf.action_library` | passed to explain_evasions |

---

## New dependency

| Package | Version constraint | Why |
|---|---|---|
| `jinja2` | `>=3.1` | Markdown template rendering |

**Install**: `pip install jinja2` in venv; add `jinja2>=3.1` to `requirements.in` under
"Templating" section; recompile `requirements.txt` via `pip-compile`.

Confirmed: Jinja2 is NOT currently in venv (ModuleNotFoundError on import check).

---

## Test ground truths

| Contract | Setup | Expected |
|---|---|---|
| C-002 | call once → check return==file content | string equality |
| C-003 | call twice with fixed generated_at | output_a == output_b |
| C-004 | records=[] | no error, len(result) > 0 |
| C-005 | 2 steps detected, 2 not → dr=0.5 | "50.0%" in report |
| C-006 | total_reward=[1.0, -1.0] → mean=0.0 | "0.0000" in report |
| C-007 | action_a 3/4 evaded, action_b 1/4 | action_a before action_b in blind spots |
| C-008 | all steps detected | empty-table message in report |
| C-009 | attacker_class="LinUCB", seed=42 | "LinUCB" and "42" in report |
| C-010 | output_path="/nonexistent/dir/r.md" | FileNotFoundError |

Baseline: 276 passed, 4 skipped, 6 failed. Target: ≥286 (+10).
