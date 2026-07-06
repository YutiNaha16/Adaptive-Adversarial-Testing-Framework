# Research: Suricata Defence Adapter (F11)

## Decision 1 — Eve.json incremental reading: byte-offset cursor vs inotify/tail -f

**Decision**: Byte-offset cursor stored as an instance attribute (`_cursor: int`).
`observe()` opens the file, seeks to `_cursor`, reads remaining bytes, advances `_cursor`
to the new end-of-file position.

**Rationale**:
- Pure stdlib (`pathlib.Path`, `open()`, `file.seek()`, `file.tell()`) — no new dependencies.
- Predictable behaviour in tests: fixture files can be written in one pass; the cursor is
  reset by creating a new adapter instance, which is the correct semantics for a new run.
- Works correctly when Suricata writes lines atomically (whole JSON lines) — which it does.
- Simpler than inotify (Linux-only, requires `inotify` or `watchdog` package) or
  `subprocess.Popen(['tail', '-f', ...])` (process management overhead).

**Alternatives considered**:
- `inotify` / `watchdog` — async event-driven, but adds a dependency and complicates the
  synchronous `observe()` contract. Rejected.
- `subprocess tail -f` — works but leaks a process per adapter instance. Rejected.
- Line-count cursor — fragile if Suricata ever rewrites lines. Byte offset is authoritative.

---

## Decision 2 — File truncation detection

**Decision**: Before reading, compare `_cursor` to `os.path.getsize(path)`. If cursor >
file size, reset cursor to 0 (file was rotated/truncated) and re-read from the beginning.

**Rationale**:
- Suricata rotates eve.json when it restarts (new file, same path). Without this check,
  the cursor would point past EOF and `seek()` + `read()` would return empty bytes, silently
  missing all new alerts.
- `os.path.getsize()` is a single syscall — no performance concern.
- Resetting to 0 on truncation means we re-read the whole new file, which is safe because
  the new file has no overlap with old alerts.

**Alternatives considered**:
- Track inode number — more robust but adds complexity (stat() on every call). Overkill
  for lab use where file rotation happens at most once per `make lab-down`. Rejected.

---

## Decision 3 — JSON parsing and malformed line handling

**Decision**: Parse each line with `json.loads(line)` inside a `try/except json.JSONDecodeError`.
Skip malformed lines silently (continue loop). Do not log or count — pure skip.

**Rationale**:
- Suricata occasionally writes partial lines if it's killed mid-write. One bad line must
  not crash the adapter or produce a wrong DetectionResult.
- Silent skip is correct: a partial line contains no actionable alert data. Logging would
  add a dependency on the logging module, which is a cross-cutting concern out of scope.

**Alternatives considered**:
- Re-raise as DefenceError — rejected, too aggressive. Suricata partial writes are transient
  and the next call will not see the same partial line (cursor has advanced past it).
- Log a warning — rejected, out of scope for F11; observability is F06/F16 territory.

---

## Decision 4 — Coverage state assignment

**Decision**: Three branches, evaluated in order:
1. File unreadable / missing → `coverage="unknown"`, raise `DefenceError`
2. File readable, ≥1 alert found → `coverage="covered"`, `alerted=True`
3. File readable, 0 alerts → `coverage="uncovered"`, `alerted=False`

**Rationale**:
- Matches Principle VI verbatim: "Logs MUST distinguish 'no rule covered this' from 'a rule
  existed but did not fire'."
- `"unknown"` is the safe failure state: the caller (feedback collector) knows it cannot
  trust the result and can abort or retry.
- Raising `DefenceError` on unreadable file makes failure explicit — no silent `"unknown"`
  results that could be mistaken for legitimate coverage data.

**Alternatives considered**:
- Return `"unknown"` without raising — rejected because callers would need to check the
  `coverage` field to detect failures, which is easy to forget.

---

## Decision 5 — Integration test skip guard

**Decision**: Check `docker inspect aatf-suricata > /dev/null 2>&1` (exit code 0 = lab
running). If not running, `pytest.skip("lab not running — run 'make lab-up' first")`.

**Rationale**:
- Mirrors the exact pattern in `tests/test_isolation.py:145` — consistency across the test
  suite. The check is a single subprocess call; failure is fast.
- Avoids pytest marks (which require conftest registration) for a simple runtime skip.

---

## Decision 6 — Eve.json path configuration

**Decision**: `SuricataDefence.__init__(self, eve_path: str | Path)` — caller supplies the
path. No hardcoded default. In integration tests, path is read from the Docker volume
(`docker inspect` or known host path). In unit tests, path points to a tmp fixture file.

**Rationale**:
- Hardcoding `/srv/eve/eve.json` would make unit tests dependent on Docker volume mounts.
  Configurable path makes the class testable in isolation.
- The feedback collector (F15) is responsible for wiring the correct path from config.

---

## No NEEDS CLARIFICATION items

All technical decisions resolved. No new pip dependencies:
- `json`, `pathlib`, `os` — all stdlib
