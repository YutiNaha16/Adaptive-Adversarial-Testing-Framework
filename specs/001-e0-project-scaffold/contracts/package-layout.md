# Contract: Package Layout & Architectural Boundary

The importable surface and the boundary invariant that later features rely on. These are asserted
by `tests/test_layout.py`.

## Importable packages

| Package | Meaning | Contract |
|---------|---------|----------|
| `aatf` | Top-level package | Imports cleanly; exposes package version metadata only |
| `aatf.live` | Live experiment loop layer | Imports cleanly; empty skeleton |
| `aatf.analysis` | Offline analysis pipeline layer | Imports cleanly; empty skeleton |
| `aatf.__main__` | Entrypoint stub | `python -m aatf` runs and exits 0 with a not-implemented message |

## Boundary invariant (Principle III)

- **Rule**: Importing `aatf.live` MUST NOT cause any concrete defence implementation to be
  imported. The live-loop layer depends only on (future) shared contracts/interfaces, never on a
  specific detector (Suricata, ML NIDS, ...).
- **Test**: After `import aatf.live`, assert that `sys.modules` contains no module whose dotted
  name marks it a concrete defence (e.g. matches a `*defence*`/`*suricata*` implementation under
  `aatf`). With no defences yet, the test passes and stands as a regression guard for every later
  feature.
- **Rationale**: Encodes the constitution's non-negotiable pluggable-defence boundary as a test
  from day one, so a future violation fails CI rather than slipping in.

## Stability

- These names (`aatf`, `aatf.live`, `aatf.analysis`) are the agreed homes for later features and
  should not be renamed without updating dependent specs (F02+).
