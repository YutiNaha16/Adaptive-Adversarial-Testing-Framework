# Quickstart: Explainability Engine (F23)

**Date**: 2026-07-11  
**Module**: `aatf.explainability`

## Minimal usage

```python
from aatf.action_library import REGISTRY
from aatf.explainability import explain_evasions
from aatf.metrics import EpisodeRecord
from aatf.episode import StepRecord

# Build episode records (normally from run_episode / run_multi_seed)
steps_ep1 = [
    StepRecord(action_id="ssh_brute_force_slow", detected=False,
               stage_progress=1, reward=1.0),
    StepRecord(action_id="tcp_syn_scan", detected=True,
               stage_progress=0, reward=-1.0),
    StepRecord(action_id="ssh_brute_force_slow", detected=False,
               stage_progress=1, reward=1.0),
]
ep1 = EpisodeRecord(attacker_class="LinUCBAttacker", seed=42,
                    steps=steps_ep1, total_reward=1.0,
                    completed=False, episode_index=0)

# Get ranked explanations
explanations = explain_evasions([ep1], REGISTRY)

for ex in explanations:
    print(f"{ex.action_id}: {ex.evasion_rate:.0%} evasion rate ({ex.evasion_count}/{ex.total_count})")
    print(f"  Category: {ex.suricata_category}")
    print(f"  Remediation: {ex.remediation}")
    print(f"  FP risk: {ex.false_positive_risk}")
    print()
```

**Expected output** (abridged):

```
ssh_brute_force_slow: 100% evasion rate (2/2)
  Category: ET BRUTE_FORCE
  Remediation: Enable or tighten ET BRUTE_FORCE rules; set login-attempt
               thresholds to match your environment's expected authentication volume...
  FP risk: Medium: high-frequency legitimate login systems (CI/CD, SSO agents)...
```

Note: `tcp_syn_scan` does not appear because it was detected on its only step (evasion_rate = 0).

---

## Integration with F21 (multi-seed runs)

```python
from aatf.statistics import run_multi_seed
# ... define runner(seed) -> list[EpisodeRecord]

all_records = run_multi_seed(runner, seeds=[0, 1, 2, 3, 4])
explanations = explain_evasions(all_records, REGISTRY)
```

Passing multi-seed records aggregates tallies across all seeds, giving a more stable
evasion rate estimate.

---

## Accessing individual fields

```python
ex = explanations[0]

assert isinstance(ex.evasion_count, int)     # steps evaded
assert isinstance(ex.total_count, int)        # total steps for this action
assert 0.0 < ex.evasion_rate <= 1.0          # float in (0, 1]
assert len(ex.remediation) > 0               # always non-empty
assert len(ex.false_positive_risk) > 0       # always non-empty

# Immutable — this raises FrozenInstanceError:
# ex.evasion_count = 0
```

---

## Running the tests

```bash
cd /home/yuti/Adaptive-Adversarial-Testing-Framework
source .venv/bin/activate
cd src && pytest ../tests/test_explainability.py -v
```

Baseline target: 12 new tests (C-001..C-012) all green, overall suite ≥269 passed.
