# Research: Reward Function (F14)

## Decision 1: Return type — float, not numpy scalar

- **Decision**: `float` (Python native)
- **Rationale**: No numpy dependency needed for a 3-branch lookup; callers (F15, F16) can widen to numpy when needed
- **Alternatives considered**: `np.float32` — unnecessary dependency for a pure scalar; `float64` — same as float in CPython

## Decision 2: Named constants over magic numbers

- **Decision**: `REWARD_DETECTED = -1.0`, `REWARD_PROGRESS = +1.0`, `REWARD_STALL = -0.1` at module level
- **Rationale**: Constitution VI requires reward to live in one place and be unit-tested against worked examples; named constants make test assertions self-documenting and allow Phase 2 to extend without hunting magic numbers
- **Alternatives considered**: Enum (heavier, no benefit for 3 scalars); dataclass (same); inline literals (violates single-source principle)

## Decision 3: detection takes priority over progress

- **Decision**: `if detected` is the first branch — `stage_progress=True` is ignored when `detected=True`
- **Rationale**: Operationally, a detected action is a failed action regardless of graph position; rewarding progress while being detected would send contradictory signals to the learner
- **Alternatives considered**: Additive reward (`detected * -1 + progress * 1`) — creates ambiguous combined signal; rejected
