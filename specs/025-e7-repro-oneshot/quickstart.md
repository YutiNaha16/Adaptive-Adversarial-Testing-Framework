# Quickstart: One-Command Reproducibility (F25)

**Date**: 2026-07-11
**Module**: `src/run_experiment.py`

## Minimal usage (lab pre-running)

```bash
# One-time setup
make setup

# Optional: start Docker lab for live traffic
make lab-up

# Run the full experiment
make run
```

Expected output:
```
Adaptive Adversarial Testing Framework
======================================
Attacker : RandomAttacker
Episodes : 100
Seed     : 42
--------------------------------------
Running 100 episodes...
--------------------------------------
Detection Rate   : 0.00
Robustness Score : 0.00
Report written   : outputs/run_001/report_20260711T120000.md
Manifest written : outputs/run_001/run_manifest_20260711T120000000000Z.json
```

---

## Direct invocation

```bash
source .venv/bin/activate
python src/run_experiment.py
# or with custom config:
python src/run_experiment.py --config path/to/config.yaml
```

---

## Changing attacker

In `config.yaml`:
```yaml
attacker_class: LinUCBAttacker  # or RandomAttacker, FixedScriptAttacker
```

Then `make run`.

---

## Verifying determinism

```bash
make run
cp outputs/run_001/report_*.md /tmp/report_run1.md
make run
diff /tmp/report_run1.md outputs/run_001/report_*.md
# Should be empty diff (identical metrics)
```

---

## Running tests

```bash
pytest tests/test_run_experiment.py -v
```

Target: 8 new tests (C-001..C-008) all green, overall suite ≥312 passed.
