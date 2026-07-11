# Tasks: Explainability Engine (F23)

**Input**: Design documents from `/specs/022-e6-explainability-engine/`  
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/explainability-contract.md ✅

**TDD**: All 12 contracts written upfront (T003), then implemented story-by-story.  
**Baseline**: 257 passed, 4 skipped, 6 failed (pre-existing Docker tests unchanged)  
**Target**: ≥269 passed, 4 skipped, 6 failed (C-010 parametrized ×8 → +19-20 pytest passes)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Confirm environment, record baseline, verify dependencies.

- [ ] T001 Record baseline suite state: `source /home/yuti/Adaptive-Adversarial-Testing-Framework/.venv/bin/activate && cd src && pytest --tb=no -q 2>&1 | tail -5` — confirm 257 passed, 4 skipped, 6 failed
- [ ] T002 Verify imports available: `python -c "from aatf.metrics import EpisodeRecord; from aatf.action_library import ActionRegistry, REGISTRY; print('OK')"` in venv — confirm no ImportError

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create stub module so test file can be imported without ImportError. MUST complete before any user story tests are written.

**⚠️ CRITICAL**: Both names (`ActionExplanation`, `explain_evasions`) must be importable from `aatf.explainability` BEFORE writing the test file, or pytest collection will fail with ImportError.

- [ ] T003 Create stub `src/aatf/explainability.py` with:
  ```python
  """Explainability engine — maps evaded actions to ranked remediation hints."""
  from __future__ import annotations
  from dataclasses import dataclass
  from aatf.action_library import ActionRegistry
  from aatf.metrics import EpisodeRecord

  @dataclass(frozen=True)
  class ActionExplanation:
      action_id: str
      suricata_category: str
      description: str
      evasion_count: int
      total_count: int
      evasion_rate: float
      remediation: str
      false_positive_risk: str

  def explain_evasions(
      records: list[EpisodeRecord],
      registry: ActionRegistry,
  ) -> list[ActionExplanation]:
      raise NotImplementedError
  ```
  Verify: `python -c "from aatf.explainability import ActionExplanation, explain_evasions; print('OK')"` in `src/` (with venv active)

