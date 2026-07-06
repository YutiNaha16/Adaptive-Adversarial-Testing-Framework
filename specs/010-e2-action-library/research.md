# Research: Defanged Action Library (F07)

## Decision 1: ActionDefinition representation — dataclass vs Pydantic

**Decision**: Python `dataclass` (stdlib, frozen=True)
**Rationale**: ActionDefinition is pure data with no validation logic beyond field presence — a frozen dataclass is lighter and imports faster than Pydantic. The Pydantic `Action` contract (F03) is only needed for the wire format produced by `to_action()`; ActionDefinition itself does not cross a serialisation boundary.
**Alternatives considered**:
- Pydantic BaseModel: heavier, adds a dependency; validation benefit does not justify cost for a static registry entry.
- TypedDict: lacks methods (e.g. `to_action()`); not a good fit.

## Decision 2: Registry construction — module-level constant vs lazy singleton

**Decision**: Module-level constant `REGISTRY: ActionRegistry` built at import time from a declarative list.
**Rationale**: Action definitions are static and never change at runtime. Building at import time gives zero-latency lookup, surfaces duplicate-ID errors immediately (before any test runs), and keeps the code dead-simple. A lazy singleton would add complexity with no benefit.
**Alternatives considered**:
- Plugin-style discovery (scan submodules): overcomplicated for a static list of 15 entries.
- Lazy singleton with `functools.cache`: unnecessary indirection.

## Decision 3: Safety guard — IP detection approach

**Decision**: Use `stdlib ipaddress` to parse string parameter values; classify any `IPv4Address` / `IPv6Address` that is not in `172.28.0.0/16` as a violation. Additionally flag empty `default_parameters` dicts.
**Rationale**: `ipaddress` provides precise is-global / is-private semantics without regex fragility. The `172.28.0.0/16` lab subnet is the only permitted address space per Constitution Principle I.
**Alternatives considered**:
- Regex pattern matching: fragile, misses edge cases (leading zeros, hex notation).
- Allowlist of exact IPs: too rigid; guard should reason about subnets.

## Decision 4: How actions map to the F03 Action contract

**Decision**: `ActionDefinition.to_action(timestamp)` constructs an `Action(action_id=..., category=..., parameters=self.default_parameters, timestamp=timestamp)`. The caller supplies the timestamp so ActionDefinition itself stays pure data.
**Rationale**: `Action` requires a `timestamp` (datetime). Injecting it at call time keeps ActionDefinition frozen and deterministic — no `datetime.now()` inside the library module.
**Alternatives considered**:
- Store timestamp inside ActionDefinition: breaks "pure data at definition time" invariant.
- Return a dict instead of an Action: loses type safety.

## Decision 5: Category taxonomy

**Decision**: Six fixed string literals: `"scan"`, `"brute"`, `"ssh"`, `"web"`, `"dns"`, `"exfil"` — no Enum.
**Rationale**: String literals keep the registry readable, avoid an import dependency cycle if categories are referenced in F08/F09, and are easily extensible (add a new string, no Enum change needed). The safety guard and registry can still validate by checking against a known set.
**Alternatives considered**:
- Enum: stricter, but adds ceremony for downstream consumers that just need to compare strings.

## Decision 6: Suricata rule categories to target

Each action maps to an ET Open rule category so F08 and the explainability engine (F23) can trace detected technique → SID → remediation. Mapping:

| Category | ET Open rule family |
|---|---|
| scan | ET SCAN |
| brute | ET BRUTE_FORCE |
| ssh | ET EXPLOIT (SSH), ET SCAN |
| web | ET WEB_CLIENT, ET WEB_SERVER |
| dns | ET DNS |
| exfil | ET POLICY (DNS over HTTP), ET TROJAN (data exfil pattern) |

## Decision 7: No new pip dependencies

**Decision**: stdlib only (`dataclasses`, `ipaddress`, `typing`).
**Rationale**: Consistent with F03 and F10–F12 pattern of using stdlib. The `ipaddress` module (Python 3.3+) covers all IP classification needs.
