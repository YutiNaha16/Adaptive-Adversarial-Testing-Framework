# Quickstart: Core Data Contracts

**Feature**: 003-e0-core-contracts | **Date**: 2026-07-02

---

## Prerequisites

F01 + F02 complete: `.venv` exists with Pydantic V2 installed, `make test` passes 29 tests.

---

## Scenario 1 — Construct all five types (happy path)

```python
from datetime import datetime, UTC
from aatf.contracts import Action, DetectionResult, ContextVector, EpisodeRecord, RunManifest

# Action
action = Action(
    action_id="act-001",
    category="scan",
    parameters={"rate": 10, "ports": [22, 80]},
    timestamp=datetime.now(UTC),
)

# DetectionResult — binary Suricata mode
detection = DetectionResult(
    alerted=True,
    rule_ids=["SID:2100498"],
    anomaly_score=0.0,
    coverage="covered",
)

# ContextVector
ctx = ContextVector(
    alert_history=[0.0, 0.0, 1.0],
    attack_progress=0.25,
    current_stage=1,
    technique_detection_rates={"scan": 0.33},
    time_since_last_alert=12.5,
)

# EpisodeRecord
record = EpisodeRecord(
    episode_id="ep-001",
    step=0,
    action=action,
    detection=detection,
    reward=-1.0,
    context_before=ctx,
    context_after=ctx,
    timestamp=datetime.now(UTC),
)

print("All five types constructed successfully")
```

---

## Scenario 2 — DetectionResult: binary, continuous, and both modes

```python
# Phase 1 — binary Suricata alert
binary = DetectionResult(
    alerted=True, rule_ids=["SID:2100498"], anomaly_score=0.0, coverage="covered"
)

# Phase 2 — continuous ML score only
continuous = DetectionResult(
    alerted=False, rule_ids=[], anomaly_score=0.73, coverage="covered"
)

# Hybrid — both simultaneously (binary alert + continuous score)
hybrid = DetectionResult(
    alerted=True, rule_ids=["SID:2100498"], anomaly_score=0.91, coverage="covered"
)

# True blind spot — no rule covers this behaviour
blind_spot = DetectionResult(
    alerted=False, rule_ids=[], anomaly_score=0.0, coverage="uncovered"
)

print(f"binary alerted={binary.alerted}, score={binary.anomaly_score}")
print(f"continuous alerted={continuous.alerted}, score={continuous.anomaly_score}")
print(f"hybrid SIDs={hybrid.rule_ids}, score={hybrid.anomaly_score}")
print(f"blind_spot coverage={blind_spot.coverage}")
```

---

## Scenario 3 — EpisodeRecord JSONL round-trip

```python
import json
from pathlib import Path
from aatf.contracts import EpisodeRecord

# Serialise to JSONL line
line = json.dumps(record.model_dump(mode="json"))

# Write to JSONL file
log_path = Path("/tmp/episode_log.jsonl")
log_path.write_text(line + "\n")

# Read back and reconstruct
restored = EpisodeRecord.model_validate(json.loads(log_path.read_text().strip()))

assert restored == record          # lossless round-trip
assert restored.episode_id == "ep-001"
assert restored.action.category == "scan"
print("JSONL round-trip: OK")
```

---

## Scenario 4 — Validation catches bad inputs

```python
from pydantic import ValidationError
from aatf.contracts import DetectionResult, ContextVector

# Bad anomaly_score
try:
    DetectionResult(alerted=False, rule_ids=[], anomaly_score=1.5, coverage="uncovered")
except ValidationError as e:
    print(f"anomaly_score=1.5 rejected: {e.error_count()} error(s)")

# Bad current_stage
try:
    ContextVector(
        alert_history=[0.0],
        attack_progress=0.5,
        current_stage=4,          # out of range [0,3]
        technique_detection_rates={},
        time_since_last_alert=0.0,
    )
except ValidationError as e:
    print(f"current_stage=4 rejected: {e.error_count()} error(s)")

# Bad dict value in technique_detection_rates
try:
    ContextVector(
        alert_history=[0.0],
        attack_progress=0.0,
        current_stage=0,
        technique_detection_rates={"ssh": 1.7},   # value > 1.0
        time_since_last_alert=0.0,
    )
except ValidationError as e:
    print(f"technique_detection_rates ssh=1.7 rejected: {e.error_count()} error(s)")
```

---

## Scenario 5 — RunManifest reads an F02 manifest file

```python
import json
from pathlib import Path
from aatf.contracts import RunManifest
from aatf.config import load_config
from aatf.manifest import write_manifest

# Write a real manifest via F02
cfg = load_config("config.yaml")
manifest_path = write_manifest(cfg, cfg.seed)

# Read and validate via F03 RunManifest
data = json.loads(manifest_path.read_text())
manifest = RunManifest.model_validate(data)

assert manifest.seed == cfg.seed
assert "pydantic" in manifest.packages
print(f"RunManifest.seed={manifest.seed}, git={manifest.git_commit[:7]}")
```

---

## Acceptance gate checklist

- [ ] SC-001: All five types importable from `aatf.contracts`, construct without error
- [ ] SC-002: `DetectionResult` accepts binary, continuous, and both modes simultaneously
- [ ] SC-003: `EpisodeRecord` JSONL round-trip produces field-for-field equal object
- [ ] SC-004: Out-of-range floats and wrong types raise `ValidationError` at construction
- [ ] SC-005: `contracts.py` imports nothing from defence, attacker, or loop modules
