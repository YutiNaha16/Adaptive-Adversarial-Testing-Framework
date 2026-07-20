# Quickstart: Pluggable Defence Interface (F10)

## Scenario 1 — Use NullDefence in a unit test (no Docker needed)

```python
from datetime import datetime, timezone
from aatf.contracts import Action
from aatf.defence import NullDefence

action = Action(
    action_id="act-001",
    category="scan",
    parameters={"port": 22, "rate": 100},
    timestamp=datetime.now(timezone.utc),
)
defence = NullDefence()
result = defence.observe(action)

assert result.alerted is False
assert result.rule_ids == []
assert result.anomaly_score == 0.0
assert result.coverage == "unknown"
```

Expected: passes with no exceptions, no containers, no I/O.

---

## Scenario 2 — Implement a custom Defence

```python
from aatf.contracts import Action, DetectionResult
from aatf.defence import Defence

class AlwaysAlertDefence(Defence):
    def observe(self, action: Action) -> DetectionResult:
        return DetectionResult(
            alerted=True,
            rule_ids=["9999999"],
            anomaly_score=1.0,
            coverage="covered",
        )
```

Expected: class definition succeeds; `observe()` returns a valid DetectionResult.

---

## Scenario 3 — Swap detector without changing consumer

```python
# Consumer code — depends only on Defence, not on any concrete class
def run_episode(defence: Defence, action: Action) -> float:
    result = defence.observe(action)
    return -1.0 if result.alerted else 0.0

# Works with NullDefence
run_episode(NullDefence(), action)

# Works with AlwaysAlertDefence — same consumer, no change
run_episode(AlwaysAlertDefence(), action)
```

Expected: both calls succeed; consumer code is identical.

---

## Scenario 4 — Handle DefenceError in caller

```python
from aatf.defence import Defence, DefenceError

class UnreliableDefence(Defence):
    def observe(self, action: Action) -> DetectionResult:
        raise DefenceError("connection to eve.json lost", cause=IOError("file not found"))

try:
    UnreliableDefence().observe(action)
except DefenceError as e:
    print(f"Defence failed: {e}")
```

Expected: `DefenceError` is raised and caught; no silent partial result.

---

## Scenario 5 — Run conformance check on any Defence

```python
# In any test file for a future concrete Defence (F11, F12, etc.)
from tests.test_defence import check_defence_contract
from aatf.defence import NullDefence

check_defence_contract(NullDefence(), action)  # passes silently if compliant
```

Expected: compliant Defence passes with no assertions raised.

---

## Scenario 6 — Validate DetectionResult tightened constraint

```python
from pydantic import ValidationError
from aatf.contracts import DetectionResult

# This should now raise ValidationError (rule_ids non-empty but alerted=False)
try:
    DetectionResult(alerted=False, rule_ids=["2001219"], anomaly_score=0.0, coverage="covered")
except ValidationError as e:
    print("Correctly rejected:", e)
```

Expected: `ValidationError` raised — the tightened F03 validator is enforced.
