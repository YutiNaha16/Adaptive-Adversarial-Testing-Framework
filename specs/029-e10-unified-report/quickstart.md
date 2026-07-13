# Quickstart & Integration Scenarios: Unified Blind-Spot Report (F29)

**Date**: 2026-07-13
**Branch**: `029-e10-unified-report`

---

## Minimal Integration Scenario

```python
# Existing call — unchanged, no ML section appears (all anomaly_score=0.0 by default):
generate_report(records, registry, "/tmp/report.md")

# With ML scores present — ML section auto-appears:
# (records populated by DQNAttacker + MLAnomalyDefence run)
generate_report(records_with_anomaly, registry, "/tmp/report_ml.md")
```

No import changes required at call sites. `generate_report` signature is identical.

---

## Test Fixture Patterns

### C-001: No ML section when all anomaly_score = 0.0

```python
from aatf.episode import EpisodeRecord, StepRecord
from aatf.action_library import REGISTRY

step = StepRecord(action_id="tcp_port_scan", detected=False, stage_progress=0, reward=1.0)
# anomaly_score defaults to 0.0
ep = EpisodeRecord(attacker_class="LinUCBAttacker", seed=42, total_reward=1.0, steps=[step])
rendered = generate_report([ep], REGISTRY, tmp_path / "report.md")
assert "ML Anomaly Defence Analysis" not in rendered
```

### C-002: ML section appears when any anomaly_score > 0

```python
step = StepRecord(action_id="tcp_port_scan", detected=False, stage_progress=0, reward=1.0,
                  anomaly_score=0.5)
ep = EpisodeRecord(attacker_class="DQNAttacker", seed=42, total_reward=1.0, steps=[step])
rendered = generate_report([ep], REGISTRY, tmp_path / "report.md")
assert "ML Anomaly Defence Analysis" in rendered
assert "CAE" in rendered or "0.5000" in rendered  # CAE = mean-of-sums = 0.5
```

### C-003: Evasive table ranks ascending by mean_anomaly_undetected

```python
step_a = StepRecord(action_id="tcp_port_scan", detected=False, stage_progress=0, reward=1.0,
                    anomaly_score=0.1)
step_b = StepRecord(action_id="udp_sweep", detected=False, stage_progress=0, reward=1.0,
                    anomaly_score=0.4)
ep = EpisodeRecord(attacker_class="DQNAttacker", seed=42, total_reward=2.0, steps=[step_a, step_b])
rendered = generate_report([ep], REGISTRY, tmp_path / "report.md")
# tcp_port_scan (0.1) should appear before udp_sweep (0.4) in the evasive table
tcp_pos = rendered.index("tcp_port_scan")
udp_pos = rendered.index("udp_sweep")
assert tcp_pos < udp_pos  # lower score = higher evasiveness = appears first
```

### C-004: Suspicious table ranks descending by mean_anomaly_all

```python
step_a = StepRecord(action_id="tcp_port_scan", detected=True, stage_progress=0, reward=-1.0,
                    anomaly_score=0.9)
step_b = StepRecord(action_id="udp_sweep", detected=True, stage_progress=0, reward=-1.0,
                    anomaly_score=0.2)
ep = EpisodeRecord(attacker_class="DQNAttacker", seed=42, total_reward=-2.0,
                   steps=[step_a, step_b])
rendered = generate_report([ep], REGISTRY, tmp_path / "report.md")
# tcp_port_scan (0.9) should appear before udp_sweep (0.2) in the suspicious table
tcp_pos = rendered.index("tcp_port_scan")
udp_pos = rendered.index("udp_sweep")
assert tcp_pos < udp_pos
```

### C-005: Retraining recommendation — category below threshold listed; above threshold → no-gap

```python
# Below threshold (0.25 < 0.3): category should appear in recommendation
step_low = StepRecord(action_id="tcp_port_scan", detected=False, stage_progress=0, reward=1.0,
                      anomaly_score=0.25)
ep_low = EpisodeRecord(attacker_class="DQNAttacker", seed=42, total_reward=1.0, steps=[step_low])
rendered_low = generate_report([ep_low], REGISTRY, tmp_path / "report_low.md")
assert "ET SCAN" in rendered_low  # tcp_port_scan's suricata_category

# Above threshold (0.7 > 0.3): no-gap message
step_high = StepRecord(action_id="tcp_port_scan", detected=False, stage_progress=0, reward=1.0,
                       anomaly_score=0.7)
ep_high = EpisodeRecord(attacker_class="DQNAttacker", seed=42, total_reward=1.0, steps=[step_high])
rendered_high = generate_report([ep_high], REGISTRY, tmp_path / "report_high.md")
assert "No ML gap identified" in rendered_high
```

---

## Backward-Compatibility Smoke Test

All existing `test_report.py` tests pass without modification because:
1. They use `EpisodeRecord` with `StepRecord` instances that have `anomaly_score=0.0` (default).
2. `_has_ml_scores` returns `False` → `ml_summary` is `None` → template `{% if ml_summary %}` is skipped.
3. The rendered output is byte-identical to the pre-F29 output for the same inputs.

---

## Commands

```bash
# Activate venv
source /home/yuti/Adaptive-Adversarial-Testing-Framework/.venv/bin/activate
cd /home/yuti/Adaptive-Adversarial-Testing-Framework

# Run only new F29 tests
pytest tests/test_unified_report.py -v

# Run full suite (target: ≥350 passed, 0 failed)
cd src && pytest

# Lint
ruff check src/aatf/report.py tests/test_unified_report.py
```
