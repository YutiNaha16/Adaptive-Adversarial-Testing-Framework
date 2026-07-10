# Data Model: Reward Function (F14)

## Entities

### RewardConstants

Module-level float constants — the single source of truth for all Phase 1 reward values.

| Constant | Value | Condition |
|----------|-------|-----------|
| `REWARD_DETECTED` | −1.0 | `detected=True` (any `stage_progress`) |
| `REWARD_PROGRESS` | +1.0 | `detected=False` and `stage_progress=True` |
| `REWARD_STALL` | −0.1 | `detected=False` and `stage_progress=False` |

---

## Truth Table

| detected | stage_progress | compute_reward() | Constant |
|----------|---------------|-----------------|----------|
| True | False | −1.0 | REWARD_DETECTED |
| True | True | −1.0 | REWARD_DETECTED |
| False | True | +1.0 | REWARD_PROGRESS |
| False | False | −0.1 | REWARD_STALL |

All four input combinations are covered. Three distinct output values. Detection always wins.

---

## Source File

`src/aatf/reward.py` — single file, no imports required.
