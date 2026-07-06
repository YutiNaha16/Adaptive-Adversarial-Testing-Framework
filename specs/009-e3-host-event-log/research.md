# Research: Host Event Log Signal (F12)

## Decision 1 — Pattern matching: substring search vs compiled regex

**Decision**: Plain substring search using Python's `in` operator (`pattern in line`).
Each configured pattern is matched against each decoded log line. If a pattern is found
anywhere in the line, it is collected.

**Rationale**:
- Matches the spec assumption ("plain string `in` operator") — simpler API for Phase 1.
- Zero additional dependencies — no `re` module needed for substring match.
- Sufficient for auth.log keywords like `"sshd"`, `"Failed password"`, `"Accepted publickey"`.
- Regex can be added in a future feature without changing the interface (pattern strings
  that happen to be valid regex can be used via `re.search` in a later version).

**Alternatives considered**:
- `re.search(pattern, line)` — more powerful but adds complexity; patterns must be valid
  regex, which can surprise callers passing literal strings containing `.` or `*`. Rejected
  for Phase 1.
- `fnmatch` glob patterns — no benefit over substring for auth.log keywords. Rejected.

---

## Decision 2 — Constructor signature

**Decision**: `HostLogDefence(log_path: str | Path, patterns: list[str])`.
Both arguments required; no defaults. Caller supplies the log path and pattern list.

**Rationale**:
- Mirrors F11 (`SuricataDefence(eve_path)`) in requiring an explicit path — no hardcoded
  defaults per FR-002.
- Patterns as a constructor argument (not per-call) reflects the natural lifecycle: the
  set of rules an adapter monitors is fixed at creation time, not per observation.
- Empty list is valid and produces `alerted=False` always (per FR-005, FR-011 edge case).

**Alternatives considered**:
- Per-call patterns via `observe(action, patterns)` — breaks the Defence interface contract
  which only passes `Action`. Rejected.
- Default patterns (`["sshd", "Failed password"]`) — hardcoded defaults violate FR-002.
  Rejected.

---

## Decision 3 — Multiple pattern matches per line and across lines

**Decision**: For each line, iterate all patterns; append matching pattern string to the
results list for each match. A single line can contribute multiple pattern strings
(one per matching pattern). Across multiple lines, all matching strings are accumulated.

**Rationale**:
- FR-011: "report every distinct pattern that matched" — accumulate across all new lines.
- Spec edge case: "all matched pattern strings appear in rule_ids, not just the first."
- Duplicates (same pattern matching in multiple lines) are allowed per the Assumptions
  section: "each distinct matching pattern string appears in rule_ids once per match."
- The caller (feedback collector, evaluator) can deduplicate if needed; the adapter's job
  is faithful reporting.

**Alternatives considered**:
- Deduplicate at adapter level — rejected; would hide how many lines matched the same
  pattern, losing observability.
- Return only the first match per line — rejected by FR-011 and spec edge cases.

---

## Decision 4 — Byte-offset cursor and truncation detection

**Decision**: Identical to F11 — `_cursor: int = 0` initialised to zero. Before reading,
call `os.path.getsize(path)` and reset `_cursor = 0` if `_cursor > file_size`. Seek to
`_cursor`, read bytes, set `_cursor = fh.tell()`.

**Rationale**:
- Direct reuse of a proven pattern from F11 — no divergence in cursor semantics between
  the two concrete Defence implementations.
- `os.path.getsize()` is a single syscall; no performance concern.
- Auth.log rotation (logrotate) replaces the file at the same path — truncation detection
  handles this correctly by resetting to 0.

**Alternatives considered**:
- Inode tracking — more robust but adds complexity. Overkill for lab use. Rejected.
- Line-number cursor — fragile under log rotation. Rejected.

---

## Decision 5 — Integration test target and skip guard

**Decision**: `docker inspect aatf-defender` as the skip-guard check (exit 0 = lab
running). The integration test reads the defender's auth log via
`docker exec aatf-defender cat /var/log/auth.log` (or the volume path), triggers an SSH
probe from the attacker container, waits 2 seconds, then calls `observe()`.

**Rationale**:
- Mirrors F11's `docker inspect aatf-suricata` guard for consistency across the test suite.
- The defender container runs sshd; a rejected SSH attempt produces a line like
  `sshd[NNN]: Failed password for invalid user root from 172.28.0.3` in auth.log.
- Reading auth.log via `docker exec cat` avoids needing to know the host-side volume path
  (which differs between Docker Desktop and native Linux). Simpler than volume inspection.

**Alternatives considered**:
- Host-side volume path (like F11 used for eve.json) — requires `docker inspect` on the
  volume, more brittle. Rejected in favour of `docker exec cat`.
- SSH probe to trigger a real "Accepted" line — requires valid credentials in the lab;
  a "Failed password" line from an invalid user is easier and requires no credential setup.

---

## Decision 6 — Empty pattern list behaviour

**Decision**: If `patterns == []`, `observe()` immediately returns
`DetectionResult(alerted=False, rule_ids=[], anomaly_score=0.0, coverage="uncovered")`
without attempting to read the file (or after checking readability to ensure the file
path is valid). Consistent with "no pattern can match" semantics.

**Rationale**:
- Spec edge case: "empty pattern list → alerted=False, coverage='uncovered' always."
- Checking file readability before returning allows the unreadable-path → DefenceError
  path to still fire even when patterns are empty, maintaining consistent error semantics.
- Returning `"uncovered"` (not `"unknown"`) is correct: the file is readable, we just
  chose not to match anything.

**Alternatives considered**:
- Skip file read entirely when patterns is empty — simpler but would miss the unreadable
  path → DefenceError case. Rejected.

---

## No NEEDS CLARIFICATION items

All technical decisions resolved. No new pip dependencies:
- `os`, `pathlib` — stdlib (same as F11)
- No `re` module needed (substring match via `in`)
