# Adaptive Adversarial Testing Framework — Requirements & Backlog

This document decomposes the approved project proposal (`Draft_proposal.pdf`) into **Epics**
and **Stories** that drive the spec-kit pipeline. It is the master index that maps each story
to a future feature spec.

- **Story = feature = one spec file.** Each story below becomes a spec via `/sp.specify`,
  which creates `specs/NNN-<short-name>/spec.md` on branch `NNN-<short-name>`.
- Each spec then flows through `/sp.plan` → `/sp.tasks` → `/sp.implement`.
- The **Feature #** column is the suggested creation order; spec-kit auto-numbers features in
  the order they are created, so following this order keeps numbering aligned.
- Every story cites the **constitution principle(s)** (`.specify/memory/constitution.md`) and
  **proposal objective(s)** it serves, for traceability.

Legend: principles **I–VII**; objectives **O1–O8**; research questions **RQ1–RQ4**.
NON-NEGOTIABLE principles: **I** (Safety/Isolation), **II** (Reproducibility), **III**
(Pluggable Defence), **IV** (Scientific Validity).

---

# PHASE 1 — Core Instrument (must ship)

Phase 1 is the guaranteed deliverable: a safe, isolated lab in which an adaptive
contextual-bandit attacker is measured against a real Suricata + ET Open ruleset, producing a
validated, defender-actionable blind-spot report — fully reproducible from one command.

## Phase 1 Epic Index

| Epic | Title | Stories | Primary principles / objectives |
|------|-------|---------|---------------------------------|
| E0 | Foundation & Reproducibility | F01–F03 | II, III; O5 |
| E1 | Isolated Lab Environment | F04–F06 | I; O1, O5 |
| E2 | Attack Surface (Actions & Graph) | F07–F09 | I; O1 |
| E3 | Defence Interface & Detectors | F10–F12 | III, VI; O1 |
| E4 | Feedback Loop & Experiment Engine | F13–F16 | VI; O2 |
| E5 | Adaptive Attacker Brain | F17–F19 | IV; O2, O3, RQ1, RQ3 |
| E6 | Analysis, Explainability & Reporting | F20–F24 | IV, V; O4, RQ1, RQ2 |
| E7 | Phase 1 Gate & Hardening | F25–F26 | II, VII; O5 |

**Critical path:** E0 → E1 → E3 (interface + Suricata adapter) → E2 → E4 → E5 → E6 → E7 gate.

---

## E0 — Foundation & Reproducibility

Cross-cutting scaffolding so every later story inherits determinism, safety hooks, and shared
data shapes. Serves Principle II (Reproducibility) and Principle III (shared contracts).

### F01 — Project scaffold & pinned dependencies
- **short-name:** `e0-project-scaffold`
- **Goal:** Establish the Python package layout, pinned dependency management, and the test +
  entrypoint skeleton that all other features build on.
- **Acceptance criteria:**
  - `src/` package layout with a clear module boundary per architecture layer (live loop vs
    offline analysis).
  - Dependencies pinned via pip-tools (`requirements.in` → `requirements.txt` with hashes);
    Python 3.1x.
  - `pytest` configured and runnable; a trivial test passes in CI-style invocation.
  - `Makefile` (or equivalent) with placeholder targets: `setup`, `test`, `run`.
  - `.gitignore` covering `__pycache__`, logs, generated reports, virtualenvs.
- **Depends on:** none. **Serves:** II; O5.

### F02 — Configuration & seed management
- **short-name:** `e0-config-seeding`
- **Goal:** A single configuration surface and one global seed that makes every run
  deterministic, plus a run-manifest recording provenance.
- **Acceptance criteria:**
  - One typed config (dataclass/pydantic + YAML) for all tunables (episodes, seed, paths,
    thresholds).
  - A single `seed_everything(seed)` propagating to Python `random`, NumPy (and PyTorch in
    Phase 2); documented as the only randomness entry point.
  - Run-manifest writer captures: seed, dependency versions, Suricata + ET Open ruleset
    version, git commit, config snapshot; written next to run outputs.
  - Test: two runs with the same seed produce identical manifest-relevant outputs.
- **Depends on:** F01. **Serves:** II; O5.

### F03 — Core data contracts
- **short-name:** `e0-core-contracts`
- **Goal:** Define the shared, typed data structures every component exchanges, so the loop
  and the offline pipeline never couple to a specific defence.
