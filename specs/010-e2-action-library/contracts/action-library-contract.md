# Action Library Contracts (F07)

## C-001 — Registry count

`len(REGISTRY.list_actions()) >= 15`

The registry MUST contain at least 15 distinct `ActionDefinition` entries after module import.

---

## C-002 — Unique action IDs

`len({a.action_id for a in REGISTRY.list_actions()}) == len(REGISTRY.list_actions())`

All `action_id` values MUST be unique. Duplicate IDs MUST raise `ValueError` at registry construction time (before any test or runtime code runs).

---

## C-003 — All six categories present

For each `cat` in `{"scan","brute","ssh","web","dns","exfil"}`:
`len(REGISTRY.actions_by_category(cat)) >= 1`

At least one action must exist in every required category.

---

## C-004 — get_action() round-trips

`REGISTRY.get_action(a.action_id) == a` for every `a` in `REGISTRY.list_actions()`

An action retrieved by its own ID must be identical to the original definition.

---

## C-005 — Non-empty parameters

`a.default_parameters != {}` for every `a` in `REGISTRY.list_actions()`

Every action must have at least one tunable parameter.

---

## C-006 — Description non-empty

`a.description.strip() != ""` for every `a`

Every action must carry a non-empty human-readable description.

---

## C-007 — suricata_category non-empty

`a.suricata_category.strip() != ""` for every `a`

Every action must declare which ET Open rule family it exercises.

---

## C-008 — to_action() produces valid Action

Given `a: ActionDefinition` and `ts = datetime.now(UTC)`:
`Action.model_validate(a.to_action(ts).model_dump())` succeeds without error.

The produced `Action` must satisfy the F03 contract (Pydantic validation passes).

---

## C-009 — to_action() preserves fields

`action.action_id == a.action_id`
`action.category == a.category`
`action.parameters == a.default_parameters`

Fields must be passed through without modification.

---

## C-010 — safety_guard() clean on registered library

`safety_guard(REGISTRY) == []`

The full registered library must produce zero safety violations.

---

## C-011 — safety_guard() flags external IP

Given an `ActionDefinition` with `default_parameters={"target": "8.8.8.8"}`:
`len(safety_guard(registry_with_bad_action)) >= 1`

An action referencing a publicly-routable IP must be flagged.

---

## C-012 — safety_guard() flags empty parameters

Given an `ActionDefinition` with `default_parameters={}`:
`len(safety_guard(registry_with_empty_params)) >= 1`

An action with no parameters must be flagged as structurally invalid.

---

## C-013 — get_action() KeyError on unknown ID

`REGISTRY.get_action("nonexistent_id")` raises `KeyError`

Lookup of an unregistered action_id must raise immediately.

---

## C-014 — actions_by_category() unknown category returns empty list

`REGISTRY.actions_by_category("nonexistent_cat") == []`

Filtering by an unknown category must return an empty list, not raise.

---

## C-015 — No I/O at import time

Importing `aatf.action_library` must not open any network socket, subprocess, or file handle. Verified by test isolation (monkeypatching `socket.socket` and `subprocess.Popen` to raise if called).
