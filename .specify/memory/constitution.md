<!--
SYNC IMPACT REPORT
==================
Version change: (template) → 1.0.0
Bump rationale: Initial ratification of the project constitution from the
  approved project proposal "Adaptive Adversarial Testing Framework".

Principles defined (7):
  I.   Safety & Isolation First (NON-NEGOTIABLE)
  II.  Reproducibility & Determinism (NON-NEGOTIABLE)
  III. Pluggable Defence Interface (NON-NEGOTIABLE)
  IV.  Scientific Validity & Test-First
  V.   Explainability as a First-Class Deliverable
  VI.  Observability & Honest Feedback
  VII. Phased Delivery Behind a Hard Gate

Added sections:
  - Technology Stack & Architecture Constraints
  - Development Workflow & Quality Gates
  - Governance

Removed sections: none (initial version).

Templates requiring updates:
  ✅ .specify/memory/constitution.md (this file)
  ✅ .specify/templates/plan-template.md — generic "Constitution Check" gate is
     compatible; principle IDs referenced by name, no edit required.
  ✅ .specify/templates/spec-template.md — scope/requirements sections compatible;
     no mandatory-section conflict introduced.
  ✅ .specify/templates/tasks-template.md — task categories (setup/test/core/
     integration/polish) accommodate safety, determinism, and explainability tasks.
  ⚠ README.md — currently a stub; SHOULD be expanded during Week 1 to reference
     this constitution and the one-command reproducible entry point.

Follow-up TODOs: none deferred. RATIFICATION_DATE set to first adoption date.
-->

# Adaptive Adversarial Testing Framework Constitution

This project builds a **safe, simulation-based measurement instrument** that evaluates an
intrusion-detection configuration (Suricata + ET Open) against an *adaptive, learning*
attacker, and explains the discovered weaknesses in defender-actionable terms. It is
defence-centric: the goal is to measure and explain *how* defences break so they can be
fixed — never to produce a usable attack tool. Every principle below exists to keep that
purpose intact in the generated code.

## Core Principles

### I. Safety & Isolation First (NON-NEGOTIABLE)

The system MUST NOT be capable of causing real-world harm, and this MUST be enforced
structurally, not by convention.

- All execution MUST occur inside a Docker / Docker Compose lab on an **internal-only**
  network with no route to the public internet or any host outside the lab. Compose files
  MUST declare networks as `internal: true`; no published host ports beyond what a local
  operator needs to read reports.
- Attack actions MUST be **defanged**: they emit harmless, lab-only traffic *shaped to
  resemble* a technique purely to test whether a rule fires. No real exploit payloads, no
  real malware, no credential theft, no destructive operations, and no live C2 are
  permitted anywhere in the codebase, tests, or fixtures.
- Action executors MUST target only lab-internal addresses. Any code path that could send
  traffic to an externally routable address MUST fail closed (raise and abort), and MUST be
  covered by a test asserting it fails closed.