- [ ] T004 Write all 12 contracts C-001..C-012 in `tests/test_explainability.py` (~150 LOC):

  **Helpers at module top:**
  ```python
  import dataclasses
  import pytest
  from aatf.action_library import ActionDefinition, ActionRegistry, REGISTRY
  from aatf.episode import StepRecord
  from aatf.explainability import ActionExplanation, explain_evasions
  from aatf.metrics import EpisodeRecord

  def _step(action_id: str, detected: bool) -> StepRecord:
      return StepRecord(action_id=action_id, detected=detected, stage_progress=0, reward=0.0)

  def _ep(*steps: StepRecord) -> EpisodeRecord:
      return EpisodeRecord(attacker_class="test", seed=0, steps=list(steps),
                           total_reward=0.0, completed=False, episode_index=0)

  def _reg(*defs: ActionDefinition) -> ActionRegistry:
      """Minimal stub registry from explicit ActionDefinition objects."""
      reg = ActionRegistry()
      for d in defs:
          reg._registry[d.action_id] = d  # or use the actual registration path
      return reg

  def _defn(action_id: str, suricata_category: str, description: str = "desc") -> ActionDefinition:
      return ActionDefinition(action_id=action_id, category="test",
                              description=description, default_parameters={},
                              suricata_category=suricata_category)
  ```

  **C-001 (US1 — field access):**
  ```python
  def test_c001_action_explanation_field_access():
      ex = ActionExplanation(
          action_id="ssh_brute_force_slow",
          suricata_category="ET BRUTE_FORCE",
          description="SSH brute-force probe",
          evasion_count=3,
          total_count=4,
          evasion_rate=0.75,
          remediation="tune thresholds",
          false_positive_risk="medium",
      )
      assert ex.action_id == "ssh_brute_force_slow"
      assert ex.suricata_category == "ET BRUTE_FORCE"
      assert ex.description == "SSH brute-force probe"
      assert ex.evasion_count == 3
      assert ex.total_count == 4
      assert ex.evasion_rate == pytest.approx(0.75)
      assert ex.remediation == "tune thresholds"
      assert ex.false_positive_risk == "medium"
  ```

  **C-002 (US1 — immutability):**
  ```python
  def test_c002_action_explanation_immutable():
      ex = ActionExplanation(action_id="x", suricata_category="ET SCAN",
                              description="d", evasion_count=1, total_count=1,
                              evasion_rate=1.0, remediation="r", false_positive_risk="f")
      with pytest.raises(dataclasses.FrozenInstanceError):
          ex.evasion_count = 99  # type: ignore[misc]
  ```

  **C-003 (US1 — importability): covered by module-level import above (no body needed beyond import)**
  ```python
  def test_c003_importable():
      # module-level import already validates this; assert names are callable
      assert callable(explain_evasions)
      assert isinstance(ActionExplanation, type)
  ```

  **C-004 (US2 — ranking by evasion_rate descending):**
  ```python
  def test_c004_ranking_by_evasion_rate():
      registry = ActionRegistry()
      # use real REGISTRY if scan_tcp and dns_recon exist, else build stubs
      reg = ActionRegistry.__new__(ActionRegistry)
      reg._registry = {
          "scan_tcp": _defn("scan_tcp", "ET SCAN"),
          "dns_recon": _defn("dns_recon", "ET DNS"),
      }
      records = [
          _ep(_step("scan_tcp", False), _step("scan_tcp", False),
              _step("scan_tcp", False), _step("scan_tcp", True)),   # 3/4 → 0.75
          _ep(_step("dns_recon", False), _step("dns_recon", True),
              _step("dns_recon", True), _step("dns_recon", True)),  # 1/4 → 0.25
      ]
      result = explain_evasions(records, reg)
      assert len(result) == 2
      assert result[0].action_id == "scan_tcp"
      assert result[1].action_id == "dns_recon"
      assert result[0].evasion_rate == pytest.approx(0.75)
      assert result[0].evasion_count == 3
      assert result[0].total_count == 4
  ```

  **C-005 (US2 — tie-break by action_id ascending):**
  ```python
  def test_c005_tiebreak_by_action_id():
      reg = ActionRegistry.__new__(ActionRegistry)
      reg._registry = {
          "zzz_action": _defn("zzz_action", "ET SCAN"),
          "aaa_action": _defn("aaa_action", "ET SCAN"),
      }
      records = [
          _ep(_step("zzz_action", False), _step("zzz_action", True)),  # 0.5
          _ep(_step("aaa_action", False), _step("aaa_action", True)),  # 0.5
      ]
      result = explain_evasions(records, reg)
      assert len(result) == 2
      assert result[0].action_id == "aaa_action"
      assert result[1].action_id == "zzz_action"
  ```

  **C-006 (US2 — evasion_rate=0 excluded):**
  ```python
  def test_c006_fully_detected_excluded():
      reg = ActionRegistry.__new__(ActionRegistry)
      reg._registry = {"scan_tcp": _defn("scan_tcp", "ET SCAN")}
      records = [_ep(_step("scan_tcp", True), _step("scan_tcp", True))]
      result = explain_evasions(records, reg)
      assert result == []
  ```

  **C-007 (US2 — empty records):**
  ```python
  def test_c007_empty_records():
      reg = ActionRegistry.__new__(ActionRegistry)
      reg._registry = {}
      assert explain_evasions([], reg) == []
  ```

  **C-008 (US2 — all steps detected across multiple episodes):**
  ```python
  def test_c008_all_steps_detected():
      reg = ActionRegistry.__new__(ActionRegistry)
      reg._registry = {
          "scan_tcp": _defn("scan_tcp", "ET SCAN"),
          "dns_recon": _defn("dns_recon", "ET DNS"),
      }
      records = [
          _ep(_step("scan_tcp", True), _step("dns_recon", True)),
          _ep(_step("scan_tcp", True), _step("dns_recon", True)),
      ]
      assert explain_evasions(records, reg) == []
  ```

  **C-009 (US2 — registry lookup populates suricata_category and description):**
  ```python
  def test_c009_registry_lookup():
      records = [_ep(_step("ssh_brute_force_slow", False))]
      result = explain_evasions(records, REGISTRY)
      defn = REGISTRY.get_action("ssh_brute_force_slow")
      assert len(result) == 1
      assert result[0].suricata_category == defn.suricata_category
      assert result[0].description == defn.description
  ```

  **C-010 (US3 — known category non-empty strings, parametrized ×8):**
  ```python
  @pytest.mark.parametrize("category", [
      "ET SCAN", "ET BRUTE_FORCE", "ET EXPLOIT", "ET DNS",
      "ET POLICY", "ET TROJAN", "ET WEB_CLIENT", "ET WEB_SERVER",
  ])
  def test_c010_known_category_non_empty(category: str):
      reg = ActionRegistry.__new__(ActionRegistry)
      reg._registry = {"act": _defn("act", category)}
      records = [_ep(_step("act", False))]
      result = explain_evasions(records, reg)
      assert len(result) == 1
      assert len(result[0].remediation) > 0
      assert len(result[0].false_positive_risk) > 0
  ```

  **C-011 (US3 — unknown category fallback non-empty):**
  ```python
  def test_c011_unknown_category_fallback():
      reg = ActionRegistry.__new__(ActionRegistry)
      reg._registry = {"custom_act": _defn("custom_act", "ET CUSTOM_UNKNOWN")}
      records = [_ep(_step("custom_act", False))]
      result = explain_evasions(records, reg)
      assert len(result) == 1
      assert len(result[0].remediation) > 0
      assert len(result[0].false_positive_risk) > 0
  ```

  **C-012 (US3 — same category yields identical strings):**
  ```python
  def test_c012_same_category_identical_strings():
      reg = ActionRegistry.__new__(ActionRegistry)
      reg._registry = {
          "action_a": _defn("action_a", "ET SCAN"),
          "action_b": _defn("action_b", "ET SCAN"),
      }
      records = [_ep(_step("action_a", False), _step("action_b", False))]
      result = explain_evasions(records, reg)
      assert len(result) == 2
      # find each by action_id (order may be alphabetical: action_a, action_b)
      a = next(r for r in result if r.action_id == "action_a")
      b = next(r for r in result if r.action_id == "action_b")
      assert a.remediation == b.remediation
      assert a.false_positive_risk == b.false_positive_risk
  ```

