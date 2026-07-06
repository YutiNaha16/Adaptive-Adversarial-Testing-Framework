# Suricata Adapter Contract

**Feature**: 008-e3-suricata-adapter
**File**: `src/aatf/suricata_defence.py`
**Contract version**: 1.0

---

## C-001 — SuricataDefence satisfies Defence interface

`check_defence_contract(SuricataDefence(path), action)` must pass with no assertion errors.

**Test**: Call `check_defence_contract()` from F10's test_defence.py with a
`SuricataDefence` pointing at an empty fixture eve.json.

---

## C-002 — Alert line produces alerted=True with correct SID

Given an eve.json fixture containing one alert line with `signature_id=2001219`, after
calling `observe()`, `result.alerted` is `True` and `"2001219"` is in `result.rule_ids`.

**Test**: Write fixture line `{"event_type":"alert","alert":{"signature_id":2001219}}` to
a temp file; call observe(); assert result.

---

## C-003 — Non-alert lines are ignored

Lines with `event_type` other than `"alert"` (e.g., `"stats"`, `"flow"`) must not produce
an alert.

**Test**: Fixture with one `"stats"` line and no alert lines → `alerted=False`, `rule_ids=[]`.

---

## C-004 — Empty file produces uncovered

An empty eve.json → `alerted=False`, `coverage="uncovered"`, `rule_ids=[]`.

**Test**: `SuricataDefence(empty_tmpfile).observe(action)` → assert fields.

---

## C-005 — Unreadable path raises DefenceError with coverage=unknown

If the eve.json path does not exist or is unreadable, observe() must raise `DefenceError`.

**Test**: `SuricataDefence("/nonexistent/path/eve.json").observe(action)` →
`pytest.raises(DefenceError)`.

---

## C-006 — Multiple alerts → all SIDs in rule_ids

Two alert lines with different SIDs → both SIDs appear in `rule_ids`; `alerted=True`.

**Test**: Fixture with SIDs 2001219 and 2034660 → assert both in result.rule_ids.

---

## C-007 — Malformed JSON line is skipped

A fixture with one valid alert line and one malformed line → result matches the valid alert;
no exception raised.

**Test**: Fixture content `{"event_type":"alert","alert":{"signature_id":9999}}\nNOT_JSON\n`
→ `alerted=True`, `rule_ids=["9999"]`.

---

## C-008 — Second call returns only new lines (tail-read)

After a first call reads an alert, a second call with no new lines returns `alerted=False`.

**Test**: First call reads SID 2001219; no new lines written; second call → `alerted=False`,
`rule_ids=[]`, `coverage="uncovered"`.

---

## C-009 — New line written between calls is picked up

After a first call, a new alert is appended to the fixture file; second call returns the new
alert only.

**Test**: First call reads empty file; append alert line; second call → `alerted=True` with
new SID.

---

## C-010 — File truncation resets cursor

If the file shrinks (cursor > file size), the cursor is reset and the new file is read from
the beginning.

**Test**: First call reads non-empty fixture (cursor advances); replace fixture content with
shorter file; second call → reads from byte 0, returns new content.

---

## C-011 — anomaly_score is always 0.0

`observe()` always returns `anomaly_score=0.0` regardless of alerts.

**Test**: Both alerted and not-alerted cases → assert `result.anomaly_score == 0.0`.

---

## C-012 — Integration: live lab probe triggers SID 2001219

When the lab is running (`make lab-up`) and an nmap SYN scan is run from the attacker to
the defender port 22, `observe()` returns `alerted=True` with `"2001219"` in `rule_ids`.
This test is skipped automatically when the lab is not running.

**Test**: `pytest.skip` guard; run `make lab-smoke` equivalent; call `observe()`; assert.
