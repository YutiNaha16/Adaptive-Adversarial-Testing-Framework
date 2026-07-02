# Contract: Config API

**Module**: `src/aatf/config.py`
**Feature**: 002-e0-config-seeding

---

## Public surface

### `load_config(path: Path | str = "config.yaml") -> ExperimentConfig`

Loads and validates the experiment configuration from a YAML file.

**Arguments**
- `path` — path to the YAML file. Resolved relative to CWD if relative. Defaults to `"config.yaml"`.

**Returns**
- A fully-validated, frozen `ExperimentConfig` instance.

**Raises**
- `FileNotFoundError` — if the file does not exist at `path` (message includes the attempted path).
- `pydantic.ValidationError` — if any required field is missing, has the wrong type, or violates a range constraint. Pydantic's error message names the field and the problem.

**Behaviour**
1. Open and read `path`.
2. Parse with `yaml.safe_load()`. An empty/whitespace-only file yields `None` → treated as all-fields-missing by Pydantic.
3. Call `ExperimentConfig.model_validate(parsed)`.
4. Return the frozen instance.

---

### `ExperimentConfig` (Pydantic V2 BaseModel)

```
ExperimentConfig
├── episodes: int          — Field(gt=0)
├── seed: int              — Field(ge=0)
├── output_dir: Path       — coerced from str
├── ruleset_path: Path     — coerced from str
└── detection_threshold: float — Field(ge=0.0, le=1.0)

model_config = ConfigDict(frozen=True)
```

**Invariants**
- All fields required — no defaults.
- Immutable after construction (`frozen=True`).
- `model_dump(mode="json")` produces a JSON-safe dict (Path → str).

---

## Example YAML (`config.yaml`)

```yaml
episodes: 100
seed: 42
output_dir: outputs/run_001
ruleset_path: /etc/suricata/rules
detection_threshold: 0.5
```

---

## Test contract (`tests/test_config.py`)

| Test | Scenario | Expected |
|------|----------|----------|
| `test_load_valid_config` | Valid YAML → load_config | Returns ExperimentConfig with correct field values |
| `test_load_missing_file` | Non-existent path | Raises FileNotFoundError with path in message |
| `test_load_missing_field` | YAML missing `seed` | Raises ValidationError naming `seed` |
| `test_load_wrong_type` | `episodes: "ten"` | Raises ValidationError naming `episodes` |
| `test_load_empty_file` | Empty YAML | Raises ValidationError (all fields missing) |
| `test_config_is_frozen` | Attempt to set field after load | Raises ValidationError |
| `test_detection_threshold_bounds` | `detection_threshold: 1.5` | Raises ValidationError |
| `test_config_dump` | Valid config → model_dump(mode="json") | Returns dict with str paths |
