# Contracts: Feedback Collector (F15)

**Feature**: `015-e4-feedback-collector` | **Date**: 2026-07-10
**File under test**: `src/aatf/feedback.py`
**Test file**: `tests/test_feedback.py`

10 contracts across 3 user stories. All contracts use a minimal test graph injected via `attack_graph=` parameter to avoid coupling tests to the canonical `ATTACK_GRAPH` topology.

---

## Test Graph (shared fixture)

```python
# Minimal 3-node graph: A → B → C
# Entry: A; A unlocks B; B unlocks C; C is terminal
from aatf.attack_graph import AttackGraph

_TEST_GRAPH = AttackGraph(
    entry_points=frozenset({"recon-syn-scan"}),
    edges={
        "recon-syn-scan": frozenset({"exploit-vsftpd-backdoor"}),
        "exploit-vsftpd-backdoor": frozenset({"lateral-move-smb"}),
    },
)
```

Use `action_id` values from REGISTRY (e.g., "recon-syn-scan", "exploit-vsftpd-backdoor", "lateral-move-smb") so that EpisodeState.__post_init__ validation passes.

---

## User Story 1: Episode State Recording

### C-001 — alert_history grows by 1

```python
def test_alert_history_appended():
    state = EpisodeState()
    collect_feedback(state, "recon-syn-scan", True, attack_graph=_TEST_GRAPH)
    assert state.alert_history == [True]
    collect_feedback(state, "exploit-vsftpd-backdoor", False, attack_graph=_TEST_GRAPH)
    assert state.alert_history == [True, False]
```

### C-002 — detection_history per action

```python
def test_detection_history_per_action():
    state = EpisodeState()
    collect_feedback(state, "recon-syn-scan", True, attack_graph=_TEST_GRAPH)
    assert state.detection_history["recon-syn-scan"] == [True]
    collect_feedback(state, "recon-syn-scan", False, attack_graph=_TEST_GRAPH)
    assert state.detection_history["recon-syn-scan"] == [True, False]
```

### C-003 — action_id added to completed_actions

```python
def test_completed_actions_updated():
    state = EpisodeState()
    collect_feedback(state, "recon-syn-scan", False, attack_graph=_TEST_GRAPH)
    assert "recon-syn-scan" in state.completed_actions
```

### C-004 — step incremented by exactly 1

```python
def test_step_incremented():
    state = EpisodeState()
    assert state.step == 0
    collect_feedback(state, "recon-syn-scan", False, attack_graph=_TEST_GRAPH)
    assert state.step == 1
    collect_feedback(state, "exploit-vsftpd-backdoor", False, attack_graph=_TEST_GRAPH)
    assert state.step == 2
```

---

## User Story 2: Stage Progress Detection

### C-005 — stage_progress=True when successors unlocked

```python
def test_stage_progress_true():
    state = EpisodeState()
    result = collect_feedback(state, "recon-syn-scan", False, attack_graph=_TEST_GRAPH)
    assert result.stage_progress is True  # "exploit-vsftpd-backdoor" newly reachable
```

### C-006 — stage_progress=False when no new successors

```python
def test_stage_progress_false_terminal():
    state = EpisodeState(
        completed_actions={"recon-syn-scan", "exploit-vsftpd-backdoor"}
    )
    result = collect_feedback(state, "lateral-move-smb", False, attack_graph=_TEST_GRAPH)
    assert result.stage_progress is False  # "lateral-move-smb" has no successors
```

### C-007 — detected mirrors alert_fired

```python
def test_detected_mirrors_alert_fired():
    state = EpisodeState()
    r1 = collect_feedback(state, "recon-syn-scan", True, attack_graph=_TEST_GRAPH)
    assert r1.detected is True
    state2 = EpisodeState()
    r2 = collect_feedback(state2, "recon-syn-scan", False, attack_graph=_TEST_GRAPH)
    assert r2.detected is False
```

---

## User Story 3: Alert Category Tracking

### C-008 — category added when alert_fired=True and category provided

```python
def test_category_added_on_alert():
    state = EpisodeState()
    collect_feedback(state, "recon-syn-scan", True, attack_graph=_TEST_GRAPH, category="ET SCAN")
    assert "ET SCAN" in state.fired_categories
```

### C-009 — category NOT added when alert_fired=False

```python
def test_category_skipped_when_no_alert():
    state = EpisodeState()
    collect_feedback(state, "recon-syn-scan", False, attack_graph=_TEST_GRAPH, category="ET SCAN")
    assert "ET SCAN" not in state.fired_categories
```

### C-010 — category NOT added when category=None

```python
def test_category_skipped_when_none():
    state = EpisodeState()
    collect_feedback(state, "recon-syn-scan", True, attack_graph=_TEST_GRAPH, category=None)
    assert len(state.fired_categories) == 0
```

---

## Summary

| Contract | Story | What it tests                                    |
|----------|-------|--------------------------------------------------|
| C-001    | US1   | alert_history appended correctly                 |
| C-002    | US1   | detection_history per-action list grows          |
| C-003    | US1   | completed_actions includes new action            |
| C-004    | US1   | step += 1 on every call                          |
| C-005    | US2   | stage_progress=True (entry point → has successors) |
| C-006    | US2   | stage_progress=False (terminal node)             |
| C-007    | US2   | detected=alert_fired in FeedbackResult           |
| C-008    | US3   | fired_categories updated on alert+category       |
| C-009    | US3   | fired_categories unchanged when no alert         |
| C-010    | US3   | fired_categories unchanged when category=None    |
