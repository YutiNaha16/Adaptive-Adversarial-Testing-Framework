# Research: Action Executor (F08)

## Decision 1: Network primitive abstraction — SendFn injection

**Decision**: Injectable `SendFn = Callable[[str, int, bytes], None]` — `(host, port, payload)` — passed at `ActionExecutor` construction time.
**Rationale**: Enables complete unit-test isolation without monkeypatching global `socket` module. Tests pass a recording stub; production passes a real socket wrapper. The interface is minimal enough to cover TCP, UDP, and HTTP without over-engineering.
**Alternatives considered**:
- Monkeypatching `socket.socket` globally: works but is brittle (affects all tests in the process) and couples tests to implementation internals.
- Abstract base class for network layer: heavier, no benefit at this scale.

## Decision 2: Handler dispatch — dict[str, Handler] keyed by action_id

**Decision**: `_handlers: dict[str, Callable]` keyed by `action_id` (not category), built at construction time from a static registration table.
**Rationale**: Each of the 15 actions has distinct traffic patterns (different ports, payloads, repeat counts) even within the same category. Keying by `action_id` allows fine-grained control without an extra dispatch step. Category is available on the Action object for the `ExecutionResult`.
**Alternatives considered**:
- Category-level dispatch with sub-dispatch by action_id: adds indirection with no benefit.
- Plugin registration via decorators: overcomplicated for 15 static handlers.

## Decision 3: ICMP ping sweep — TCP echo port (7) stand-in

**Decision**: `icmp_ping_sweep` sends TCP SYN to port 7 (echo service) instead of raw ICMP.
**Rationale**: Raw ICMP requires root privileges or raw socket capabilities not guaranteed inside the attacker container. TCP SYN to a destination triggers ET SCAN rules (particularly `ET SCAN` Nmap-style sweep signatures) without needing elevated privileges. The shape of the traffic — many short-lived connections to the same host — resembles a ping sweep.
**Alternatives considered**:
- Raw ICMP via `socket.IPPROTO_ICMP`: requires `CAP_NET_RAW`; not reliable in containers.
- subprocess `ping`: violates no-subprocess rule and is non-deterministic.

## Decision 4: DNS query bytes — minimal wire-format construction

**Decision**: Construct minimal valid DNS query bytes manually (12-byte header + QNAME + QTYPE/QCLASS) without importing `dnspython`.
**Rationale**: No new pip dependencies. A minimal DNS query (AXFR = type 252, A = type 1) is ~30 bytes and straightforward to construct with `struct.pack`. This is sufficient to trigger ET DNS rules which match on query type fields.
**Alternatives considered**:
- `dnspython`: clean API but is a new dependency, against the no-new-deps constraint.
- Hardcoded byte strings: fragile to copy-paste errors; struct.pack is readable and verifiable.

## Decision 5: HTTP payloads — pattern strings, not working exploits

**Decision**: SQLi handler sends `GET /?q=1+UNION+SELECT+1--` ; XSS handler sends `GET /?q=<script>alert(1)</script>`; dir scan sends `GET /admin HTTP/1.0`.
**Rationale**: ET Open rules match on these exact pattern strings in HTTP request URIs. The requests are syntactically valid HTTP but carry no exploit — they merely contain the string patterns the rules watch for. This satisfies Constitution Principle I (defanged) while reliably triggering ET WEB_SERVER / ET WEB_CLIENT rules.
**Alternatives considered**:
- Randomly generated payloads: non-deterministic, may miss rule patterns.
- Full HTTP library (requests): new dependency; overkill for simple GET/POST.

## Decision 6: Jitter timing — rng.uniform, no real sleep in unit tests

**Decision**: Jitter is computed as `delay = rng.uniform(0, interval_ms / 1000)` but actual `time.sleep(delay)` is called only in production. The `sleep_fn` is injected alongside `send_fn` so unit tests pass a no-op.
**Rationale**: Unit tests must run fast (< 1 second). Injecting `sleep_fn` keeps the seeded RNG path exercisable without actually sleeping, while production uses `time.sleep`.
**Alternatives considered**:
- Monkeypatch `time.sleep`: works but couples tests to global state.
- Skip sleep entirely in tests via env var: implicit, harder to reason about.

## Decision 7: ExternalTargetError — subclass of ValueError

**Decision**: `class ExternalTargetError(ValueError)`.
**Rationale**: `ValueError` is the standard Python exception for invalid argument values. Subclassing it means callers can catch either `ExternalTargetError` (precise) or `ValueError` (broad). Does not require a new exception hierarchy.
**Alternatives considered**:
- `RuntimeError`: less semantically accurate.
- Custom base `ExecutorError`: adds hierarchy with no immediate benefit.
