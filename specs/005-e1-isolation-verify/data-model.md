# Data Model: Isolation Verification (F06)

**Feature**: 005-e1-isolation-verify  
**Date**: 2026-07-02

This feature introduces no persistent data entities and no changes to `src/aatf/contracts.py`.
The two runtime entities are a custom exception type and the guard function signature.

---

## Entity 1: ExternalTargetError

**What it represents**: The error raised when a target address is rejected by the
fail-closed guard because it is not within the permitted lab subnet or loopback.

**Kind**: Python exception (subclass of `ValueError`)

**Attributes**:
- `target` (str) — the address or hostname that was rejected
- `reason` (str) — human-readable explanation ("publicly routable", "outside lab subnet",
  "hostname resolution failed — failing closed", etc.)

**Relationships**: Raised by `assert_lab_internal`; caught by callers (e.g. F08 action
executor) to abort the operation.

**Lifecycle**: Raised synchronously; never persisted.

---

## Entity 2: assert_lab_internal (function contract)

**What it represents**: The fail-closed guard. A pure function that classifies a target
address or hostname and either returns `None` (target is safe) or raises
`ExternalTargetError` (target is external or unresolvable).

**Signature**:
```
assert_lab_internal(target: str, allowed_networks: list[str] | None = None) -> None
```

**Parameters**:
- `target` — IP address string (e.g. `"172.28.0.5"`) or hostname (e.g. `"aatf-defender"`).
- `allowed_networks` — list of CIDR strings that are permitted (e.g. `["172.28.0.0/16"]`).
  Defaults to `["172.28.0.0/16"]` (the F04 lab subnet). Loopback (`127.0.0.0/8`, `::1/128`)
  is always permitted regardless of this parameter.

**Classification logic**:
1. If `target` looks like an IP: parse directly.
2. If `target` is a hostname: resolve via DNS; if resolution fails → raise (fail closed).
3. If resolved IP is loopback → pass (always safe).
4. If resolved IP is in any network in `allowed_networks` → pass.
5. Otherwise → raise `ExternalTargetError`.

**Relationships**: Used by F08 (action executor) — imported as
`from aatf.isolation import assert_lab_internal`. Tested in `tests/test_isolation.py`.

---

## Entity 3: Lab Network Configuration (read-only)

**What it represents**: The YAML structure in `lab/docker-compose.yml` that declares the
lab network. F06 reads this; F04 owns it.

**Relevant fields** (from F04 docker-compose.yml):
- `networks.lab.internal` — must be `true`
- `networks.lab.name` — must be `"aatf-lab"`
- `networks.lab.ipam.config[0].subnet` — must be `"172.28.0.0/16"`
- `services.<name>.ports` — must be absent on experiment containers

**Relationships**: Read by the US1 structural test. No runtime dependency — test-only.

---

## What is NOT in this data model

- No changes to `Action`, `DetectionResult`, `ContextVector`, `EpisodeRecord`, `RunManifest`
  in `src/aatf/contracts.py`.
- No database, no files written, no logs emitted.
- No configuration added to `config.yaml` (the allowed networks are a code-level default,
  not a user-tunable parameter — changing the lab subnet is an F04 concern).
