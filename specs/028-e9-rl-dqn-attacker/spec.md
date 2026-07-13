# Feature Specification: RL/DQN Attacker

**Feature Branch**: `028-e9-rl-dqn-attacker`
**Created**: 2026-07-13
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Adaptive Action Selection Through Experience (Priority: P1)

A security researcher wants an attacker that gets smarter over time. Rather than picking
actions randomly or following a fixed script, the attacker should learn from each step
which actions achieve objectives while drawing the least attention from the ML anomaly
detector. It improves purely through experience — no manual tuning of action preferences.

**Why this priority**: This is the core E9 deliverable. Without a self-improving attacker,
the adaptive adversarial loop cannot close. Every other story depends on this working.

**Independent Test**: Instantiate the learned attacker, run it through a sequence of steps
with a mock defence returning anomaly scores, confirm it selects actions and updates its
internal state without errors. No Docker lab required.

**Acceptance Scenarios**:

1. **Given** a freshly created learned attacker, **When** `choose_action` is called with a
   list of available actions and the current episode state, **Then** a valid action from the
   available list is returned every time.
2. **Given** a learned attacker that has taken several steps, **When** `observe` is called
   with the action taken, the resulting reward, and the updated state, **Then** the attacker
   updates its internal knowledge without raising any errors.
3. **Given** a learned attacker after many steps with consistent reward signals, **When**
   compared to its early-episode behaviour, **Then** its action selection shifts toward
   lower-anomaly actions (it learns to be stealthier over time).
4. **Given** two runs with the same seed, **When** the attacker is stepped through identical
   episode sequences, **Then** identical actions are chosen at every step.

---

### User Story 2 — Stealth Measurement: Cumulative Anomaly Exposure (Priority: P2)

A security researcher needs to quantify how stealthy the learned attacker is across
episodes. The existing metrics (Detection Rate, Robustness Score) only capture whether
the attacker was detected, not how much anomaly signal it generated. A new metric is
needed: lower score means the attacker stayed under the radar more successfully.

**Why this priority**: Scientific validity requires a measurable outcome. Without CAE,
there is no way to claim the learned attacker is stealthier than the baselines. Comes
after US1 because it requires episode records to compute.

**Independent Test**: Compute the new metric on a list of synthetic episode records with
known anomaly scores. Verify the value matches the expected mean-of-sums formula.

**Acceptance Scenarios**:

1. **Given** a list of completed episode records each containing per-step anomaly scores,
   **When** `cumulative_anomaly_exposure` is called, **Then** it returns the mean total
   anomaly exposure per episode as a non-negative float.
2. **Given** episode records where every step has anomaly_score = 0.0, **When** the metric
   is computed, **Then** the result is exactly 0.0.
3. **Given** two attacker strategies run for the same number of episodes, **When** CAE is
   computed for both, **Then** the attacker that chose less anomalous actions produces a
   strictly lower CAE value.

---

### User Story 3 — Drop-In Replacement in Experiment Loop (Priority: P3)

A security researcher wants to swap the learned attacker into the existing experiment loop
in place of RandomAttacker or LinUCBAttacker with a single config change, and have all
downstream metrics, reports, and manifests continue working unchanged.

**Why this priority**: Validates the pluggable-attacker architecture claim. Without this,
the experiment pipeline cannot run E9 end-to-end. Comes last because it requires US1
(working attacker) and US2 (new metric) to already exist.

**Independent Test**: Pass the learned attacker to the experiment runner via the dedicated
DQN config. Confirm valid episode records are produced with no changes to the episode or
metrics modules.

**Acceptance Scenarios**:

1. **Given** `config_dqn.yaml` specifying the learned attacker class with 200 episodes,
   **When** the experiment runner is executed, **Then** it completes successfully and produces
   episode records and a run manifest with no code changes to the episode or metrics modules.
