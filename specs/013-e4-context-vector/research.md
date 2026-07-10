# Research: Context Vector Builder (F13)

## Decision 1: EpisodeState mutability

- **Decision**: Plain `@dataclass` (not frozen) — fields mutate between steps in the episode loop
- **Rationale**: `completed_actions`, `detection_history`, `alert_history`, and `fired_categories` all grow as the episode progresses; freezing would force a new object every step
- **Alternatives considered**: Pydantic BaseModel (heavier, no benefit here); frozen dataclass + new instance each step (unnecessary allocation overhead)

## Decision 2: current_time injection for testability

- **Decision**: `build_context(episode_state, current_time: float | None = None)` — defaults to `time.time()` when None
- **Rationale**: Timing slot (`elapsed`) depends on wall clock; injecting it makes every test deterministic without monkeypatching
- **Alternatives considered**: Passing a clock callable; using `time.monotonic` — both equivalent; float injection is simpler

## Decision 3: alert_history ordering

- **Decision**: Slot 0 = oldest, slot N-1 = most recent; zero-padded at the front when history is short
- **Rationale**: Temporal order matters for RL; most-recent-last matches standard time-series convention; left-padding with zeros is natural ("no history yet = 0")
- **Alternatives considered**: Most-recent-first (reversed) — less intuitive for sequence models

## Decision 4: technique_history is lifetime rate, not windowed

- **Decision**: Rate = detected_count / total_executions over all history, never windowed
- **Rationale**: Simpler and sufficient for Phase 1 LinUCB; windowing adds a hyperparameter with no proven benefit at this stage
- **Alternatives considered**: Rolling K-window (adds K constant, complicates EpisodeState); exponential moving average (non-trivial to unit-test)

## Decision 5: action slot ordering

- **Decision**: `sorted(action_id for action_id in REGISTRY)` — lexicographic, deterministic
- **Rationale**: Consistent with attack_graph.py precedent (F09 used same ordering); ensures CONTEXT_DIM is stable across sessions
- **Alternatives considered**: REGISTRY insertion order (non-deterministic across Python versions)

## Decision 6: CONTEXT_DIM = 50 (fixed)

- **Decision**: 10 + 15 + 15 + 2 + 8 = 50; exposed as module constant
- **Rationale**: RL policy's input layer size must match; single constant prevents divergence between builder and policy
- **Alternatives considered**: Dynamic computation from parameters — more fragile; any parameter change silently changes RL input shape

## Decision 7: numpy array output, not list or Pydantic model

- **Decision**: Return `np.ndarray(shape=(50,), dtype=np.float32)`
- **Rationale**: RL frameworks (scikit-learn, PyTorch, stable-baselines3) all consume numpy arrays natively; no conversion overhead
- **Alternatives considered**: Python list (requires conversion downstream); torch.Tensor (adds torch dependency to a pure function)

## Decision 8: __post_init__ validation scope

- **Decision**: Validate `step >= 0`; validate all `completed_actions` ids exist in REGISTRY
- **Rationale**: These are programmer errors, not runtime conditions — fail early and loudly
- **Alternatives considered**: No validation (silently wrong context vector); Pydantic validators (overkill for two checks)
