# Research: Configuration & Seed Management

**Feature**: 002-e0-config-seeding | **Date**: 2026-07-02

All decisions were either resolved in `/sp.clarify` (D1–D3) or are standard patterns requiring
minimal research (D4–D8). No NEEDS CLARIFICATION items remain.

---

## D1 — Config Validation: Pydantic V2

**Decision**: Use `pydantic>=2.0` `BaseModel` for `ExperimentConfig`.

**Rationale**: FR-002 through FR-007 require automatic type coercion, required-field enforcement,
and descriptive per-field error messages — all provided by Pydantic V2 out of the box. The
alternative (stdlib `dataclass` + hand-written `__post_init__` validation) would require ~50 lines
of custom validation code that Pydantic replaces with field annotations.

**Key Pydantic V2 patterns used**:
- `model_config = ConfigDict(frozen=True)` — makes the config instance immutable after load
  (read-only constraint from spec Key Entities).
- `Field(gt=0)` for `episodes`, `Field(ge=0)` for `seed`, `Field(ge=0.0, le=0.1)` for
  `detection_threshold` — enforces FR-003 range constraints automatically.
- `model_validate(yaml_dict)` — entry point from the YAML-parsed dict.

**Alternatives considered**: stdlib `dataclass` — rejected (manual validation code); `attrs` —
unnecessary third dependency; Pydantic V1 — outdated, V2 is current.

---

## D2 — YAML Library: PyYAML

**Decision**: Use `pyyaml` (`yaml.safe_load()`).

**Rationale**: Simple single-call API (`yaml.safe_load(f)`), most widely known Python YAML
library, sufficient for read-only config loading. `ruamel.yaml` was considered but rejected
because comment round-trip preservation is not needed (the researcher edits the YAML source
directly; the library never writes back to it).

**Key pattern**: Always use `yaml.safe_load()` not `yaml.load()` — the `safe_` variant prevents
arbitrary Python object instantiation from YAML tags (security best practice).

**Alternatives considered**: `ruamel.yaml` — more complex API, unneeded feature set; `tomllib`
(stdlib TOML, Python 3.11+) — TOML is less familiar for ML config files than YAML.

---

## D3 — Manifest Filename: Timestamped, Never Overwrite

**Decision**: Write `run_manifest_<ISO-timestamp>.json` (UTC, compact ISO-8601, e.g.
`run_manifest_20260702T120000Z.json`) to `output_dir`.

**Rationale**: Silent overwrite would destroy provenance for previous runs if the researcher
reuses the same `output_dir` — a direct violation of Constitution Principle II (every run's
provenance must be auditable). Timestamped filenames make every run's record permanent at zero
cost. The timestamp in the filename matches the `timestamp` field inside the manifest.

**Format chosen**: `%Y%m%dT%H%M%SZ` (compact, sortable, no colons for cross-OS path safety).

**Alternatives considered**: Silent overwrite — rejected (provenance loss); numbered suffixes —
rejected (non-monotonic on concurrent runs); single static filename — rejected (same reason as
overwrite).

---

## D4 — Package Version Capture: importlib.metadata

**Decision**: Use `importlib.metadata.version(package_name)` (Python 3.8+ stdlib).

**Rationale**: No extra dependency. Capture versions for all packages listed in
`requirements.in` by iterating the known direct-dependency names. Skip gracefully if a package
is not installed (catch `importlib.metadata.PackageNotFoundError`).

**Direct dependency names to capture** (all `requirements.in` entries after this feature):
`pip-tools`, `pytest`, `ruff`, `pydantic`, `pyyaml`, `numpy`.

**Alternatives considered**: `pip show` via subprocess — fragile, parses text output; `pkg_resources` — deprecated in favour of `importlib.metadata`.

---

## D5 — Git SHA Capture: subprocess + git rev-parse

**Decision**: Capture git commit via `subprocess.run(["git", "rev-parse", "HEAD"], ...)`.
Detect dirty working tree via `git status --porcelain`. Annotate as `"<sha>-dirty"` if dirty.
Fall back to `"unknown"` if git is unavailable or the directory is not a repo.

**Rationale**: No extra dependency (`gitpython` would be unnecessary). The `git` binary is
always available in CI (ubuntu-latest) and on developer machines. `CalledProcessError` and
`FileNotFoundError` are caught and mapped to `"unknown"`.

**Alternatives considered**: `gitpython` — too heavy for what is a one-line operation;
`dulwich` — pure-Python but another dependency.

---

## D6 — NumPy RNG Seeding: Legacy Global State

**Decision**: Use `numpy.random.seed(seed)` (seeds the legacy global `RandomState`).

**Rationale**: The LinUCB attacker (F17) and other Phase 1 components will call NumPy random
functions through the module-level API (e.g. `numpy.random.normal()`). Seeding the legacy global
state ensures these calls are deterministic without requiring callers to pass a `Generator`
instance. This is the correct choice for Phase 1 given that all NumPy calls will use the global
API.

**Future note**: If Phase 2 components use `numpy.random.default_rng()`, they should receive the
seed directly and not depend on `seed_everything` — document this in seeding.py's docstring.

**Alternatives considered**: `numpy.random.default_rng(seed)` — creates a new `Generator`
object that is NOT the global state; callers would need to import and use the instance, which
requires threading the Generator through every call site.

---

## D7 — ExperimentConfig Immutability: frozen=True

**Decision**: Set `model_config = ConfigDict(frozen=True)` on `ExperimentConfig`.

**Rationale**: The spec Key Entities section states the config is "treated as read-only by all
downstream code". Pydantic V2's `frozen=True` enforces this at runtime — any attempt to mutate
a field raises `ValidationError`. This catches accidental mutation bugs early.

**Effect**: `ExperimentConfig` instances are hashable (can be used as dict keys or in sets if
needed).

---

## D8 — config.yaml Default Path: CWD

**Decision**: `load_config(path: Path | str = "config.yaml")` resolves the path relative to the
current working directory (Python standard).

**Rationale**: Standard Python convention for CLI tools. When invoked as `python -m aatf` from
the repo root, CWD is the repo root and `config.yaml` is found there. Researchers can also pass
an explicit path for CI or multi-config setups.

**Note**: `config.yaml` is NOT added to `.gitignore` — it is the example config that ships with
the repo. Researchers who want personal overrides can pass an explicit path.