- [ ] T005 Verify red phase: `cd src && pytest ../tests/test_explainability.py -v --tb=short 2>&1 | tail -20` — confirm C-001..C-003 PASS (ActionExplanation stub is complete), C-004..C-012 FAIL (explain_evasions raises NotImplementedError). If C-001..C-003 fail, fix the ActionExplanation stub in explainability.py before proceeding.

  **Note on _reg helper**: If `ActionRegistry.__new__(ActionRegistry)` + `reg._registry = {}` doesn't work with the actual class (check action_library.py internals), use an alternative approach: subclass ActionRegistry or build ActionDefinition objects and register them via the real add/register method. Check the actual class implementation before writing the helper.

**Checkpoint**: Stub importable, 12 tests written, red phase confirmed.

---

## Phase 3: User Story 1 — Action Explanation Container (Priority: P1) 🎯 MVP

**Goal**: `ActionExplanation` is a frozen dataclass with all 8 fields accessible and immutable.

**Independent Test**: `pytest ../tests/test_explainability.py::test_c001_action_explanation_field_access ../tests/test_explainability.py::test_c002_action_explanation_immutable ../tests/test_explainability.py::test_c003_importable -v`

- [ ] T006 [US1] Verify `ActionExplanation` in `src/aatf/explainability.py` is complete (all 8 typed fields, `frozen=True`) — the stub from T003 should already satisfy US1; run C-001..C-003 and confirm all 3 pass. If any fail, fix the dataclass definition.

**Checkpoint**: C-001, C-002, C-003 green. ActionExplanation usable as a value type by F24.

---

## Phase 4: User Story 2 — Evasion Analysis (Priority: P2)

**Goal**: `explain_evasions` aggregates step data, filters zero-evasion actions, looks up registry metadata, ranks by evasion_rate desc / action_id asc.

**Independent Test**: `pytest ../tests/test_explainability.py -k "c004 or c005 or c006 or c007 or c008 or c009" -v`

