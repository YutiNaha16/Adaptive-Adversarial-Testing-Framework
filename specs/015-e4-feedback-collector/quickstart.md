# Quickstart: Feedback Collector (F15)

**Feature**: `015-e4-feedback-collector` | **Date**: 2026-07-10

## Minimal usage

```python
from aatf.context_vector import EpisodeState
from aatf.feedback import collect_feedback, FeedbackResult
from aatf.reward import compute_reward

# Fresh episode
state = EpisodeState()

# After action executor runs "recon-syn-scan" and Suricata fires an alert:
result: FeedbackResult = collect_feedback(
    episode_state=state,
    action_id="recon-syn-scan",
    alert_fired=True,
    category="ET SCAN",
)
reward = compute_reward(detected=result.detected, stage_progress=result.stage_progress)
# result.detected = True, result.stage_progress = True (entry point unlocks successors)
# reward = -1.0 (detection penalty overrides progress)
```

## Undetected action with progress

```python
result = collect_feedback(state, "recon-syn-scan", alert_fired=False)
# result.detected = False, result.stage_progress = True
reward = compute_reward(result.detected, result.stage_progress)
# reward = +1.0
```

## Undetected, no progress (terminal node or all successors already done)

```python
result = collect_feedback(state, "lateral-move-smb", alert_fired=False)
# result.detected = False, result.stage_progress = False
reward = compute_reward(result.detected, result.stage_progress)
# reward = -0.1
```

## Custom attack graph (for tests)

```python
from aatf.attack_graph import AttackGraph

mini_graph = AttackGraph(
    entry_points=frozenset({"recon-syn-scan"}),
    edges={"recon-syn-scan": frozenset({"exploit-vsftpd-backdoor"})},
)
result = collect_feedback(state, "recon-syn-scan", True, attack_graph=mini_graph)
```

## Inspecting EpisodeState after feedback

```python
state = EpisodeState()
collect_feedback(state, "recon-syn-scan", True, category="ET SCAN")
collect_feedback(state, "exploit-vsftpd-backdoor", False)

print(state.step)                           # 2
print(state.alert_history)                  # [True, False]
print(state.detection_history)              # {"recon-syn-scan": [True], "exploit-vsftpd-backdoor": [False]}
print(state.completed_actions)              # {"recon-syn-scan", "exploit-vsftpd-backdoor"}
print(state.fired_categories)              # {"ET SCAN"}
```