2. **Given** a completed experiment run with the learned attacker, **When** CAE is computed
   on the produced records, **Then** the value is reported in the experiment summary
   alongside Detection Rate and Robustness Score.
3. **Given** the same seed used twice with the learned attacker, **When** both run summaries
   are compared, **Then** the CAE values are identical.

---

### Edge Cases

- What if `choose_action` is called with only one available action? → Must return that
  action immediately without error.
- What if `observe` is called before any `choose_action`? → Must raise a clear error
  describing the invalid call order.
- What if the anomaly score is exactly 0.0 on every step? → Reward shaping must still
  function correctly with no NaN or division errors in internal state.
- What if the reward signal is negative on every step? → Internal learning must continue
  without divergence or silent failure.
- What if `cumulative_anomaly_exposure` receives an empty list? → Must return 0.0.
- What if a step record has no anomaly score (rule-based defence used instead of ML)?
  → Must treat missing scores as 0.0 and compute gracefully.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a learned attacker component that selects actions
  from the available action set and improves its selection strategy through trial-and-error
  experience across episode steps.
- **FR-002**: The learned attacker MUST implement the existing pluggable attacker interface
  with no changes to that interface or to any existing attacker, episode, or metrics module.
- **FR-003**: The learned attacker MUST balance exploration (trying new actions) with
  exploitation (repeating high-reward actions), with exploration decreasing automatically
  as experience accumulates.
- **FR-004**: The attacker MUST penalise steps that trigger high anomaly scores by
  incorporating the anomaly signal into its reward, so it learns to prefer stealthier actions.
- **FR-005**: The system MUST provide a `cumulative_anomaly_exposure` metric that summarises
  the mean total anomaly signal generated per episode across a set of episode records.
- **FR-006**: All random operations MUST be controlled by an explicit seed so that two runs
  with the same seed produce identical action sequences and metrics.
- **FR-007**: A dedicated experiment configuration MUST be provided that runs enough episodes
  for the learned attacker to demonstrate improvement in stealth over random selection.
- **FR-008**: The new dependency MUST be declared with a minimum version constraint in the
  dependency manifest to ensure reproducibility across machines.

### Key Entities

- **LearnedAttacker**: Stateful attacker component. Selects actions based on accumulated
  experience. Improves stealth over time through reward feedback. Holds internal value
  estimates and an exploration policy.
- **ExperienceStore**: Bounded memory of past transitions (state, action, reward,
  next-state). Enables learning from randomised past experience rather than only the most
  recent step.
- **ActionValueEstimator**: Approximates the expected future reward for each action given
  the current state. Updated incrementally as experience accumulates.
- **CumulativeAnomalyExposure**: Per-episode sum of anomaly scores across all steps,
  averaged over episodes. Lower = stealthier attacker.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After 200 training episodes, the learned attacker's mean CAE is lower than
  that of a random attacker run for the same 200 episodes — demonstrating learned stealth.
- **SC-002**: Action selection completes in under 10 ms per call (pure in-memory, no I/O).
- **SC-003**: Two experiment runs with `seed=42` produce identical CAE values and identical
  episode records.
- **SC-004**: Zero lines of code are changed in `episode.py`, `action_executor.py`,
  `report.py`, or `ground_truth.py` to support the learned attacker.
- **SC-005**: The existing 335 tests continue to pass after this feature is merged.

## Assumptions

- The ML anomaly detector (F27) is already fitted and available to provide continuous
  anomaly scores in [0, 1] per action observed.
- The reward signal per step comes from the existing reward function (F14). The anomaly
  penalty is applied before passing the combined reward to the attacker's `observe()`.
- 200 episodes of 10 steps each is sufficient to demonstrate measurable stealth improvement
  over random action selection under the synthetic baseline.
- The pluggable attacker interface (`choose_action` + `observe`) is unchanged from F17.
- CPU-only computation is sufficient; GPU acceleration is not required.
- `anomaly_score` is already stored per step in each episode record via the existing loop.