- **Acceptance criteria:**
  - Typed schemas for: `Action`, `DetectionResult`, `ContextVector`, `EpisodeRecord`,
    `RunManifest`.
  - `DetectionResult` MUST represent **both** a binary alert with responsible rule id(s)
    (Suricata) **and** a continuous anomaly score in [0,1] (Phase 2 ML) — one shape, both
    paradigms.
  - `EpisodeRecord` is JSONL-serialisable and round-trips losslessly (test).
  - Contracts have no dependency on Suricata or any concrete detector.
- **Depends on:** F01. **Serves:** III, IV, VI.

---

## E1 — Isolated Lab Environment

The safe, sealed environment in which everything runs. Serves Principle I (Safety/Isolation)
and objective O1.

### F04 — Internal-only Docker lab
- **short-name:** `e1-docker-lab`
- **Goal:** A Docker Compose lab on an internal-only network with no route to the public
  internet.
- **Acceptance criteria:**
  - Compose file declares the experiment network with `internal: true`; no published host
    ports beyond what a local operator needs to read reports.
  - Service skeleton for attacker/executor, defence (Suricata), and log collection.
  - Healthchecks confirm services are up before an experiment starts.
  - `docker compose up` brings the lab to a ready state from a clean checkout.
- **Depends on:** F01. **Serves:** I; O1, O5.

### F05 — Suricata + pinned ET Open ruleset
- **short-name:** `e1-suricata-etopen`
- **Goal:** Run Suricata as the detection judge of record, consuming a pinned ET Open ruleset
  and emitting `eve.json`.
- **Acceptance criteria:**
  - Suricata service configured with a pinned ET Open ruleset version (recorded in manifest).
  - `eve.json` alerts are produced and accessible to the feedback collector.
  - A documented hook to enable/disable specific rules by SID (needed for ground-truth
    validation, F22).
  - Smoke test: a known-malicious-shaped probe triggers an expected SID.
- **Depends on:** F04. **Serves:** I; O1.

### F06 — Isolation verification
- **short-name:** `e1-isolation-verify`
- **Goal:** Prove, automatically, that nothing can reach outside the lab and that executors
  fail closed on external targets.
- **Acceptance criteria:**
  - Automated test asserts no egress from the experiment network (no external route).
  - Test asserts any attempt to target an externally routable address raises and aborts
    (fail-closed), per Principle I.
  - Runs as part of the standard test suite, not a manual check.
- **Depends on:** F04. **Serves:** I.

---

## E2 — Attack Surface (Actions & Graph)

The defanged techniques the attacker can choose from and the staged structure over them.
Serves objective O1; bounded hard by Principle I.

### F07 — Defanged action library (≥15 actions)
- **short-name:** `e2-action-library`
- **Goal:** A library of at least 15 abstract, **defanged** attack actions spanning the
  relevant categories.
- **Acceptance criteria:**
  - ≥15 actions across categories (e.g. scan, login/brute, web, SSH, DNS, exfil), each an
    abstraction over a *behaviour* (e.g. "SSH probe at N attempts / 60s"), not a working
    exploit.
  - Each action is parameterised where the proposal needs it (rate, timing, volume) to enable
    threshold-evasion behaviour.
  - No real exploit payloads, malware, or destructive operations anywhere (test/lint guard).
- **Depends on:** F03. **Serves:** I; O1.

### F08 — Action executor
- **short-name:** `e2-action-executor`
- **Goal:** Translate an abstract action into harmless, lab-only network traffic.
- **Acceptance criteria:**
  - Executor maps each `Action` to defanged traffic emitted **only** to lab-internal
    addresses.
  - Internal-target guard: external/routable targets fail closed (ties to F06).
  - Deterministic under seed (timing jitter is seeded).
- **Depends on:** F07, F04. **Serves:** I; O1.

### F09 — 4-stage attack graph
- **short-name:** `e2-attack-graph`
- **Goal:** Structure actions into the staged campaign the attacker must progress through.
- **Acceptance criteria:**
  - Four stages: recon → initial access → lateral movement → exfiltration, each with its
    technique set.
  - Progression rules: a stage must be completed before the next is attempted; "progress" is
    well-defined for the reward function.
  - Exposes current stage / stages-completed / actions-this-stage for the context vector.
- **Depends on:** F07. **Serves:** O1.

---

## E3 — Defence Interface & Detectors

The architectural hinge that lets Phase 2 swap detectors without rewriting the loop. Serves
Principle III (Pluggable Defence) and VI (Honest Feedback).

