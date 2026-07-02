# Contracts API: aatf.contracts

**Feature**: 003-e0-core-contracts | **Module**: `src/aatf/contracts.py`

All five types are Pydantic V2 `BaseModel` with `ConfigDict(frozen=True)`.
Import: `from aatf.contracts import Action, DetectionResult, ContextVector, EpisodeRecord, RunManifest`

---

## Action

```python
Action(
    action_id: str,           # required, non-empty
    category: str,            # required, non-empty
    parameters: dict[str, Any],  # required, may be empty dict
    timestamp: datetime,      # required, timezone-aware UTC
) -> Action  # frozen
```

**Raises**: `ValidationError` if any required field is missing or wrong type.

### Test contracts

| # | Input | Expected |
|---|-------|----------|
| T-A1 | All fields valid | Instance with correct field values, frozen |
| T-A2 | `action_id` missing | `ValidationError` naming `action_id` |
| T-A3 | `category` missing | `ValidationError` naming `category` |
| T-A4 | `parameters={}` (empty dict) | Valid — no parameters is allowed |
| T-A5 | Attempt `action.category = "x"` after construction | `ValidationError` (frozen) |

---

## DetectionResult

```python
DetectionResult(
    alerted: bool,                                          # required
    rule_ids: list[str],                                    # required, may be empty
    anomaly_score: float,                                   # required, ge=0.0, le=1.0
    coverage: Literal["covered", "uncovered", "unknown"],  # required
) -> DetectionResult  # frozen
```

**Raises**: `ValidationError` if `anomaly_score` outside [0.0, 1.0] or `coverage` not one
of the three literals.

### Test contracts

| # | Input | Expected |
|---|-------|----------|
| T-DR1 | `alerted=True, rule_ids=["SID:2100498"], anomaly_score=0.0, coverage="covered"` | Valid binary mode |
| T-DR2 | `alerted=True, rule_ids=[], anomaly_score=0.87, coverage="covered"` | Valid continuous mode |
| T-DR3 | `alerted=True, rule_ids=["SID:1234"], anomaly_score=0.91, coverage="covered"` | Valid both modes simultaneously |
| T-DR4 | `alerted=False, rule_ids=[], anomaly_score=0.0, coverage="uncovered"` | Valid undetected |
| T-DR5 | `anomaly_score=1.5` | `ValidationError` naming `anomaly_score` |
| T-DR6 | `coverage="maybe"` | `ValidationError` naming `coverage` |
| T-DR7 | `anomaly_score=-0.1` | `ValidationError` naming `anomaly_score` |

---

## ContextVector

```python
ContextVector(
    alert_history: list[Annotated[float, Field(ge=0.0, le=1.0)]],  # required, elements in [0,1]
    attack_progress: float,            # required, ge=0.0, le=1.0
    current_stage: int,                # required, ge=0, le=3
    technique_detection_rates: dict[str, Annotated[float, Field(ge=0.0, le=1.0)]],  # required
    time_since_last_alert: float,      # required, ge=0.0
) -> ContextVector  # frozen
```

**Raises**: `ValidationError` if any element of `alert_history` outside [0.0, 1.0], any
value in `technique_detection_rates` outside [0.0, 1.0], `attack_progress` outside [0.0, 1.0],
`current_stage` outside [0, 3], or `time_since_last_alert` < 0.

### Test contracts

| # | Input | Expected |
|---|-------|----------|
| T-CV1 | All fields valid | Instance with correct field values, frozen |
| T-CV2 | `alert_history=[0.0, 1.0, 0.0]` | Valid |
| T-CV3 | `alert_history=[0.0, 1.5, 0.0]` | `ValidationError` (element 1.5 out of range) |
| T-CV4 | `attack_progress=-0.1` | `ValidationError` naming `attack_progress` |
| T-CV5 | `current_stage=4` | `ValidationError` naming `current_stage` |
| T-CV6 | `technique_detection_rates={"ssh": 1.7}` | `ValidationError` (dict value out of range) |
| T-CV7 | `time_since_last_alert=-1.0` | `ValidationError` naming `time_since_last_alert` |
| T-CV8 | `technique_detection_rates={}` (empty dict) | Valid — no techniques observed yet |

---

## EpisodeRecord

```python
EpisodeRecord(
    episode_id: str,             # required, non-empty
    step: int,                   # required, ge=0
    action: Action,              # required, valid Action
    detection: DetectionResult,  # required, valid DetectionResult
    reward: float,               # required, any finite float
    context_before: ContextVector,  # required, valid ContextVector
    context_after: ContextVector,   # required, valid ContextVector
    timestamp: datetime,         # required, timezone-aware UTC
) -> EpisodeRecord  # frozen
```

**JSONL round-trip**:
```python
data = record.model_dump(mode="json")
line = json.dumps(data)             # write to JSONL
restored = EpisodeRecord.model_validate(json.loads(line))  # read from JSONL
assert restored == record           # lossless
```

### Test contracts

| # | Input | Expected |
|---|-------|----------|
| T-ER1 | All fields valid | Instance with correct field values, frozen |
| T-ER2 | `step=-1` | `ValidationError` naming `step` |
| T-ER3 | `reward=999.9` | Valid (reward has no hard bound) |
| T-ER4 | `reward="high"` | `ValidationError` naming `reward` |
| T-ER5 | Full round-trip: `model_dump(mode="json")` → `model_validate()` | Reconstructed record equals original |
| T-ER6 | JSONL file: write 3 records, read back, reconstruct all | All 3 records equal originals |
| T-ER7 | `episode_id` missing | `ValidationError` naming `episode_id` |

---

## RunManifest

```python
RunManifest(
    seed: int,                    # required, ge=0
    python_version: str,          # required, non-empty
    packages: dict[str, str],     # required, may be empty
    suricata_version: str,        # required (may be "unknown")
    ruleset_version: str,         # required (may be "unknown")
    git_commit: str,              # required (may be "unknown")
    config_snapshot: dict[str, Any],  # required, may be empty
    timestamp: str,               # required, ISO 8601 string
) -> RunManifest  # frozen
```

**Round-trip with F02**: `RunManifest.model_validate(json.loads(manifest_path.read_text()))`
produces a valid `RunManifest` from any file written by `aatf.manifest.write_manifest()`.

### Test contracts

| # | Input | Expected |
|---|-------|----------|
| T-RM1 | All fields valid | Instance with correct field values, frozen |
| T-RM2 | `seed=-1` | `ValidationError` naming `seed` |
| T-RM3 | `suricata_version="unknown"` | Valid |
| T-RM4 | `packages={}` (empty) | Valid |
| T-RM5 | Round-trip: `model_dump(mode="json")` → `model_validate()` | Reconstructed manifest equals original |
| T-RM6 | Parse actual F02 manifest file | Valid `RunManifest` produced without error |

---

## Static isolation guard (FR-010)

```python
# test_contracts.py: test_no_forbidden_imports
import pathlib
source = pathlib.Path("src/aatf/contracts.py").read_text()
forbidden = ["aatf.defender", "aatf.attacker", "aatf.environment", "suricata"]
for term in forbidden:
    assert term not in source
```

**Total test contracts**: 5 (Action) + 7 (DetectionResult) + 8 (ContextVector) +
7 (EpisodeRecord) + 6 (RunManifest) + 1 (static isolation) = **34 test cases**.
