# Quickstart: Configuration & Seed Management

**Feature**: 002-e0-config-seeding | **Date**: 2026-07-02

---

## Prerequisites

F01 scaffold is complete: `.venv` exists with `pip install -e .` done, `make test` passes 4 tests.

---

## Scenario 1 — Happy path: load config, seed, write manifest

```bash
# 1. Create config.yaml at repo root
cat > config.yaml <<'EOF'
episodes: 100
seed: 42
output_dir: outputs/run_001
ruleset_path: /etc/suricata/rules
detection_threshold: 0.5
EOF

# 2. Run tests (all must pass after implementation)
make test
# Expected: 4 existing + new test_config + test_seeding + test_manifest tests pass

# 3. Verify make lint is clean
make lint

# 4. Run the entrypoint (still a stub — no change in F02)
make run
```

---

## Scenario 2 — Config validation catches bad input

```python
# In a Python REPL or test:
from aatf.config import load_config

# Missing required field
cfg = load_config("bad_config.yaml")
# → pydantic.ValidationError: 1 validation error for ExperimentConfig
#   seed: Field required [type=missing, ...]

# Wrong type
cfg = load_config("wrong_type.yaml")  # episodes: "ten"
# → pydantic.ValidationError: 1 validation error for ExperimentConfig
#   episodes: Input should be a valid integer, unable to parse string as an integer
```

---

## Scenario 3 — Seeding determinism

```python
from aatf.seeding import seed_everything
import random, numpy as np

seed_everything(42)
v1_rnd = random.random()
v1_np  = np.random.random()

seed_everything(42)           # re-seed
v2_rnd = random.random()
v2_np  = np.random.random()

assert v1_rnd == v2_rnd       # ✓ deterministic
assert v1_np  == v2_np        # ✓ deterministic
```

---

## Scenario 4 — Manifest provenance record

```python
from aatf.config import load_config
from aatf.manifest import write_manifest

cfg = load_config("config.yaml")
manifest_path = write_manifest(cfg, seed=cfg.seed)

print(manifest_path)
# → PosixPath('outputs/run_001/run_manifest_20260702T120000Z.json')

import json
manifest = json.loads(manifest_path.read_text())
assert manifest["seed"] == 42
assert manifest["suricata_version"] == "unknown"  # placeholder; E1 will fill
assert "pydantic" in manifest["packages"]
```

---

## Scenario 5 — Two runs produce two distinct manifests

```python
p1 = write_manifest(cfg, seed=42)
p2 = write_manifest(cfg, seed=42)
assert p1 != p2               # ✓ different timestamps → different filenames
assert p1.exists() and p2.exists()  # ✓ neither overwrites the other
```

---

## Acceptance gate checklist

After `make test` and `make lint` pass clean:

- [ ] SC-001: Changing `config.yaml` fields changes experiment config without code edits
- [ ] SC-002: Same seed → same random sequences (verified by `test_seeding.py`)
- [ ] SC-003: Timestamped manifest in output_dir; schema verified by `test_manifest.py`
- [ ] SC-004: Missing config field → clear error before experiment starts (`test_config.py`)
- [ ] SC-005: No direct seed calls outside `seeding.py` (verified by `test_no_direct_seeding_calls`)
