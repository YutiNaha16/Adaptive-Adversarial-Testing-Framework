# Quickstart: Reward Function (F14)

## Import

```python
from aatf.reward import compute_reward, REWARD_DETECTED, REWARD_PROGRESS, REWARD_STALL
```

## Usage in feedback loop

```python
# After action execution and IDS polling:
detected: bool = defence.observe(action_id).detected
stage_progress: bool = len(graph.available_actions(completed_after) -
                           graph.available_actions(completed_before)) > 0

reward = compute_reward(detected=detected, stage_progress=stage_progress)
# reward is one of: -1.0, +1.0, -0.1
```

## All four input combinations

```python
compute_reward(True,  False)  # -1.0  — detected, no progress
compute_reward(True,  True)   # -1.0  — detected even though progress (detection wins)
compute_reward(False, True)   # +1.0  — evaded and advanced the kill chain
compute_reward(False, False)  # -0.1  — evaded but no new stages unlocked
```

## Logging the reward by name

```python
REWARD_NAMES = {
    REWARD_DETECTED: "DETECTED",
    REWARD_PROGRESS: "PROGRESS",
    REWARD_STALL: "STALL",
}
print(f"reward={reward} ({REWARD_NAMES[reward]})")
```