### F10 — Pluggable Defence interface
- **short-name:** `e3-defence-interface`
- **Goal:** Define the single stable `Defence` contract every component depends on.
- **Acceptance criteria:**
  - Abstract `Defence` exposing a uniform method: executed action / observed traffic →
    `DetectionResult`.
  - Contract is rich enough for binary alert + rule id(s) **and** continuous anomaly score.
  - All downstream consumers (collector, evaluator, explainability) depend only on this
    interface, never on a concrete detector.
- **Depends on:** F03. **Serves:** III.

### F11 — Suricata defence adapter
- **short-name:** `e3-suricata-adapter`
- **Goal:** Implement the `Defence` interface over real Suricata `eve.json`.
- **Acceptance criteria:**
  - Parses `eve.json` into `DetectionResult` with the responsible SID(s).
  - Distinguishes "no rule covered this behaviour" from "a rule exists but did not fire"
    (needed to classify true blind spots vs threshold/load failures — Principle VI).
  - Integration test against the running Suricata service (F05), not a stub.
- **Depends on:** F10, F05. **Serves:** III, VI.

### F12 — Host event log signal
- **short-name:** `e3-host-event-log`
- **Goal:** Provide the lightweight, EDR-like secondary signal for host-level actions.
- **Acceptance criteria:**
  - Auditd-style host event capture for relevant actions, surfaced into the context.
  - Available to the feedback collector alongside Suricata alerts.
- **Depends on:** F04, F03. **Serves:** O1.

---

## E4 — Feedback Loop & Experiment Engine

The heart of the system: the per-episode cycle that turns detection into reward and learning.
Serves Principle VI (Honest Feedback) and objective O2.

### F13 — Context vector builder
- **short-name:** `e4-context-vector`
- **Goal:** One tested function producing the full context vector the attacker observes.
- **Acceptance criteria:**
  - Includes all proposal feature families (§7.4): alert-history, attack-progress,
    technique-history (per-technique rolling detection rate), timing, rule-category-fired
    signals.
  - Pure, deterministic, unit-tested against worked examples.
- **Depends on:** F03, F09. **Serves:** VI.

### F14 — Reward function
- **short-name:** `e4-reward-function`
- **Goal:** The single, authoritative reward computation.
- **Acceptance criteria:**
  - Phase 1 rule: detected → −1.0; undetected + stage progress → +1.0; undetected + no
    progress → −0.1.
  - Lives in exactly one place; unit-tested against worked examples for each branch.
- **Depends on:** F03, F09. **Serves:** VI.

### F15 — Feedback collector
- **short-name:** `e4-feedback-collector`
- **Goal:** Gather observed signals and convert them into the reward + next state.
- **Acceptance criteria:**
  - Reads Suricata `DetectionResult` (F11), host events (F12), and (Phase 2) ML score.
  - Computes reward via F14 and updates state for the next context (F13).
- **Depends on:** F11, F12, F13, F14. **Serves:** VI.

### F16 — Episode orchestrator & logging
- **short-name:** `e4-episode-loop`
- **Goal:** The runnable experiment loop with episode/run lifecycle and structured logging.
- **Acceptance criteria:**
  - Implements the cycle: build context → attacker chooses → executor emits → defence detects
    → collector computes reward → attacker updates → log → repeat.
  - Emits one `EpisodeRecord` (JSONL) per step with context, action, detection, reward, state
    — sufficient to replay analysis offline without rerunning the lab.
  - Episode/run lifecycle with the run-manifest (F02) attached.
- **Depends on:** F08, F15, F02; (attacker via F17). **Serves:** VI; O2.

---

## E5 — Adaptive Attacker Brain

The learning agent and the baselines it must beat. Serves objectives O2/O3 and RQ1/RQ3 under
Principle IV.

### F17 — Attacker interface + baselines
- **short-name:** `e5-attacker-baselines`
- **Goal:** A common attacker policy interface plus the non-learning baselines for comparison.
- **Acceptance criteria:**
  - `Attacker` interface: `choose_action(context)` / `update(context, action, reward)`.
  - Random baseline and fixed-script baseline implemented behind the interface.
  - Drop-in usable by the episode orchestrator (F16).
- **Depends on:** F03, F13. **Serves:** O2; RQ1.

### F18 — LinUCB contextual bandit
- **short-name:** `e5-linucb-attacker`
- **Goal:** The core adaptive attacker that learns to evade detection from feedback.
- **Acceptance criteria:**
  - LinUCB implementation (expected reward + uncertainty bonus) over the context vector.
  - Learned per-technique linear weights are accessible for the explainability report
    (the interpretability reason LinUCB was chosen over Thompson Sampling).
  - Demonstrably reduces detection rate over episodes vs the random baseline (seeded).
- **Depends on:** F17. **Serves:** O2; RQ1.