- [ ] T007 [US2] Implement `explain_evasions` body (without remediation table yet) in `src/aatf/explainability.py`:
  - Step-level accumulator: `counts: dict[str, list[int]] = {}` → `{action_id: [evaded, total]}`
  - Walk `records` → each `record.steps` → `counts[step.action_id][1] += 1`; `if not step.detected: counts[step.action_id][0] += 1`
  - Filter: `if evaded == 0: continue`
  - Registry lookup: `defn = registry.get_action(action_id)` (let KeyError propagate per A2)
  - Placeholder: set `remediation=""`, `false_positive_risk=""` for now (US3 will fill these)
  - Build `ActionExplanation` with `evasion_rate=evaded/total`
  - Sort: `sorted(result, key=lambda x: (-x.evasion_rate, x.action_id))`
  - Return sorted list

- [ ] T008 [US2] Run pytest C-004..C-009: `cd src && pytest ../tests/test_explainability.py -k "c004 or c005 or c006 or c007 or c008 or c009" -v` — verify all 6 green. Fix any failures before proceeding.

**Checkpoint**: C-004..C-009 green. Evasion ranking and filtering verified.

---

## Phase 5: User Story 3 — Remediation and Risk Hints (Priority: P3)

**Goal**: `REMEDIATION_TABLE` covers all 8 `suricata_category` values; `_FALLBACK` covers unknowns; `explain_evasions` returns non-empty `remediation` and `false_positive_risk` for any evaded action.

**Independent Test**: `pytest ../tests/test_explainability.py -k "c010 or c011 or c012" -v`

- [ ] T009 [US3] Add `_FALLBACK` and `REMEDIATION_TABLE` module-level constants to `src/aatf/explainability.py` (above `ActionExplanation`), and update `explain_evasions` to replace the `remediation=""` placeholder:

  ```python
  _FALLBACK: tuple[str, str] = (
      "Review and update Suricata rule signatures for this technique category; "
      "consult the ET PRO ruleset documentation for coverage recommendations.",
      "Unknown: assess false-positive risk empirically against your environment's "
      "baseline traffic before enabling.",
  )

  REMEDIATION_TABLE: dict[str, tuple[str, str]] = {
      "ET SCAN": (
          "Review ET SCAN ruleset thresholds; consider lowering scan detection sensitivity "
          "or narrowing source IP ranges. Verify scan interval thresholds match your "
          "environment's normal discovery traffic.",
          "High: network scan rules frequently trigger on legitimate discovery tools and "
          "asset-management probes.",
      ),
      "ET BRUTE_FORCE": (
          "Enable or tighten ET BRUTE_FORCE rules; set login-attempt thresholds to match "
          "your environment's expected authentication volume. Consider adding detection for "
          "slow-rate credential stuffing.",
          "Medium: high-frequency legitimate login systems (CI/CD, SSO agents) may trigger "
          "brute-force rules.",
      ),
      "ET EXPLOIT": (
          "Activate and tune ET EXPLOIT signatures for the specific service version targeted. "
          "Ensure vulnerability scanner traffic is excluded from triggering these rules.",
          "Low: exploit signatures are highly specific; false positives are rare but possible "
          "on unusual protocol implementations.",
      ),
      "ET DNS": (
          "Enable ET DNS rules for zone transfer and subdomain enumeration; tune query-rate "
          "thresholds to your resolver's legitimate query volume.",
          "Medium: high-volume DNS resolvers and CDN prefetching can generate patterns "
          "resembling DNS reconnaissance.",
      ),
      "ET POLICY": (
          "Review ET POLICY rules for data-exfiltration patterns; enable DNS and HTTP "
          "exfiltration signatures and set volume thresholds appropriate to baseline traffic.",
          "High: policy rules covering large data transfers can trigger on legitimate backup "
          "or sync traffic.",
      ),
      "ET TROJAN": (
          "Enable ET TROJAN signatures covering HTTP-based C2 patterns; update rule sets "
          "frequently as evasion techniques evolve rapidly in this category.",
          "Low: trojan signatures are narrow; false positives are uncommon but possible with "
          "custom internal tooling using similar HTTP patterns.",
      ),
      "ET WEB_CLIENT": (
          "Enable ET WEB_CLIENT rules for XSS probe patterns; ensure your web application "
          "firewall is configured to complement Suricata detections.",
          "Medium: legitimate security scanners and browser automation tools may trigger "
          "XSS detection rules.",
      ),
      "ET WEB_SERVER": (
          "Enable ET WEB_SERVER directory scan and SQLi probe signatures; tune to exclude "
          "known-safe scanner IPs and internal penetration testing ranges.",
          "Medium: automated vulnerability scanners and web crawlers frequently trigger "
          "directory scan rules.",
      ),
  }
  ```

  Update the `explain_evasions` body: replace `remediation=""`, `false_positive_risk=""` with:
  ```python
  remediation, fpr = REMEDIATION_TABLE.get(defn.suricata_category, _FALLBACK)
  ```
  and set `false_positive_risk=fpr` in the `ActionExplanation` constructor.

