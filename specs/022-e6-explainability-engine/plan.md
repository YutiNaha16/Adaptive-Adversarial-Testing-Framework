# Implementation Plan: Explainability Engine (F23)

**Branch**: `022-e6-explainability-engine` | **Date**: 2026-07-11 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/022-e6-explainability-engine/spec.md`

## Summary

Implement `aatf.explainability` — a pure, in-memory module that maps evaded attack
actions to ranked, defender-actionable explanations. The module provides:

1. `ActionExplanation` — a frozen dataclass with 8 fields capturing what evaded, how
   often, and how to fix it.
2. `explain_evasions(records, registry)` — walks episode step logs, tallies per-action
   evasion counts, looks up technique metadata from `ActionRegistry` (F10), and resolves
   remediation + false-positive-risk text from a built-in `REMEDIATION_TABLE` constant
   covering all 8 Phase 1 `suricata_category` values. Returns list sorted by evasion_rate
   descending; ties broken by action_id ascending.

Consumes F10 (ActionRegistry) and F20 (EpisodeRecord) with no new pip dependencies.
Implemented TDD: 12 contracts written upfront (red), then green story-by-story.

---

## Technical Context

**Language/Version**: Python 3.12 (pinned per F01 scaffold)  
**Primary Dependencies**: stdlib only (`dataclasses`); `aatf.metrics` (F20), `aatf.action_library` (F10)  
**Storage**: N/A — pure in-memory function  
**Testing**: pytest (already in venv); `cd src && pytest ../tests/test_explainability.py`  
**Target Platform**: Linux (same host as all other `aatf` modules)  
**Project Type**: Single Python package under `src/`  
**Performance Goals**: Negligible — offline analytics over ≤1000 episodes  
**Constraints**: Pure function (FR-010): no I/O, no subprocess, no network  
**Scale/Scope**: Up to 15 action_ids × N episodes × M steps; all in-memory

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Safety & Isolation | ✅ PASS | Pure offline analytics; no network, no lab env access |
| II. Reproducibility & Determinism | ✅ PASS | No randomness; sorted output deterministic (compound key) |
| III. Pluggable Defence Interface | ✅ N/A | Offline layer; does not couple to Defence interface |
| IV. Scientific Validity / TDD | ✅ PASS | 12 contracts written upfront; all hand-verifiable |
| V. Explainability | ✅ PASS | This IS the explainability feature; every blind spot paired with concrete fix (FR-005) |
| VI. Observability & Honest Feedback | ✅ PASS | Feeds F24 report; consumes structured step logs |
| VII. Phased Delivery | ✅ PASS | E6 feature on critical path to Phase 1 gate |

**Post-design re-check**: All principles still hold. REMEDIATION_TABLE is a module-level
constant (A4) — no external call, no non-determinism. Generic fallback covers unknown
categories — no silent data loss.

---

## Project Structure

### Documentation (this feature)

```text
specs/022-e6-explainability-engine/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   └── explainability-contract.md  ← 12 contracts C-001..C-012
└── tasks.md             (Phase 2 output — /sp.tasks command)
```

### Source Code

```text
src/
└── aatf/
    └── explainability.py   # ~55 LOC (NEW)

tests/
└── test_explainability.py  # ~150 LOC, 12 tests (NEW)
```

**Structure Decision**: Single-file addition to the existing `src/aatf/` package.
No new subdirectories. Matches the pattern established by F21 (`statistics.py` /
`test_statistics.py`).

---

## Implementation Sketch

```python
"""Explainability engine — maps evaded actions to ranked remediation hints."""
from __future__ import annotations

from dataclasses import dataclass

from aatf.action_library import ActionRegistry
from aatf.metrics import EpisodeRecord

_FALLBACK: tuple[str, str] = (
    "Review and update Suricata rule signatures for this technique category; "
    "consult the ET PRO ruleset documentation for coverage recommendations.",
    "Unknown: assess false-positive risk empirically against your environment's "
    "baseline traffic before enabling.",
)