### F19 — Tabular Q-learning (stretch comparison)
- **short-name:** `e5-qlearning-attacker`
- **Goal:** A simple planning agent to test whether sequential planning beats greedy
  per-step selection against stateless rules.
- **Acceptance criteria:**
  - Tabular Q-learning over the attack graph behind the `Attacker` interface.
  - Comparable head-to-head with LinUCB on the same metrics (feeds RQ3).
- **Depends on:** F17, F09. **Serves:** O3; RQ3. *(Stretch — may be deferred without
  blocking the gate.)*

---

## E6 — Analysis, Explainability & Reporting

The offline pipeline that turns logs into validated, defender-actionable output. Operates only
on logged artifacts (Principle V). Serves objective O4 and RQ1/RQ2 under Principle IV.

### F20 — Evaluator & metrics
- **short-name:** `e6-evaluator-metrics`
- **Goal:** Compute the Phase 1 metrics from episode logs.
- **Acceptance criteria:**
  - Detection Rate, Robustness Score (steady-state), Adaptation Gain (baseline vs learner),
    Convergence Episodes — all computed from `EpisodeRecord` logs, not hand-assembled.
  - Deterministic given the same logs.
- **Depends on:** F16. **Serves:** IV; O4, RQ1, RQ3.

### F21 — Statistical rigor layer
- **short-name:** `e6-statistical-rigor`
- **Goal:** Ensure reported numbers are real, not lucky single runs.
- **Acceptance criteria:**
  - Orchestrates multiple seeded repetitions; reports dispersion (confidence intervals).
  - Significance test for improvement claims (e.g. Adaptation Gain).
  - Single-run numbers are never presented as results.
- **Depends on:** F20. **Serves:** IV.

### F22 — Ground-truth validation harness
- **short-name:** `e6-ground-truth-validation`
- **Goal:** Validate that the report finds real gaps by checking it against deliberately
  disabled rules.
- **Acceptance criteria:**
  - Harness deliberately disables a known set of SIDs (via F05 hook), runs, and verifies the
    report flags exactly those as gaps.
  - Computes Blind-Spot Precision against the known disabled set.
- **Depends on:** F05, F23. **Serves:** IV; RQ2.

### F23 — Explainability engine
- **short-name:** `e6-explainability-engine`
- **Goal:** Map each evaded action to the responsible rule/threshold and a concrete fix.
- **Acceptance criteria:**
  - For every evaded action: responsible SID/threshold (or, Phase 2, responsible features) +
    ranked remediation + false-positive-risk note.
  - Consumes only the structured detection contract and logged data; no rerun, no defence
    internals (works unchanged in Phase 2).
- **Depends on:** F11, F16. **Serves:** V; O4, RQ2.

### F24 — Report generator
- **short-name:** `e6-report-generator`
- **Goal:** Produce the automated, reproducible blind-spot report.
- **Acceptance criteria:**
  - Jinja2 Markdown/HTML report citing specific SIDs and observed evasion rates.
  - Regenerates deterministically from the same logs.
- **Depends on:** F23, F20. **Serves:** V; O4.

---

## E7 — Phase 1 Gate & Hardening

Lock in the must-ship deliverable and evaluate the gate. Serves Principles II/VII and O5.

### F25 — One-command reproducibility
- **short-name:** `e7-repro-oneshot`
- **Goal:** The entire experiment runs from a clean checkout with a single command and
  identical results under a fixed seed.
- **Acceptance criteria:**
  - `make run` (or one documented entrypoint) builds the lab and runs an experiment end to
    end, producing metrics + report.
  - Identical results under a fixed seed across machines.
  - README documents the single command and expected outputs.
- **Depends on:** F16, F24. **Serves:** II; O5.

### F26 — Phase 1 gate evaluation
- **short-name:** `e7-phase1-gate`
- **Goal:** Automated evaluation of the Phase 1 → Phase 2 gate criteria.
- **Acceptance criteria:**
  - Computes and reports: Adaptation Gain ≥ 15 percentage points; Blind-Spot Precision ≥ 0.8;
    one-command reproducibility under fixed seed.
  - Emits a clear pass/fail gate report.
- **Depends on:** F21, F22, F25. **Serves:** VII; O5.

---

## Phase 1 Gate (decision point)

Phase 2 MUST NOT begin in code until **all** hold (proposal §15/16, Principle VII):

| Criterion | Threshold | Tied to |
|-----------|-----------|---------|
| Adaptation Gain | ≥ 15 percentage points | RQ1 |
| Blind-Spot Precision | ≥ 0.8 | RQ2 |
| Reproducibility | one command, identical under fixed seed | O5 |

