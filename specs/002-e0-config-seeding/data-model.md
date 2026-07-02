# Data Model: Configuration & Seed Management

**Feature**: 002-e0-config-seeding | **Date**: 2026-07-02

Two entities: one runtime object (`ExperimentConfig`) and one disk artifact (`RunManifest`).

---

## Entity 1: ExperimentConfig

**Source module**: `src/aatf/config.py`
**Implementation**: Pydantic V2 `BaseModel` with `frozen=True`
**Lifecycle**: Created once by `load_config()` at startup; read-only for the rest of the run.

### Fields

| Field | Type | Constraint | Description |
|-------|------|------------|-------------|
| `episodes` | `int` | `> 0` | Number of experiment episodes to run |
| `seed` | `int` | `>= 0` | Global RNG seed — passed to `seed_everything()` |
| `output_dir` | `pathlib.Path` | non-empty string coerced to Path | Directory where run outputs and manifests are written |
| `ruleset_path` | `pathlib.Path` | non-empty string coerced to Path | Path to Suricata ET Open ruleset directory (used by F10+) |
| `detection_threshold` | `float` | `>= 0.0`, `<= 1.0` | Minimum detection score threshold (used by F20+ evaluator) |

### Validation rules (enforced by Pydantic V2)

- All fields are **required** — missing any field raises `pydantic.ValidationError` naming the field.
- Type coercion is strict for numeric fields (`episodes`, `seed`, `detection_threshold`); a string value that cannot be coerced raises `ValidationError`.
- An empty YAML document (parsed as `None`) is rejected at `model_validate()` — Pydantic treats it as all-fields-missing.
- `frozen=True` means no mutation after construction; attempting to set a field raises `ValidationError`.

### Serialisation

- **Input**: YAML dict loaded by `yaml.safe_load()` → `ExperimentConfig.model_validate(dict)`
- **Output** (for manifest snapshot): `config.model_dump(mode="json")` → JSON-safe dict
  (Path fields are serialised as strings automatically by Pydantic V2).

---

## Entity 2: RunManifest (disk artifact)

**Source module**: `src/aatf/manifest.py`
**Implementation**: Plain Python dict written to JSON via `json.dump()`.
**Lifecycle**: Created once per run by `write_manifest()`; immutable on disk.
**Filename pattern**: `run_manifest_<YYYYMMDDTHHMMSSz>.json` in `output_dir`.

### Schema (JSON)

```json
{
  "seed": 42,
  "python_version": "3.12.3",
  "packages": {
    "pydantic": "2.7.1",
    "pyyaml": "6.0.1",
    "numpy": "1.26.4",
    "pip-tools": "7.4.1",
    "pytest": "8.2.0",
    "ruff": "0.4.4"
  },
  "suricata_version": "unknown",
  "ruleset_version": "unknown",
  "git_commit": "4f342e2a1b3c...",
  "config_snapshot": {
    "episodes": 100,
    "seed": 42,
    "output_dir": "outputs/run_001",
    "ruleset_path": "/etc/suricata/rules",
    "detection_threshold": 0.5
  },
  "timestamp": "2026-07-02T12:00:00Z"
}
```

### Field definitions

| Field | JSON type | Source | Notes |
|-------|-----------|--------|-------|
| `seed` | integer | caller argument | The seed passed to `write_manifest()` |
| `python_version` | string | `sys.version_info` | e.g. `"3.12.3"` |
| `packages` | object (str→str) | `importlib.metadata` | Direct deps from `requirements.in`; missing packages omitted |
| `suricata_version` | string | caller argument | Defaults to `"unknown"`; E1 will supply real value |
| `ruleset_version` | string | caller argument | Defaults to `"unknown"`; E1 will supply real value |
| `git_commit` | string | `git rev-parse HEAD` | `"<sha>-dirty"` if dirty; `"unknown"` if git unavailable |
| `config_snapshot` | object | `config.model_dump(mode="json")` | All ExperimentConfig fields as JSON-safe dict |
| `timestamp` | string | `datetime.utcnow()` | ISO-8601 UTC, e.g. `"2026-07-02T12:00:00Z"` |

### Invariants

- Every manifest file has a **unique filename** (timestamp-based) — no two runs produce the same filename unless started within the same second (extremely unlikely in practice; acceptable risk).
- The `timestamp` field inside the manifest matches the timestamp in the filename.
- `config_snapshot.seed` always equals the top-level `seed` field.

---

## Relationships

```
load_config(path) ──────────► ExperimentConfig (frozen, in memory)
                                      │
                                      ├── seed ──────► seed_everything(seed)
                                      │                     │
                                      │                     ▼
                                      │              [random, numpy, torch? seeded]
                                      │
                                      └── passed to ──► write_manifest(config, seed)
                                                              │
                                                              ▼
                                                   run_manifest_<ISO>.json (on disk)
```

The config is the single source of truth; seeding and manifest writing both consume it. No entity
holds a reference to another at rest — they communicate through function arguments.
