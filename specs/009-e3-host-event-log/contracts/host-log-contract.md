# Host Log Defence Contract

**Feature**: 009-e3-host-event-log
**File**: `src/aatf/host_log_defence.py`
**Contract version**: 1.0

---

## C-001 — HostLogDefence satisfies Defence interface

`check_defence_contract(HostLogDefence(path, patterns), action)` must pass with no
assertion errors.

**Test**: Call `check_defence_contract()` from F10's test_defence.py with a
`HostLogDefence` pointing at an empty fixture log file and a non-empty pattern list.

---

## C-002 — Matching line produces alerted=True with matched pattern in rule_ids

Given a log fixture containing one line with a known keyword, after calling `observe()`,
`result.alerted` is `True` and the matched pattern string is in `result.rule_ids`.

**Test**: Fixture line `"Jul  6 10:00:00 host sshd[1234]: Failed password for root"`;
patterns `["sshd"]`; assert `result.alerted is True`, `"sshd" in result.rule_ids`.

---

## C-003 — Non-matching lines produce alerted=False

Lines that do not match any configured pattern must produce `alerted=False`.

**Test**: Fixture line with no pattern match; patterns `["sshd"]`; assert
`alerted=False`, `rule_ids=[]`.

---

## C-004 — Empty file produces uncovered

An empty log file → `alerted=False`, `coverage="uncovered"`, `rule_ids=[]`.

**Test**: `HostLogDefence(empty_tmpfile, ["sshd"]).observe(action)` → assert fields.

---

## C-005 — Unreadable path raises DefenceError

If the log file path does not exist or is unreadable, `observe()` must raise
`DefenceError`.

**Test**: `HostLogDefence("/nonexistent/auth.log", ["sshd"]).observe(action)` →
`pytest.raises(DefenceError)`.

---

## C-006 — Multiple patterns can match a single line — all reported

A line matching two different patterns produces both pattern strings in `rule_ids`.

**Test**: Fixture line `"sshd Failed password"`; patterns `["sshd", "Failed password"]`;
assert both strings in `result.rule_ids`.

---

## C-007 — Multiple matching lines accumulate all matches

Two lines each matching different patterns → all matched pattern strings in `rule_ids`.

**Test**: Two-line fixture; first matches `"sshd"`, second matches `"Failed password"`;
patterns `["sshd", "Failed password"]`; assert both in `result.rule_ids`.

---

## C-008 — Second call with no new lines returns alerted=False

After a first call reads a match, a second call with no new lines returns `alerted=False`.

**Test**: First call reads matching line; no new lines written; second call →
`alerted=False`, `rule_ids=[]`, `coverage="uncovered"`.

---

## C-009 — New line written between calls is picked up

After a first call, a new matching line is appended; second call returns the new match.

**Test**: First call reads empty file; append matching line; second call →
`alerted=True`, matched pattern in `rule_ids`.

---

## C-010 — File truncation resets cursor

If the file shrinks (cursor > file size), the cursor resets and the new file is read
from the beginning.

**Test**: First call reads long file (cursor advances past 100 bytes); replace file
with shorter content (new match); second call → reads from byte 0, returns new match.

---

## C-011 — anomaly_score is always 0.0

`observe()` always returns `anomaly_score=0.0` regardless of matches.

**Test**: Both matching and non-matching cases → assert `result.anomaly_score == 0.0`.

---

## C-012 — Empty pattern list returns uncovered without alerted

When `patterns=[]`, `observe()` returns `alerted=False`, `coverage="uncovered"`,
`rule_ids=[]` even when the log file contains lines.

**Test**: Fixture with matching content; `patterns=[]`; assert `alerted=False`,
`coverage="uncovered"`.

---

## C-013 — Integration: live lab SSH probe triggers host log match (auto-skip)

When the lab is running (`make lab-up`) and an SSH attempt is made from the attacker
to the defender, a "Failed password" line appears in the defender's auth log and
`observe()` returns `alerted=True` with `"Failed password"` in `rule_ids`.
This test is skipped automatically when the lab is not running.

**Test**: `pytest.skip` guard on `docker inspect aatf-defender`; run SSH probe via
`docker exec aatf-attacker ssh`; read defender auth log via `docker exec aatf-defender
cat /var/log/auth.log`; call `observe()`; assert result.
