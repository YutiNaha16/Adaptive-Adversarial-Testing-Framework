# Data Model: Evaluator & Metrics (F20)

**Feature**: 020-e6-evaluator-metrics
**Date**: 2026-07-11

## Entities

### StepRecord (from F16 — aatf.episode, read-only)

| Field | Type | Description |
|-------|------|-------------|
| `action_id` | `str` | Identifier of the attack action taken |
| `detected` | `bool` | Whether the defence raised an alert |
| `stage_progress` | `bool` | Whether the attack graph advanced a stage |
| `reward` | `float` | Computed reward for this step |

**Constraints**: Frozen dataclass (immutable). Defined in `aatf.episode`; `aatf.metrics` imports it but does not own it.

---

### EpisodeRecord (new — aatf.metrics)

| Field | Type | Description |
|-------|------|-------------|
| `attacker_class` | `str` | Plain class name of the attacker used (e.g. `"LinUCBAttacker"`) |
| `seed` | `int` | RNG seed used for reproducibility tracking |
| `steps` | `list[StepRecord]` | Ordered sequence of steps taken in this episode |
| `total_reward` | `float` | Sum of `step.reward` across all steps |
| `completed` | `bool` | Whether the attack graph was fully traversed |
| `episode_index` | `int` | Position of this episode in the run sequence (0-based) |

**Constraints**: Frozen dataclass (immutable at field level). `steps` list should not be mutated after construction. `episode_index` is caller-assigned; metric functions use it only for the return value of `convergence_episodes`.

---

## Metric Function Signatures

| Function | Input | Output | Side Effects |
|----------|-------|--------|--------------|
| `detection_rate` | `list[EpisodeRecord]` | `float ∈ [0.0, 1.0]` | None |
| `robustness_score` | `list[EpisodeRecord], window: int` | `float ∈ [0.0, 1.0]` | None |
| `adaptation_gain` | `list[EpisodeRecord], list[EpisodeRecord]` | `float` (percentage points, unbounded) | None |
| `convergence_episodes` | `list[EpisodeRecord], threshold: float = 0.5, *, window: int = 5` | `int \| None` | None |

---

## Relationships

```
EpisodeRecord
  └── steps: list[StepRecord]   (0..∞ StepRecord objects)

detection_rate(list[EpisodeRecord])
  └── aggregates StepRecord.detected across all episodes

robustness_score(list[EpisodeRecord], window)
  └── delegates to detection_rate(records[-window:])

adaptation_gain(baseline_list, learner_list)
  └── computes detection_rate(baseline) - detection_rate(learner), ×100

convergence_episodes(list[EpisodeRecord], threshold, window)
  └── per-position detection_rate over trailing window slice
  └── returns EpisodeRecord.episode_index at first crossing
```

---

## Empty/Edge State Handling

| Scenario | `detection_rate` | `robustness_score` | `adaptation_gain` | `convergence_episodes` |
|----------|-----------------|-------------------|-------------------|----------------------|
| Empty records list | `0.0` | `0.0` | `0.0` | `None` |
| Records with no steps | `0.0` | `0.0` | depends on each list | `None` |
| window ≤ 0 | N/A | `0.0` | N/A | (not applicable — window ≥ 1 expected) |
| window > len(records) | N/A | uses all records | N/A | window naturally truncated by slice |
| one arg empty (adaptation_gain) | N/A | N/A | `dr(empty)=0.0` substituted | N/A |
