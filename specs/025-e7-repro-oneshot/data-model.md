# Data Model: One-Command Reproducibility (F25)

**Phase**: 1 — Design
**Date**: 2026-07-11
**Feature**: 025-e7-repro-oneshot

## Entities

### ExperimentConfig (modified from F02)

Add one field: `attacker_class: str = "RandomAttacker"`.

```python
class ExperimentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    episodes: int = Field(gt=0)
    seed: int = Field(ge=0)
    output_dir: Path
    ruleset_path: Path
    detection_threshold: float = Field(ge=0.0, le=1.0)
    attacker_class: str = "RandomAttacker"   # NEW
```

**Valid values**: `"RandomAttacker"`, `"LinUCBAttacker"`, `"FixedScriptAttacker"`

---

### config.yaml (updated)

```yaml
episodes: 100
seed: 42
output_dir: outputs/run_001
ruleset_path: /etc/suricata/rules
detection_threshold: 0.5
attacker_class: RandomAttacker
```

---

### run_manifest (enriched, written by existing aatf.manifest.write_manifest)

Already written by F02's `write_manifest(config, seed)`. Contains: `seed`, `python_version`, `packages`, `suricata_version`, `ruleset_version`, `git_commit`, `config_snapshot`, `timestamp`.

The entrypoint will additionally write a **metrics summary** to stdout (not added to manifest — manifest stays as F02 defined it).

---

## Files

```text
src/
└── run_experiment.py       # NEW (~90 LOC)

(modified)
src/aatf/config.py          # +1 field: attacker_class
config.yaml                 # +1 key: attacker_class
Makefile                    # update run: target
README.md                   # add Quick Start section
```

---

## Data Flow

```
config.yaml
    │
    ▼ load_config()
ExperimentConfig
    │
    ├─ seed_everything(seed)
    │
    ├─ Attacker (by attacker_class) ──────────────────────┐
    │                                                      │
    ├─ NullDefence()                                       │
    │                                                      │
    └─ for i in range(episodes):                          │
            │                                              │
            ▼                                             │
        EpisodeState (fresh)                              │
            │                                              │
            ▼ run_episode(state, action_selector, ...)   │
        EpisodeResult                                     │
            │                                              │
            ├─ attacker.observe(per step)  ◄──────────────┘
            │
            ▼ convert to EpisodeRecord
        list[EpisodeRecord]
            │
            ├─ generate_report(records, REGISTRY, report_path)  →  output/report_*.md
            │
            ├─ write_manifest(config, seed)  →  output/run_manifest_*.json
            │
            └─ print summary to stdout
```