If not met, Phase 1 ships as a complete standalone artifact and Phase 2 becomes documented
future work.

---

# PHASE 2 — ML Defence Extension (gated; do not spec until the gate passes)

Phase 2 reuses the entire Phase 1 lab, action library, feedback loop, and reporting pipeline,
adding advanced AI on both sides via the pluggable interfaces. It is a high-value extension,
not a prerequisite for delivery.

## Phase 2 Epic Index

| Epic | Title | Stories | Primary principles / objectives |
|------|-------|---------|---------------------------------|
| E8 | ML Anomaly Defence | F27 | III; O6, RQ4 |
| E9 | Reinforcement-Learning Attacker | F28 | IV; O7 |
| E10 | Unified Reporting | F29 | V; O8 |

---

## E8 — ML Anomaly Defence

### F27 — ML anomaly detector behind the Defence interface
- **short-name:** `e8-ml-anomaly-detector`
- **Goal:** Add a learned anomaly detector that produces continuous scores, plugged in via the
  same `Defence` interface — adding one class, reusing everything else (validates H4).
- **Acceptance criteria:**
  - Autoencoder or isolation forest (PyTorch / scikit-learn) trained on normal lab traffic.
  - Implements `Defence`, returning a continuous anomaly score in [0,1].
  - No changes required to the loop, executor, or report pipeline beyond the new class + its
    explainability adapter.
  - ROC-AUC computed for normal vs attacker traffic.
- **Depends on:** F10 (interface), Phase 1 gate passed. **Serves:** III; O6, RQ4.

---

## E9 — Reinforcement-Learning Attacker

### F28 — RL/DQN attacker with suspicion budget
- **short-name:** `e9-rl-dqn-attacker`
- **Goal:** An RL attacker that plans sequences to manage a cumulative suspicion budget against
  the continuous ML detector.
- **Acceptance criteria:**
  - DQN agent behind the `Attacker` interface.
  - Reward = progress made − cumulative anomaly-score penalty (suspicion budget).
  - Metric: Cumulative Anomaly Exposure (lower = stealthier) reported with statistical rigor.
- **Depends on:** F17 (interface), F27. **Serves:** IV; O7.

---

## E10 — Unified Reporting

### F29 — Unified blind-spot report
- **short-name:** `e10-unified-report`
- **Goal:** One report covering both detection paradigms (Suricata rules + ML-NIDS features).
- **Acceptance criteria:**
  - Extends the report generator to detail which features the RL attacker exploited to fool
    the ML defence and how to retrain to stop it.
  - Reuses the Phase 1 explainability + reporting pipeline.
- **Depends on:** F24, F27, F28. **Serves:** V; O8.

---

# Traceability summary

| Objective | Stories |
|-----------|---------|
| O1 (lab + actions) | F04, F05, F07, F08, F09, F12 |
| O2 (adaptive attacker) | F16, F17, F18 |
| O3 (planning comparison) | F19 |
| O4 (report) | F20, F23, F24 |
| O5 (safety + reproducibility) | F01, F02, F04, F25, F26 |
| O6 (ML defence) | F27 |
| O7 (RL attacker) | F28 |
| O8 (upgraded report) | F29 |

| Research question | Validated by |
|-------------------|--------------|
| RQ1 (adaptive vs scripted) | F18 vs F17 baseline → Adaptation Gain (F20/F21) |
| RQ2 (accurate explanation) | F22 ground-truth → Blind-Spot Precision |
| RQ3 (planning value) | F19 vs F18 (F20) |
| RQ4 (generalises to ML detector) | F27 via the F10 interface |

# How to execute this backlog

1. Run `/sp.specify` once per story, in Feature-# order, using the story's **short-name** and
   goal/acceptance criteria as the input. Short-names are prefixed with the epic id
   (`eN-`) so the flat `specs/NNN-<short-name>/` layout visibly groups by epic, e.g.
   `specs/001-e0-project-scaffold/`, `specs/004-e1-docker-lab/`. (spec-kit has no native
   epic container; `specs/` is flat and globally numbered — the epic layer lives in this
   document and in the slug prefix.)
2. For each created spec: `/sp.clarify` (optional) → `/sp.plan` → `/sp.tasks` → `/sp.implement`.
3. `/sp.plan` runs the Constitution Check gate; any NON-NEGOTIABLE violation is a hard blocker.
4. Stop at the Phase 1 gate (F26). Only spec Phase 2 (F27–F29) if the gate passes.
