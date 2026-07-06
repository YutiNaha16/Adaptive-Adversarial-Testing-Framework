# Quickstart: Host Event Log Signal (F12)

## Scenario 1 — Unit test: keyword match in fixture file

```python
import pathlib, tempfile
from datetime import datetime, timezone
from aatf.contracts import Action
from aatf.host_log_defence import HostLogDefence

log_line = "Jul  6 10:00:00 aatf-defender sshd[1234]: Failed password for invalid user root from 172.28.0.3 port 54321 ssh2\n"

with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
    f.write(log_line)
    log_path = f.name

action = Action(
    action_id="act-001",
    category="scan",
    parameters={"port": 22},
    timestamp=datetime.now(timezone.utc),
)

defence = HostLogDefence(log_path, patterns=["sshd", "Failed password"])
result = defence.observe(action)

assert result.alerted is True
assert "sshd" in result.rule_ids
assert "Failed password" in result.rule_ids
assert result.coverage == "covered"
assert result.anomaly_score == 0.0
```

Expected: passes with no Docker, no lab.

---

## Scenario 2 — Empty file (no events yet)

```python
with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
    f.write("")
    log_path = f.name

defence = HostLogDefence(log_path, patterns=["sshd"])
result = defence.observe(action)

assert result.alerted is False
assert result.rule_ids == []
assert result.coverage == "uncovered"
assert result.anomaly_score == 0.0
```

---

## Scenario 3 — Tail-read: second call sees only new lines

```python
import tempfile, os

with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
    f.write("")
    log_path = f.name

defence = HostLogDefence(log_path, patterns=["sshd"])

# First call: empty file
r1 = defence.observe(action)
assert r1.alerted is False

# Append a new matching line
with open(log_path, "a") as f:
    f.write("sshd[9999]: Failed password\n")

# Second call: sees only the new line
r2 = defence.observe(action)
assert r2.alerted is True
assert "sshd" in r2.rule_ids
```

---

## Scenario 4 — Unreadable path raises DefenceError

```python
from aatf.defence import DefenceError
import pytest

defence = HostLogDefence("/nonexistent/auth.log", patterns=["sshd"])
with pytest.raises(DefenceError):
    defence.observe(action)
```

---

## Scenario 5 — Conformance check from F10

```python
from tests.test_defence import check_defence_contract
import tempfile

with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
    f.write("")
    log_path = f.name

check_defence_contract(HostLogDefence(log_path, ["sshd"]), action)  # passes silently
```

---

## Scenario 6 — Integration test (lab must be running)

```python
import subprocess, tempfile, time, pytest

def _lab_running() -> bool:
    r = subprocess.run(["docker", "inspect", "aatf-defender"], capture_output=True)
    return r.returncode == 0

if not _lab_running():
    pytest.skip("lab not running — run 'make lab-up' first")

# Trigger a Failed-password line on the defender
subprocess.run(
    ["docker", "exec", "aatf-attacker",
     "ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
     "-o", "ConnectTimeout=3", "root@aatf-defender"],
    capture_output=True,
)
time.sleep(2)

# Read defender auth log content to a temp file
result = subprocess.run(
    ["docker", "exec", "aatf-defender", "cat", "/var/log/auth.log"],
    capture_output=True, text=True,
)
with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
    f.write(result.stdout)
    log_path = f.name

defence = HostLogDefence(log_path, patterns=["Failed password", "sshd"])
dr = defence.observe(action)

assert dr.alerted is True
assert "Failed password" in dr.rule_ids
assert dr.coverage == "covered"
```
