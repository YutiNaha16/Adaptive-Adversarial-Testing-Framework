# Quickstart: Report Generator (F24)

**Date**: 2026-07-11  
**Module**: `aatf.report`

## Minimal usage

```python
from pathlib import Path
from aatf.action_library import REGISTRY
from aatf.metrics import EpisodeRecord
from aatf.episode import StepRecord
from aatf.report import generate_report

# Build episode records (normally from run_episode / run_multi_seed)
steps = [
    StepRecord(action_id="ssh_brute_force", detected=False, stage_progress=1, reward=1.0),
    StepRecord(action_id="tcp_port_scan",   detected=True,  stage_progress=0, reward=-1.0),
]
ep = EpisodeRecord(attacker_class="LinUCBAttacker", seed=42, steps=steps,
                   total_reward=0.0, completed=False, episode_index=0)

output = Path("outputs/report.md")
output.parent.mkdir(parents=True, exist_ok=True)

md = generate_report([ep], REGISTRY, output)
print(md[:500])
```

**Expected output** (abridged):

```markdown
# Blind-Spot Report

## Run Metadata
- **Attacker**: LinUCBAttacker
- **Seeds**: 42
- **Episodes**: 1
- **Generated**: 2026-07-11T...

## Headline Metrics
| Metric | Value |
|--------|-------|
| Detection Rate | 50.0% |
...

## Blind Spots
| Action | Category | Evasion Rate | Evaded | Total | Remediation |
|--------|----------|--------------|--------|-------|-------------|
| ssh_brute_force | ET BRUTE_FORCE | 100.0% | 1 | 1 | Enable or tighten... |
```

---

## Deterministic usage (for tests / CI)

```python
from datetime import UTC, datetime

FIXED_TS = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

md1 = generate_report(records, REGISTRY, "outputs/run1.md", generated_at=FIXED_TS)
md2 = generate_report(records, REGISTRY, "outputs/run2.md", generated_at=FIXED_TS)

assert md1 == md2  # byte-for-byte identical
```

---

## Integration with F21 multi-seed runs

```python
from aatf.statistics import run_multi_seed

all_records = run_multi_seed(runner, seeds=[0, 1, 2, 3, 4])
md = generate_report(all_records, REGISTRY, "outputs/multiseed_report.md")
```

The metadata section will list all 5 seeds; metrics aggregate across all episodes.

---

## Error handling

```python
# Parent directory must exist — generate_report does NOT mkdir
Path("missing_dir/report.md")  # → FileNotFoundError if missing_dir absent

# Pass an existing parent:
out = Path("outputs") / "report.md"
out.parent.mkdir(exist_ok=True)
generate_report(records, REGISTRY, out)
```

---

## Running the tests

```bash
cd /home/yuti/Adaptive-Adversarial-Testing-Framework
source .venv/bin/activate
cd src && pytest ../tests/test_report.py -v
```

Target: 10 new tests (C-001..C-010) all green, overall suite ≥286 passed.