REMEDIATION_TABLE: dict[str, tuple[str, str]] = {
    "ET SCAN": (
        "Review ET SCAN ruleset thresholds; consider lowering scan detection sensitivity "
        "or narrowing source IP ranges. Verify scan interval thresholds match your "
        "environment's normal discovery traffic.",
        "High: network scan rules frequently trigger on legitimate discovery tools and "
        "asset-management probes.",
    ),
    "ET BRUTE_FORCE": (
        "Enable or tighten ET BRUTE_FORCE rules; set login-attempt thresholds to match "
        "your environment's expected authentication volume. Consider adding detection for "
        "slow-rate credential stuffing.",
        "Medium: high-frequency legitimate login systems (CI/CD, SSO agents) may trigger "
        "brute-force rules.",
    ),
    "ET EXPLOIT": (
        "Activate and tune ET EXPLOIT signatures for the specific service version targeted. "
        "Ensure vulnerability scanner traffic is excluded from triggering these rules.",
        "Low: exploit signatures are highly specific; false positives are rare but possible "
        "on unusual protocol implementations.",
    ),
    "ET DNS": (
        "Enable ET DNS rules for zone transfer and subdomain enumeration; tune query-rate "
        "thresholds to your resolver's legitimate query volume.",
        "Medium: high-volume DNS resolvers and CDN prefetching can generate patterns "
        "resembling DNS reconnaissance.",
    ),
    "ET POLICY": (
        "Review ET POLICY rules for data-exfiltration patterns; enable DNS and HTTP "
        "exfiltration signatures and set volume thresholds appropriate to baseline traffic.",
        "High: policy rules covering large data transfers can trigger on legitimate backup "
        "or sync traffic.",
    ),
    "ET TROJAN": (
        "Enable ET TROJAN signatures covering HTTP-based C2 patterns; update rule sets "
        "frequently as evasion techniques evolve rapidly in this category.",
        "Low: trojan signatures are narrow; false positives are uncommon but possible with "
        "custom internal tooling using similar HTTP patterns.",
    ),
    "ET WEB_CLIENT": (
        "Enable ET WEB_CLIENT rules for XSS probe patterns; ensure your web application "
        "firewall is configured to complement Suricata detections.",
        "Medium: legitimate security scanners and browser automation tools may trigger "
        "XSS detection rules.",
    ),
    "ET WEB_SERVER": (
        "Enable ET WEB_SERVER directory scan and SQLi probe signatures; tune to exclude "
        "known-safe scanner IPs and internal penetration testing ranges.",
        "Medium: automated vulnerability scanners and web crawlers frequently trigger "
        "directory scan rules.",
    ),
}


@dataclass(frozen=True)
class ActionExplanation:
    action_id: str
    suricata_category: str
    description: str
    evasion_count: int
    total_count: int
    evasion_rate: float
    remediation: str
    false_positive_risk: str


def explain_evasions(
    records: list[EpisodeRecord],
    registry: ActionRegistry,
) -> list[ActionExplanation]:
    counts: dict[str, list[int]] = {}  # {action_id: [evasion_count, total_count]}
    for record in records:
        for step in record.steps:
            if step.action_id not in counts:
                counts[step.action_id] = [0, 0]
            counts[step.action_id][1] += 1
            if not step.detected:
                counts[step.action_id][0] += 1

    result: list[ActionExplanation] = []
    for action_id, (evaded, total) in counts.items():
        if evaded == 0:
            continue
        defn = registry.get_action(action_id)  # KeyError propagates (A2)
        remediation, fpr = REMEDIATION_TABLE.get(defn.suricata_category, _FALLBACK)
        result.append(ActionExplanation(
            action_id=action_id,
            suricata_category=defn.suricata_category,
            description=defn.description,
            evasion_count=evaded,
            total_count=total,
            evasion_rate=evaded / total,
            remediation=remediation,
            false_positive_risk=fpr,
        ))

    return sorted(result, key=lambda x: (-x.evasion_rate, x.action_id))
```

---

## Test Structure (tests/test_explainability.py)

```python
# Helpers
def _step(action_id: str, detected: bool) -> StepRecord: ...
def _ep(*steps) -> EpisodeRecord: ...

# Stub registry helper
def _registry(*action_defs: ActionDefinition) -> ActionRegistry: ...

# US1 — container
def test_c001_field_access(): ...
def test_c002_immutable(): ...
def test_c003_importable(): ...  # covered by module-level import

# US2 — evasion analysis
def test_c004_ranking(): ...
def test_c005_tiebreak_by_action_id(): ...
def test_c006_fully_detected_excluded(): ...
def test_c007_empty_records(): ...
def test_c008_all_detected_empty(): ...
def test_c009_registry_lookup(): ...

# US3 — remediation hints
@pytest.mark.parametrize("category", [...8 categories...])
def test_c010_known_category_non_empty(category): ...
def test_c011_unknown_category_fallback(): ...
def test_c012_same_category_identical_strings(): ...
```

C-010 uses `@pytest.mark.parametrize` over all 8 known categories — counts as one
contract (12 total), but produces 8 parametrized test cases in the suite.

---

## Baseline and target

| Metric | Value |
|---|---|
| Baseline (post-F21) | 257 passed, 4 skipped, 6 failed |
| New test cases | 12 (C-001..C-012); C-010 parametrized × 8 = 8 extra passes |
| Target | ≥269 passed, 4 skipped, 6 failed |

The 6 pre-existing failures are Docker isolation tests — unchanged.

---

## Story completion order

| Story | Contracts | Blocking? |
|---|---|---|
| US1 (P1) ActionExplanation | C-001, C-002, C-003 | Yes — all other stories import it |
| US2 (P2) Evasion analysis | C-004..C-009 | Yes — US3 tests assume a result list |
| US3 (P3) Remediation hints | C-010..C-012 | No — verifies remediation strings only |

---

## Complexity Tracking

No constitution violations. Table is empty.