- The action library is an abstraction over *categories of behaviour* (e.g. "SSH probe at
  N attempts / 60s"), not a collection of working exploits. Generated code MUST keep this
  abstraction; it MUST NOT be elaborated into weaponizable tooling.

Rationale: The proposal's central promise is "the output is not an attack tool, it is a
measurement instrument." If safety is left to documentation it will erode; it MUST be a
property of the architecture and the test suite.

### II. Reproducibility & Determinism (NON-NEGOTIABLE)

Anyone MUST be able to reproduce any reported result from a clean checkout.

- A single documented command MUST build the lab and run an experiment end to end
  (e.g. `make run` or `docker compose up` plus one entrypoint). No undocumented manual
  steps.
- Every source of randomness (attacker exploration, traffic timing jitter, ML training,
  data splits, NumPy/PyTorch/Python `random`) MUST be seeded from a single configurable
  seed. Given the same seed and pinned environment, runs MUST produce identical metrics.
- Dependencies MUST be pinned (e.g. `requirements.txt` compiled via pip-tools with hashes,
  or an equivalent lockfile). Suricata and ET Open ruleset versions MUST be pinned to a
  specific tag/snapshot and recorded in run metadata.
- Every experiment run MUST emit a run-manifest capturing seed, dependency versions,
  ruleset version, config, and git commit, written alongside its outputs.

Rationale: Reproducibility is both a stated objective (O5) and a Phase 1 gate criterion.
Non-determinism would make Adaptation Gain and Blind-Spot Precision unmeasurable.

### III. Pluggable Defence Interface (NON-NEGOTIABLE)

The defence MUST sit behind a single stable interface so that swapping Suricata for an ML
detector (Phase 2) requires adding one class, not rewriting the loop.

- A `Defence` abstraction MUST expose a uniform contract: given an executed action /
  observed traffic, return a structured detection result. The contract MUST be rich enough
  to represent **both** a binary alert (Suricata: detected + responsible rule id(s)) **and**
  a continuous anomaly score (ML NIDS: score in [0,1]).
- The attacker brain, action executor, feedback collector, evaluator, explainability engine,
  and report generator MUST depend only on this interface and on shared data contracts —
  never on Suricata-specific internals.
- Phase 2 MUST be achievable by implementing one new `Defence` subclass plus its
  explainability adapter, reusing every other component unchanged (hypothesis H4).

Rationale: This interface is the architectural hinge of the whole proposal. Getting it
wrong forces a rewrite for Phase 2 and breaks the "one extensible instrument" deliverable.

### IV. Scientific Validity & Test-First

Results MUST be trustworthy, and the code that produces them MUST be tested before it is
written where the contract is known.

- Tests are written before implementation for every component contract (attacker update
  rule, reward computation, context-vector construction, eve.json parsing, metric
  computation, explainability mapping). Contracts are locked by tests, then implemented.
- **Ground-truth validation is mandatory**: an experiment harness MUST be able to
  deliberately disable a known set of rules, run, and verify the report flags exactly those
  rules as gaps. Blind-Spot Precision MUST be computed against this known set.
- **Statistical honesty is mandatory**: every headline metric MUST be reported across
  multiple seeded repetitions with dispersion (confidence intervals) and, where a claim of
  improvement is made (e.g. Adaptation Gain), a significance test. Single-run numbers MUST
  NOT be presented as results.
- The real Suricata + ET Open pipeline is the judge of record. Detection MUST be derived
  from actual `eve.json` output in integration runs. Stubbed/synthetic detectors are
  permitted only as clearly-labelled unit-test doubles, never as a substitute for the real
  defence in reported experiments.

Rationale: The project's value is measurement. A plausible-but-fabricated number is worse
than no number. Ground-truth validation and seeded statistics are what separate this from a
demo.

### V. Explainability as a First-Class Deliverable

The headline output is not "we evaded the IDS" but "here is exactly how, which rule was
responsible, and how to fix it."

- For every evaded action, the explainability engine MUST map it to the responsible
  rule/threshold (or, for the ML detector, the responsible features) and produce a concrete,
  ranked remediation with an associated false-positive risk note.
- Reports MUST be generated automatically (Markdown/HTML via templating), reproducibly,
  and MUST cite specific rule identifiers (e.g. ET Open SIDs) and observed evasion rates.
- The explainability layer MUST consume only the structured detection contract and logged
  experiment data — it MUST NOT re-run attacks or depend on defence internals — so it works
  unchanged across Phase 1 and Phase 2.

Rationale: This is the project's differentiator (Section 12) and objective O4/O8. A report
that merely demonstrates evasion fails the core thesis.

### VI. Observability & Honest Feedback

The feedback loop is the heart of the system; it MUST be transparent and faithful.

- The feedback collector MUST compute reward strictly from observed signals: detected →
  −1.0; undetected with stage progress → +1.0; undetected without progress → −0.1 (Phase 1).
  Phase 2 reward = progress − cumulative anomaly penalty over a suspicion budget. The reward
  function MUST live in one place and be unit-tested against worked examples.
- Every episode MUST log structured records (JSON/Lines) of context, chosen action,
  detection result, reward, and updated state — sufficient to replay analysis offline
  without re-running the lab.
- Metrics (Detection Rate, Robustness Score, Adaptation Gain, Blind-Spot Precision,
  Convergence Episodes; Phase 2: ROC-AUC, Cumulative Anomaly Exposure) MUST be computed by
  the offline evaluator from these logs, not hand-assembled.
- Logs MUST distinguish "no rule covered this" from "a rule existed but did not fire" so the
  explainability engine can classify true blind spots versus threshold/load failures.

Rationale: A learning loop that silently misreports its reward or detection signal will
"learn" the wrong thing and invalidate every downstream metric.

### VII. Phased Delivery Behind a Hard Gate

Phase 1 MUST be a complete, defensible standalone artifact; Phase 2 is gated.

- Phase 1 scope is fixed: Suricata + ET Open defence, a lightweight host event log,
  ≥15 defanged actions, a 4-stage attack graph (recon → initial access → lateral movement →
  exfiltration), a LinUCB contextual-bandit attacker, an optional tabular Q-learning
  comparison, the explainability report with ground-truth validation, and reproducibility.
- Phase 2 (ML anomaly detector + RL/DQN attacker + unified report) MUST NOT begin in code
  until the Phase 1 gate passes: **Adaptation Gain ≥ 15 percentage points**, **Blind-Spot
  Precision ≥ 0.8**, and **one-command reproducibility under a fixed seed**.
- If the gate is not met, Phase 1 still MUST ship as a coherent, working instrument; Phase 2
  becomes documented future work. No half-built Phase 2 code may compromise Phase 1
  shippability.

Rationale: The proposal explicitly defines this gate (Section 15/16). It protects the
guaranteed deliverable from being destabilised by the high-risk extension.

## Technology Stack & Architecture Constraints

- **Language**: Python 3.1x for all components.
- **Lab**: Docker + Docker Compose, internal-only network, no external connectivity.
- **Defence (Phase 1)**: Suricata with a pinned ET Open ruleset; `eve.json` is the alert
  source of record. A lightweight host event log (auditd-style) provides the secondary
  EDR-like signal.
- **Attacker (Phase 1)**: LinUCB contextual bandit (chosen over Thompson Sampling for
  interpretable linear weights that feed the report); optional tabular Q-learning over the
  attack graph as a comparison. Implemented with NumPy / scikit-learn + custom code.
- **Phase 2**: ML anomaly detector (autoencoder or isolation forest) and an RL attacker
  (DQN), built with PyTorch + scikit-learn, both behind the Principle III interfaces.
- **Data & reporting**: NumPy, pandas, Matplotlib for metrics/plots; Jinja2 for
  Markdown/HTML report generation.
- **Tooling**: pip-tools for pinned deps, pytest for tests, fixed seeds throughout.
- **Architecture**: Two layers MUST remain separated — (1) the live experiment loop inside
  the lab (attacker brain → action executor → lab network → defences → feedback collector)
  and (2) the offline analysis pipeline (evaluator → explainability engine → report
  generator). The offline layer MUST operate purely on logged artifacts.
- The context vector MUST include the proposal's feature families: alert-history,
  attack-progress, technique-history (per-technique rolling detection rate), timing, and
  rule-category-fired signals. Its construction MUST be a single tested function.

## Development Workflow & Quality Gates

- **Plan/Tasks compliance**: Every `/sp.plan` output MUST pass a Constitution Check before
  task generation. A plan that introduces external network access, non-determinism,
  defence-specific coupling in shared components, real exploit code, or unvalidated metrics
  MUST be revised or carry an explicit, justified entry in the plan's Complexity Tracking.
- **Definition of done for a feature**: contract tests written first and passing; integration
  path exercised against the real Suricata pipeline where applicable; reward/metric code unit
  tested against worked examples; run-manifest emitted; report regenerates deterministically;
  no new external-network capability; docs/README updated for any new entry point.
- **Reviews** MUST verify the four non-negotiables (safety isolation, determinism, pluggable
  interface integrity, scientific validity) on every change that touches the loop, the
  defence interface, the reward/metrics, or the report.
- **Existing scaffold**: the current `main.py`, `attacker/`, `defender/`, and `environment/`
  modules are a throwaway prototype (random-probability "detector", non-bandit update rule).
  They MUST be replaced by the architecture above, not extended; they are not a contract.

## Governance

- This constitution supersedes ad-hoc practice. Where a spec, plan, or task conflicts with
  it, the constitution wins; the conflicting artifact MUST be corrected.
- **Amendments** require: a written rationale, a version bump per the policy below, an update
  to this file, and propagation to dependent templates (`plan-template.md`,
  `spec-template.md`, `tasks-template.md`) plus a refreshed Sync Impact Report.
- **Versioning policy** (semantic):
  - MAJOR — removal or backward-incompatible redefinition of a principle/governance rule.
  - MINOR — a new principle/section or materially expanded mandatory guidance.
  - PATCH — clarifications and wording that do not change obligations.
- **Compliance review**: `/sp.plan` and `/sp.analyze` MUST report constitution alignment.
  Any NON-NEGOTIABLE violation is a hard blocker, not a tradeoff to be argued in review.
- **Runtime guidance**: agent-specific operational notes belong in agent guidance files
  (e.g. `CLAUDE.md`) and the README, not in this constitution; those files MUST stay
  consistent with the principles here.

**Version**: 1.0.0 | **Ratified**: 2026-06-13 | **Last Amended**: 2026-06-13
