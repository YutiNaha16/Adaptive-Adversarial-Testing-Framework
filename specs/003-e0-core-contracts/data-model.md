# Data Model: Core Data Contracts

**Feature**: 003-e0-core-contracts | **Date**: 2026-07-02

All five types are Pydantic V2 `BaseModel` with `ConfigDict(frozen=True)`.

---

## Action

Represents one step the attacker takes. Created by the attacker brain; consumed by the
executor and logged inside `EpisodeRecord`.

| Field | Type | Validation | Notes |
|-------|------|-----------|-------|
| `action_id` | `str` | non-empty | Caller-assigned unique identifier (UUID or sequential) |
| `category` | `str` | non-empty | Technique category: `"scan"`, `"brute"`, `"exfil"`, etc. |
| `parameters` | `dict[str, Any]` | any dict | Permissive — specific actions validate their own params (F07) |
| `timestamp` | `datetime` | timezone-aware UTC | When the action was chosen |

**Relationships**: Nested inside `EpisodeRecord.action`.

---

## DetectionResult

The defence's verdict on one action. The architectural key to Principle III — this single
type serves both Suricata (binary) and ML detector (continuous) without schema changes.

| Field | Type | Validation | Notes |
|-------|------|-----------|-------|
| `alerted` | `bool` | — | True if any rule/detector fired |
| `rule_ids` | `list[str]` | any list, may be empty | Responsible Suricata SIDs: `["SID:2100498"]`; empty when `alerted=False` or ML-only mode |
| `anomaly_score` | `float` | `ge=0.0, le=1.0` | ML anomaly score; 0.0 in Phase 1 Suricata-only mode |
| `coverage` | `Literal["covered", "uncovered", "unknown"]` | one of three values | `"covered"` = a rule exists for this behaviour; `"uncovered"` = no rule covers it (true blind spot); `"unknown"` = coverage not determinable |

**Valid construction modes**:
- Binary (Suricata): `alerted=True, rule_ids=["SID:2100498"], anomaly_score=0.0, coverage="covered"`
- Continuous (ML): `alerted=True, rule_ids=[], anomaly_score=0.87, coverage="covered"`
- Undetected: `alerted=False, rule_ids=[], anomaly_score=0.0, coverage="uncovered"`
- Both simultaneously: `alerted=True, rule_ids=["SID:1234"], anomaly_score=0.91, coverage="covered"`

**Relationships**: Nested inside `EpisodeRecord.detection`.

---

## ContextVector

The observable state the attacker sees before choosing each action. Contains all four
proposal (§7.4) signal families plus the explicit `current_stage` field added in clarify.

| Field | Type | Validation | Notes |
|-------|------|-----------|-------|
| `alert_history` | `list[Annotated[float, Field(ge=0.0, le=1.0)]]` | each element in [0.0, 1.0] | Recent per-step detection flags: 0.0 = no alert, 1.0 = alert fired; Phase 2 may use intermediate scores |
| `attack_progress` | `float` | `ge=0.0, le=1.0` | Fraction of the 4-stage campaign completed |
| `current_stage` | `int` | `ge=0, le=3` | Current attack graph stage: 0=recon, 1=initial access, 2=lateral movement, 3=exfiltration |
| `technique_detection_rates` | `dict[str, Annotated[float, Field(ge=0.0, le=1.0)]]` | each value in [0.0, 1.0] | Per-technique rolling detection rate keyed by category string |
| `time_since_last_alert` | `float` | `ge=0.0` | Seconds since the last alert fired; 0.0 at episode start |

**Relationships**: Nested twice inside `EpisodeRecord` as `context_before` and `context_after`.

---

## EpisodeRecord

One complete logged step. Written as a JSONL line per step; consumed by the offline
analysis pipeline (evaluator, explainability engine) without re-running the lab.

| Field | Type | Validation | Notes |
|-------|------|-----------|-------|
| `episode_id` | `str` | non-empty | Identifies which episode this step belongs to |
| `step` | `int` | `ge=0` | Step index within the episode (0-based) |
| `action` | `Action` | valid `Action` | The action the attacker chose this step |
| `detection` | `DetectionResult` | valid `DetectionResult` | The defence's verdict this step |
| `reward` | `float` | any finite float | Computed by the reward function (F14) |
| `context_before` | `ContextVector` | valid `ContextVector` | State before the action was taken |
| `context_after` | `ContextVector` | valid `ContextVector` | State after detection result received |
| `timestamp` | `datetime` | timezone-aware UTC | When this step was logged |

**JSONL round-trip**: `record.model_dump(mode="json")` → `json.dumps()` → write;
read → `json.loads()` → `EpisodeRecord.model_validate(data)` → equal object.

**Relationships**: Aggregates `Action`, `DetectionResult`, and two `ContextVector` instances.

---

## RunManifest

Typed read-side validation for the F02 provenance JSON. Used by the offline analysis
pipeline to safely parse and validate a stored manifest file.

| Field | Type | Validation | Notes |
|-------|------|-----------|-------|
| `seed` | `int` | `ge=0` | Global RNG seed used for this run |
| `python_version` | `str` | non-empty | e.g. `"3.12.3"` |
| `packages` | `dict[str, str]` | any dict | Package name → version string |
| `suricata_version` | `str` | non-empty | `"unknown"` until E1 fills it |
| `ruleset_version` | `str` | non-empty | `"unknown"` until E1 fills it |
| `git_commit` | `str` | non-empty | Full SHA or `"unknown"` |
| `config_snapshot` | `dict[str, Any]` | any dict | Full `ExperimentConfig.model_dump()` output |
| `timestamp` | `str` | non-empty | ISO 8601 string (stored as str to match F02 write-side) |

**Write-side**: `aatf.manifest.write_manifest()` (F02) — field names are identical.
**Read-side**: `RunManifest.model_validate(json.loads(path.read_text()))` — this type.

---

## Type relationships

```
EpisodeRecord
├── action: Action
├── detection: DetectionResult
├── context_before: ContextVector
└── context_after: ContextVector

RunManifest  (standalone — validated from F02 manifest JSON)
```
