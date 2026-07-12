# Feature Specification: ML Anomaly Defence

**Feature Branch**: `027-e8-ml-anomaly-detector`
**Created**: 2026-07-12
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Anomaly Detection Without Rule Changes (Priority: P1)

A security researcher wants to detect attacker traffic without writing or maintaining
detection rules. The system learns what "normal" traffic looks like from a baseline, then
flags deviations automatically. No rule authoring or signature management is required.

**Why this priority**: Core value of Phase 2 — demonstrates the framework can defend
with a learned model, not just hand-written rules. Without this, E8 has no deliverable.

**Independent Test**: Instantiate `MLAnomalyDefence`, call `observe(action)` on a
known-attack action, verify `DetectionResult.anomaly_score` is in [0,1] and `alerted`
reflects the threshold comparison. No Docker lab required.

**Acceptance Scenarios**:

1. **Given** a freshly instantiated `MLAnomalyDefence`, **When** `observe(action)` is
   called with a scan-category action, **Then** the result has `anomaly_score` in [0,1]
   and `coverage == "covered"`.
2. **Given** a trained detector, **When** an action with high-intensity parameters (wide
   port range, many attempts) is observed, **Then** `anomaly_score` is measurably higher
   than for a single-port, single-attempt benign action.
3. **Given** `MLAnomalyDefence(threshold=0.6)`, **When** `anomaly_score >= 0.6`,
   **Then** `alerted == True`; **When** `anomaly_score < 0.6`, **Then** `alerted == False`.

---

### User Story 2 — Pluggable Swap: ML Replaces Rule-Based Detector Without Loop Changes (Priority: P2)

A researcher wants to swap the rule-based detector for `MLAnomalyDefence` in an
experiment run and have every downstream metric (Detection Rate, Robustness Score,
report) continue working unchanged, proving the pluggable design is real.

**Why this priority**: Validates the core architectural claim. Without a genuine drop-in
swap, the pluggable interface is theoretical. Comes second because US1 must exist first.

**Independent Test**: Pass `MLAnomalyDefence` as the `defence` argument to
`run_episode()`. Confirm a valid `EpisodeRecord` is produced. No changes to
`episode.py` or `metrics.py`.

**Acceptance Scenarios**:

1. **Given** `run_episode(state, selector, exec_fn, MLAnomalyDefence())`, **When** the
   episode completes, **Then** `EpisodeRecord.steps` has at least one `StepRecord` with
   `detected` correctly reflecting the ML defence result.
2. **Given** the same episode logs, **When** `detection_rate(records)` is computed,
   **Then** the value reflects the ML detector's alerts without any code changes to the
   metrics module.

---

### User Story 3 — Scientific Validation: Discrimination Better Than Chance (Priority: P3)

A researcher needs to verify the anomaly detector meaningfully separates normal from
attack traffic, demonstrating scientific validity before claiming it as a result.

**Why this priority**: Required for scientific credibility. Without a validated
discrimination score, E8 cannot be published as a working ML defence.

**Independent Test**: Evaluate the trained model on held-out normal and attack feature
sets. Assert the discrimination score exceeds the random-chance baseline.

**Acceptance Scenarios**:

1. **Given** a trained detector and held-out normal and attack feature matrices, **When**
   `evaluate_roc_auc` is called, **Then** the returned value is in [0,1] and > 0.5.
2. **Given** two evaluation runs with `seed=42`, **When** `evaluate_roc_auc` is computed
   both times, **Then** the returned value is identical (deterministic).

---

### Edge Cases

- What if `observe()` is called before the model is fitted? → Must raise a clear error,
  not silently return 0.0.
- What if an action has missing or zero-valued parameters? → Encoder must zero-pad
  gracefully, returning a valid fixed-length vector without raising.
- What if `anomaly_score` lands exactly on the threshold? → `alerted = True` (≥ rule).
- What if `n_samples=0` is passed to `collect_normal_baseline`? → Must raise
  `ValueError` with a descriptive message.
- What if the same action is observed twice in a row? → Must return the same score
  (stateless encoding + deterministic model).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an encoder that converts any action from the
  action library into a fixed-length numeric vector deterministically, with no external
  I/O and no dependency on live traffic.
- **FR-002**: The system MUST provide a baseline generator that returns a reproducible
  matrix of benign-traffic feature vectors; two calls with the same seed and sample
  count must produce identical output across machines.
- **FR-003**: The system MUST provide an anomaly detector that can be trained on a
  normal-traffic matrix and score any new feature vector in [0,1], where higher values
  indicate greater deviation from the baseline.
- **FR-004**: The system MUST provide an anomaly-based defence component that implements
  the existing pluggable defence interface with no interface changes; every existing
  metric, report, and loop module MUST work unchanged when this component is substituted.
- **FR-005**: The system MUST provide a discrimination evaluator that computes a
  score comparing normal and attack feature distributions; the score MUST exceed 0.5
  (better than random) for the default configuration and seed.
- **FR-006**: All random operations MUST be controlled by an explicit seed parameter;
  two runs with the same seed MUST produce identical feature matrices, model parameters,
  and anomaly scores.
- **FR-007**: The new dependency MUST be declared with a minimum version in the
  dependency manifest to ensure reproducibility.
- **FR-008**: The anomaly defence component MUST set coverage to "covered" for every
  action (unlike rule-based detection, the learned model covers all traffic by design).

### Key Entities

- **ActionFeatureEncoder**: Stateless converter. Input: an `Action`. Output: a
  fixed-length numeric vector. No state, no I/O.
- **NormalBaseline**: Matrix of feature vectors representing benign low-intensity
  traffic (single-port connections, 1-attempt auth). Used as training data.
- **AnomalyDetector**: Trained statistical model. State: fitted / unfitted. Accepts a
  feature vector and returns an anomaly score in [0,1].
- **MLAnomalyDefence**: Stateful defence component. Trained at construction. Holds a
  fitted `AnomalyDetector` and a configurable alert threshold. Implements the pluggable
  defence interface.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Observing an attack action via `MLAnomalyDefence` returns a result within
  50 ms with no external calls (pure in-memory inference).
- **SC-002**: The discrimination score evaluated on a 500-sample normal baseline vs 15
  distinct attack action vectors exceeds 0.5 under `seed=42`.
- **SC-003**: Two experiment runs with `seed=42` using `MLAnomalyDefence` produce
  identical episode records (reproducibility criterion).
- **SC-004**: Zero lines of code are changed in `episode.py`, `action_executor.py`,
  `run_experiment.py`, `metrics.py`, or `report.py` to support the ML defence.
- **SC-005**: The existing test suite of 325 tests continues to pass after this feature
  is merged.

## Assumptions

- "Normal traffic" is approximated by synthetic benign feature vectors generated from a
  seeded RNG using benign parameter distributions (low port counts, single attempts).
  Real captured benign traffic is not required for Phase 2.
- The `DetectionResult.anomaly_score` field already exists in the data contract
  (confirmed from F03 implementation).
- The pluggable `Defence` abstract base class already defines the `observe` method
  signature (confirmed from F10 implementation).
- A statistical isolation-based method produces ROC-AUC > 0.5 given sufficiently
  separated benign vs attack parameter distributions.
- `scikit-learn>=1.4` is compatible with the existing Python 3.12 environment.
