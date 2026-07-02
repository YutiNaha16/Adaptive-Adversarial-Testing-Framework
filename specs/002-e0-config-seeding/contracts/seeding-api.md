# Contract: Seeding API

**Module**: `src/aatf/seeding.py`
**Feature**: 002-e0-config-seeding

---

## Public surface

### `seed_everything(seed: int) -> None`

Seeds all random-number generators in the process from a single integer.
**This is the ONLY permitted seeding call in the entire codebase** (FR-012).

**Arguments**
- `seed` — non-negative integer. Negative values and zero are accepted (Python random and NumPy accept any integer as seed); no guard is applied.

**Returns**: `None`

**Raises**: Nothing. If `torch` is not importable, that branch is silently skipped.

**Behaviour** (in order):
1. `random.seed(seed)` — seeds Python's built-in `random` module global state.
2. `numpy.random.seed(seed)` — seeds NumPy's legacy global `RandomState`.
3. Attempt `import torch`; if successful: `torch.manual_seed(seed)`. If `ImportError`, skip silently.

**Idempotency**: Calling `seed_everything(42)` twice resets all RNGs to the same state as the first call — subsequent draws are identical to draws after the first call.

---

## Boundary constraint (FR-012)

No module in `src/aatf/` other than `seeding.py` may call:
- `random.seed()`
- `numpy.random.seed()` or `numpy.random.default_rng()` for global-state seeding
- `torch.manual_seed()`

This is enforced by `tests/test_seeding.py::test_no_direct_seeding_calls` — a static-analysis test that greps `src/aatf/` for these patterns and asserts none exist outside `seeding.py`.

---

## Test contract (`tests/test_seeding.py`)

| Test | Scenario | Expected |
|------|----------|----------|
| `test_seed_produces_deterministic_random` | seed(42) twice → random.random() | Both draws equal |
| `test_seed_produces_deterministic_numpy` | seed(42) twice → numpy.random.random() | Both draws equal |
| `test_different_seeds_differ` | seed(42) vs seed(99) → random.random() | Draws not equal |
| `test_reseed_resets_state` | seed(42), draw, seed(42) → draw again | Second draw equals first |
| `test_torch_absent_no_error` | torch not importable (mock) → seed(42) | Completes without error |
| `test_no_direct_seeding_calls` | Grep src/aatf/ for seed patterns | Zero matches outside seeding.py |
