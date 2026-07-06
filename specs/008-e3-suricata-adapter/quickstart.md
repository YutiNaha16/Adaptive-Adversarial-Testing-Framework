# Quickstart: Suricata Defence Adapter (F11)

## Scenario 1 — Unit test: alert in fixture file

```python
import json, pathlib, tempfile
from datetime import datetime, timezone
from aatf.contracts import Action
from aatf.suricata_defence import SuricataDefence

# Create fixture eve.json with one SSH scan alert
alert_line = json.dumps({
    "event_type": "alert",
    "timestamp": "2026-07-06T10:00:00.000000+0000",
    "alert": {"signature_id": 2001219, "signature": "ET SCAN Potential SSH Scan"},
    "src_ip": "172.28.0.3", "dest_ip": "172.28.0.2",
})

with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    f.write(alert_line + "\n")
    eve_path = f.name

action = Action(
    action_id="act-001",
    category="scan",
    parameters={"port": 22},
    timestamp=datetime.now(timezone.utc),
)

defence = SuricataDefence(eve_path)
result = defence.observe(action)

assert result.alerted is True
assert "2001219" in result.rule_ids
assert result.coverage == "covered"
assert result.anomaly_score == 0.0
```

Expected: passes with no Docker, no lab.

---

## Scenario 2 — No alerts (silent Suricata)

```python
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    f.write("")  # empty
    eve_path = f.name

defence = SuricataDefence(eve_path)
result = defence.observe(action)

assert result.alerted is False
assert result.rule_ids == []
assert result.coverage == "uncovered"
assert result.anomaly_score == 0.0
```

---

## Scenario 3 — Tail-read: second call sees only new lines

```python
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    f.write("")
    eve_path = f.name

defence = SuricataDefence(eve_path)

# First call: empty file
r1 = defence.observe(action)
assert r1.alerted is False

# Append a new alert
with open(eve_path, "a") as f:
    f.write(json.dumps({"event_type": "alert", "alert": {"signature_id": 9999}}) + "\n")

# Second call: sees only the new line
r2 = defence.observe(action)
assert r2.alerted is True
assert "9999" in r2.rule_ids
```

---

## Scenario 4 — Unreadable path raises DefenceError

```python
from aatf.defence import DefenceError
import pytest

defence = SuricataDefence("/nonexistent/eve.json")
with pytest.raises(DefenceError):
    defence.observe(action)
```

---

## Scenario 5 — Conformance check from F10

```python
from tests.test_defence import check_defence_contract
import tempfile

with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    f.write("")
    eve_path = f.name

check_defence_contract(SuricataDefence(eve_path), action)  # passes silently
```

---

## Scenario 6 — Integration test (lab must be running)

```python
import subprocess, pytest

result = subprocess.run(
    ["docker", "inspect", "aatf-suricata"],
    capture_output=True,
)
if result.returncode != 0:
    pytest.skip("lab not running — run 'make lab-up' first")

# Trigger SID 2001219
subprocess.run(
    ["docker", "exec", "aatf-attacker",
     "nmap", "-sS", "-p", "22", "--min-rate", "1000", "aatf-defender"],
    check=True,
)

import time; time.sleep(2)  # allow Suricata to process

eve_host_path = "/var/lib/docker/volumes/aatf-eve/_data/eve.json"
defence = SuricataDefence(eve_host_path)
result = defence.observe(action)

assert result.alerted is True
assert "2001219" in result.rule_ids
assert result.coverage == "covered"
```