- [ ] T010 [US3] Run pytest C-010..C-012: `cd src && pytest ../tests/test_explainability.py -k "c010 or c011 or c012" -v` — verify all pass (C-010 runs 8 parametrized cases). Fix any failures.

**Checkpoint**: C-010..C-012 green. All 3 user stories complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Code quality, suite integrity, commit.

- [ ] T011 Run ruff check: `cd src && ruff check ../tests/test_explainability.py aatf/explainability.py` — fix any reported issues (unused imports, wrong import sources, etc.)
- [ ] T012 Run ruff format: `cd src && ruff format ../tests/test_explainability.py aatf/explainability.py` — apply formatting
- [ ] T013 Run full suite: `cd src && pytest --tb=no -q 2>&1 | tail -5` — verify ≥269 passed, 4 skipped, 6 failed. The 6 pre-existing failures MUST remain unchanged.
- [ ] T014 Update tasks.md: mark all completed tasks [X]
- [ ] T015 Commit: `git add src/aatf/explainability.py tests/test_explainability.py specs/022-e6-explainability-engine/tasks.md && git commit -m "Add F23 explainability engine (022-e6-explainability-engine)"`
- [ ] T016 Merge to main: `git checkout main && git merge 022-e6-explainability-engine`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all story phases
- **US1 (Phase 3)**: Depends on Phase 2 (T003 stub must exist)
- **US2 (Phase 4)**: Depends on Phase 3 complete (ActionExplanation must be correct)
- **US3 (Phase 5)**: Depends on Phase 4 complete (explain_evasions body must exist)
- **Polish (Phase 6)**: Depends on Phase 5 complete (all tests green)

### User Story Dependencies

- **US1 (P1)**: Blocking — ActionExplanation is returned by explain_evasions; all other stories use it
- **US2 (P2)**: Depends on US1 — explain_evasions constructs ActionExplanation
- **US3 (P3)**: Depends on US2 — remediation fields are populated inside the explain_evasions body

### Within Each Phase

- Tests written (T004) BEFORE implementation (T007, T009)
- T005 red-phase verification before any story implementation
- T006 before T007 (confirm ActionExplanation is correct before testing full function)
- T007 before T009 (core aggregation before remediation table)

---

## Parallel Example: Foundational Phase

```bash
# T003 and T004 are the only blocking sequential tasks:
# T003 must complete before T004 (stub needed for import)
# T004 must complete before T005 (tests before red verification)
# No parallel opportunities in Phase 2 — single file, sequential
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational stub + all tests written
3. Complete Phase 3: Verify ActionExplanation correct (C-001..C-003 green)
4. **STOP**: ActionExplanation usable as value type by F24 already

### Incremental Delivery

1. Phase 1 + 2 → stub importable, all 12 tests written, red confirmed
2. Phase 3 → US1 green (3 tests)
3. Phase 4 → US2 green (+6 tests, 9 total)
4. Phase 5 → US3 green (+8 passes from C-010 parametrize, 12 contracts all green)
5. Phase 6 → polish, commit, merge

---

## Notes

- **_reg helper**: Check `ActionRegistry` implementation in `src/aatf/action_library.py` before writing the helper. If `_registry` is not a public dict, use the real registration method or create a minimal `ActionRegistry` subclass that accepts a dict. The real `REGISTRY` constant is used only for C-009.
- **C-010 parametrize**: Counts as one contract but produces 8 pytest passes. Total suite increase is 12 contracts + 7 extra parametrize passes = 19 net new passes (257 → 276 expected, well above ≥269 target).
- **ruff**: Watch for `Callable` from `typing` vs `collections.abc` (same issue caught in F21) and unused imports in test file.
- **Pre-existing failures**: The 6 Docker isolation failures MUST remain at 6 after this feature. If count changes, investigate before committing.
