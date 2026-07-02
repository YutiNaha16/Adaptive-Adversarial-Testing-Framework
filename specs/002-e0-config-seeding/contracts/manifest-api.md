# Contract: Manifest API

**Module**: `src/aatf/manifest.py`
**Feature**: 002-e0-config-seeding

---

## Public surface

### `write_manifest(config: ExperimentConfig, seed: int, *, suricata_version: str = "unknown", ruleset_version: str = "unknown") -> Path`

Writes a timestamped JSON provenance manifest to `config.output_dir`.

**Arguments**
- `config` — loaded `ExperimentConfig` instance (provides `output_dir` and the config snapshot).
- `seed` — the integer seed used for this run (may differ from `config.seed` if overridden at runtime; typically they are equal).
- `suricata_version` — (keyword-only) Suricata version string. Defaults to `"unknown"`. E1 will supply the real value.
- `ruleset_version` — (keyword-only) ET Open ruleset version string. Defaults to `"unknown"`. E1 will supply the real value.

**Returns**
- `pathlib.Path` — absolute path to the written manifest file.

**Raises**
- `OSError` / `PermissionError` — if `output_dir` cannot be created or the file cannot be written (propagated, not caught).

**Behaviour**:
1. Compute UTC timestamp: `datetime.utcnow()` formatted as `%Y%m%dT%H%M%SZ`.
2. Create `config.output_dir` (and parents) with `mkdir(parents=True, exist_ok=True)`.
3. Collect package versions via `importlib.metadata.version()` for each known direct dependency; skip on `PackageNotFoundError`.
4. Capture git commit: `git rev-parse HEAD` via subprocess; append `-dirty` if `git status --porcelain` is non-empty; record `"unknown"` on any failure.
5. Build manifest dict (see schema in data-model.md).
6. Write to `output_dir / f"run_manifest_{timestamp}.json"` with `json.dump(indent=2)`.
7. Return the `Path` of the written file.

---

## Known direct dependencies captured in `packages`

```python
KNOWN_PACKAGES = ["pip-tools", "pytest", "ruff", "pydantic", "pyyaml", "numpy"]
```

Updated as new packages are added to `requirements.in` in later features.

---

## Test contract (`tests/test_manifest.py`)

| Test | Scenario | Expected |
|------|----------|----------|
| `test_manifest_written` | write_manifest(config, 42) | File exists in output_dir |
| `test_manifest_filename_pattern` | write_manifest → filename | Matches `run_manifest_\d{8}T\d{6}Z\.json` |
| `test_manifest_no_overwrite` | write_manifest called twice | Two distinct files exist |
| `test_manifest_schema` | Parse written JSON | All 8 required keys present with correct types |
| `test_manifest_seed_field` | write_manifest(config, 99) | manifest["seed"] == 99 |
| `test_manifest_config_snapshot` | write_manifest(config, 42) | config_snapshot matches config fields |
| `test_manifest_creates_output_dir` | output_dir does not exist | Directory created; file written |
| `test_manifest_unknown_suricata` | default call | suricata_version == "unknown" |
| `test_manifest_custom_versions` | suricata_version="7.0.3" passed | Field value preserved in JSON |
| `test_manifest_git_absent` | git not available (mock) | git_commit == "unknown", no error |
| `test_manifest_packages_dict` | Parse packages field | Dict of str→str; pydantic key present |
