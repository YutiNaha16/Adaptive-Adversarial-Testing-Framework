# Adaptive Adversarial Testing Framework — Technical Internals

> How it actually works under the hood: tech stack, data flow, hyperparameters, and every internal detail.
> Companion to PROJECT_SUMMARY.md.

---

## 1. Tech Stack — Every Library and Why It's There

| Library | Version | Role |
|---|---|---|
| **Python** | 3.12 | Runtime. Pinned hard — no 3.11 or 3.13. |
| **PyTorch** | ≥2.2 (CPU-only) | Neural network for DQN/ParameterizedDQN. `torch.nn`, `torch.optim.Adam`, `torch.no_grad`. |
| **scikit-learn** | ≥1.4 | `IsolationForest` for the ML anomaly detector. Also `roc_auc_score` for evaluation. |
| **NumPy** | existing | Context vector construction, feature encoding, evasive cache storage (`.npy` files), baseline generation. |
| **Pydantic V2** | existing | `ExperimentConfig` — validates every config field with type checking and range constraints. `Action` and `DetectionResult` data contracts. |
| **PyYAML** | existing | Parses `config.yaml` into a Python dict that Pydantic then validates. |
| **Flask** | existing | Dashboard web server at port 5050. Reads output dirs, renders `dashboard.html` with live data. |
| **Jinja2** | ≥3.1 | Two templates: `report.md.j2` (experiment report), `dashboard.html` (web UI). |
| **scipy** | ≥1.12 | `scipy.stats.bootstrap` for 95% confidence intervals in `run_multiseed.py`. |
| **pytest** | existing | 383 tests across 20+ test files. Run with `cd src && pytest`. |
| **ruff** | existing | Linting (`ruff check .`) + formatting (`ruff format`). Replaces flake8 + black. |
| **pip-tools** | existing | Pins exact dependency versions via `requirements.in` → `requirements.txt`. |
| **Docker Engine** | ≥20 | Lab mode only. Runs Suricata + nginx + SSH containers in an isolated network. |
| **Docker Compose V2** | plugin | Orchestrates the lab containers via `lab/docker-compose.yml`. |
| **Suricata** | 7.0.5 | Real IDS. Reads live traffic in lab mode, writes alerts to `eve.json`. |

---

## 2. How to Run It — Every Command

### Setup (first time)
```bash
# Create virtualenv and install dependencies
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Simulation runs (no Docker needed)
```bash
# Basic run using config.yaml
cd src
python run_experiment.py

# Specify a different config
python run_experiment.py --config ../config_round3_ml.yaml

# With evasive cache (N2 active)
python run_experiment.py --config ../config_round3_ml.yaml \
    --evasive-cache ../outputs/run_003_ml/evasive_cache.npy

# Via Makefile
make round3-ml                    # config_round3_ml.yaml
make round4                       # config_round4.yaml + evasive cache
make multiseed SEEDS=0,1,2,3,4   # 5-seed statistical run
make sweep                        # 5×5 hyperparameter grid
make arms-race ROUNDS=4           # 4-round arms race loop
make transfer-sim                 # seed=99 transfer test
```

### Lab mode (Docker required)
```bash
# Start lab containers
make lab-up

# Verify isolation (outbound traffic blocked)
make lab-check

# Run 50-episode lab experiment
cd src
python run_experiment.py --config ../config_lab_run.yaml --lab

# Start dashboard
make dashboard   # → http://localhost:5050

# Tear down lab
make lab-down
```

### Tests and linting
```bash
cd src
pytest              # Run all 383 tests
pytest -x           # Stop on first failure
ruff check .        # Lint
ruff format .       # Format
```

---

## 3. Config Fields — Every Field Explained

Config is a YAML file loaded into `ExperimentConfig` (Pydantic model). Example:

```yaml
episodes: 200
seed: 42
output_dir: outputs/run_004
ruleset_path: /etc/suricata/rules
detection_threshold: 0.63
attacker_class: ParameterizedDQNAttacker
anomaly_lambda: 0.5
lab_target_ip: 172.28.0.2
```

| Field | Type | Constraints | What It Does |
|---|---|---|---|
| `episodes` | int | > 0 | How many full attack episodes to run. Each episode = fresh `EpisodeState`, attacker resets to step 0. DQN keeps learning across episodes (replay buffer persists). |
| `seed` | int | ≥ 0 | Random seed passed to `seed_everything()` — sets `random.seed()`, `np.random.seed()`, `torch.manual_seed()`. Ensures reproducibility. |
| `output_dir` | Path | must be writable | Where reports, manifests, policy snapshots, and learning curves are saved. Created automatically. |
| `ruleset_path` | Path | any | Path to Suricata rules directory. Used in lab mode to load `disabled.conf`. In sim mode, ignored. |
| `detection_threshold` | float | [0.0, 1.0] | The anomaly score threshold for `MLAnomalyDefence.observe()`. Score ≥ threshold → `alerted=True`. At 0.63, the IsolationForest sits just below the evasion boundary (phase transition at ~0.62). |
| `attacker_class` | str | one of 5 | Which attacker to instantiate: `RandomAttacker`, `FixedScriptAttacker`, `LinUCBAttacker`, `DQNAttacker`, `ParameterizedDQNAttacker`. |
| `anomaly_lambda` | float | ≥ 0.0 | Weight for ML penalty in shaped reward: `shaped = reward − λ × anomaly_score`. 0.0 = no ML. 0.5 = balanced. Controls whether N3 (dual-paradigm shaping) is active. Also controls which defence is instantiated: >0 → `MLAnomalyDefence`, =0 → `NullDefence`. |
| `lab_target_ip` | str | IP address | IP of the nginx/SSH Docker container to attack in lab mode. Default 172.28.0.2. Passed to `ActionExecutor` and `get_params_for_intensity()`. |

---

## 4. The 50-Dimensional Context Vector

Every time the attacker is asked to choose an action, a 50-dimensional float32 vector is built from the current episode state and passed as input to the neural network. This is the DQN's entire "view" of the world.

**Source:** `src/aatf/context_vector.py`, `CONTEXT_DIM = 50`

The vector is a concatenation of 5 sub-arrays:

```
context = [alert (10)] + [progress (15)] + [technique (15)] + [timing (2)] + [cats (8)]
         = 50 total
```

### Sub-array 1: Alert History (10 dims)

Binary encoding of the last 10 steps — did an alert fire?

```python
ALERT_WINDOW = 10
window = alert_history[-10:]   # last 10 booleans
padded = [0.0, 0.0, ..., 1.0, 0.0]   # zero-padded at left if fewer than 10 steps
```

- `1.0` = alert fired at that step
- `0.0` = no alert
- Zero-padded at the start of the episode

**Why:** Lets the DQN see the recent detection pattern — e.g. "I got caught 3 times in the last 5 steps".

---

### Sub-array 2: Attack Progress (15 dims)

One bit per action (sorted alphabetically) — did the attacker already execute this action?

```python
_SORTED_ACTION_IDS = sorted([...15 action ids...])
progress[i] = 1.0 if action_ids[i] in completed_actions else 0.0
```

- Once an action is executed it stays 1.0 for the rest of the episode
- The attack graph prevents repeated actions

**Why:** The DQN can see what it's already done and what remains.

---

### Sub-array 3: Technique History (15 dims)

Per-action detection rate across the entire episode history (not just current episode):

```python
for aid in _SORTED_ACTION_IDS:
    execs = history.get(aid, [])        # list of detected booleans
    rate = sum(execs) / max(len(execs), 1)   # fraction detected
```

- 0.0 = this action was never detected
- 1.0 = this action always triggers an alert

**Why:** The DQN learns which specific actions are risky across previous episodes, not just the current one. This is cross-episode memory for the attacker.

---

### Sub-array 4: Timing (2 dims)

Progress through the episode, normalised:

```python
step_norm    = min(step / MAX_STEPS, 1.0)          # MAX_STEPS = 100
elapsed_norm = min(elapsed_seconds / 3600.0, 1.0)  # clipped to 1 hour
```

**Why:** Tells the DQN how far through the episode it is. In lab mode, timing is real wall-clock; in sim mode, it's nearly 0 because execution is instant.

---

### Sub-array 5: Rule Categories (8 dims)

One bit per Suricata ET category that has fired during the episode:

```python
ET_CATEGORIES = [
    "ET SCAN", "ET EXPLOIT", "ET BRUTE_FORCE", "ET WEB_SPECIFIC_APPS",
    "ET DNS", "ET POLICY", "ET TROJAN", "ET INFO"
]
cats[i] = 1.0 if ET_CATEGORIES[i] in fired_categories else 0.0
```

**Why:** Tells the DQN which Suricata rule categories have been triggered so far — useful for inferring "SCAN alerts are up, maybe switch to WEB actions".

---

## 5. The 7-Dimensional ML Feature Vector

When `MLAnomalyDefence.observe()` is called, the `Action` is encoded into a 7-dimensional vector and fed to the `IsolationForest`. This is a completely different representation from the 50-dim context vector — it describes the *action's network characteristics*, not the episode state.

**Source:** `src/aatf/ml_defence.py`, `FEATURE_DIM = 7`

```python
feat[0] = CATEGORY_MAP[action.category] / 5.0       # scan=0, brute=1, ssh=2, web=3, dns=4, exfil=5
feat[1] = md5(action_id) % 1000 / 1000.0            # stable hash → unique float per action
feat[2] = port_range_start / 65535                  # normalised port number (start)
feat[3] = port_range_end / 65535                    # normalised port number (end)
feat[4] = min(attempts / 100, 1.0)                  # number of login/request attempts
feat[5] = min(timing_ms / 10000, 1.0)               # delay between attempts in ms
feat[6] = min(wordlist_size / 100, 1.0)             # number of words/paths in scan wordlist
```

**Why intensity matters here:** At low intensity, `attempts=2` → feat[4] = 0.02. At high intensity, `attempts=100` → feat[4] = 1.0. The IsolationForest was trained on normal traffic where attempts ≤ 2, timing_ms ≥ 500ms, wordlist_size ≈ 0. Low-intensity attacks look like normal traffic; high-intensity attacks look like attacks.

**Baseline training data:** 500 samples of synthetic "normal" traffic generated at startup:
- feat[4] (attempts): uniform in [0, 0.02] (≤ 2 attempts)
- feat[5] (timing_ms): uniform in [0, 0.01] (slow, human-paced)
- feat[6] (wordlist_size): uniform in [0, 0.01] (no scanning)

---

## 6. IsolationForest — How It Scores

**Fitting (happens once at startup):**
```python
IsolationForest(contamination=0.1, random_state=seed).fit(X_normal)
# X_normal = 500 × 7 matrix of normal-traffic feature vectors
```

`contamination=0.1` tells the forest: "expect 10% of training data to be anomalous" — this sets the decision boundary.

**Scoring (happens every step):**
```python
raw = clf.score_samples(x)    # sklearn raw score: more negative = more anomalous
z = -raw                      # flip sign: anomalous → larger z
score = 1 / (1 + exp(-z))    # sigmoid: maps to (0, 1), larger = more anomalous
```

The sigmoid converts the raw score into a probability-like value in (0, 1). Score > 0.63 → detected.

---

## 7. Cosine-Similarity Boosting (N2 Internals)

When the evasive cache has vectors in it, every call to `observe()` computes a boost:

```python
def _similarity_boost(feat):
    # For each vector in evasive_cache:
    max_sim = max(cosine_similarity(feat, ev) for ev in evasive_cache)
    # cosine similarity ∈ [-1, 1]
    # Only boost if very close match (cosine > 0.9)
    boost = max(0.0, (max_sim - 0.9) * 5.0) * (1 - detector.score(feat))
    return boost

final_score = min(1.0, base_score + boost)
```

**Logic:** If the incoming action's feature vector is within cosine distance 0.1 of a known-evasive vector, and the base detector score is still low (detector is still fooled), apply a boost proportional to similarity. Maximum boost = `(1.0 - 0.9) * 5.0 * (1 - base_score)`. If base_score is already 0.2, max boost ≈ 0.4, pushing total to 0.6 (near detection threshold). This is why 15/15 blind spots get closed — every action has a unique feature vector that's a perfect match to its cached evasive vector.

---

## 8. DQN Training — Every Hyperparameter

### Architecture: QNetwork

```python
QNetwork(state_dim=50, n_actions=15 or 45):
    Linear(50, 64)
    ReLU
    Linear(64, 64)
    ReLU
    Linear(64, 15)   # or 45 for ParameterizedDQN
```

Two hidden layers of 64 units each. Simple and fast to train on CPU.

### DQNModel Hyperparameters

| Parameter | Value | Meaning |
|---|---|---|
| `lr` | 1e-3 | Adam learning rate |
| `gamma` | 0.95 | Discount factor. Future rewards worth 95% of immediate. |
| `epsilon_start` | 1.0 | Start fully random (100% exploration) |
| `epsilon_end` | 0.1 | Settle at 10% random (90% greedy) |
| `epsilon_decay_steps` | 500 (DQN), 1000 (Param-DQN) | Steps to decay from 1.0 to 0.1 linearly |
| `buffer_capacity` | 2000 (DQN), 4000 (Param-DQN) | Max transitions in replay buffer (circular) |
| `batch_size` | 32 | Random sample from buffer per gradient step |
| `target_update_freq` | 10 | Copy online weights to target every 10 gradient steps |

**Why two networks (online + target)?** The online network is what gets updated every step. The target network is a frozen copy used to compute stable Q-value targets during training. Without it, the target keeps moving and training diverges. Every 10 gradient steps, target is updated to match online.

### Training Step (called after every action)

```python
# 1. Push transition to replay buffer
buffer.push(state, action_idx, reward, next_state)

# 2. If buffer has enough samples:
batch = buffer.sample(32)

# 3. Compute target Q-values (Bellman equation)
target_q = reward + 0.95 * target_net(next_state).max()
#           ^^^^^    ^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^
#           immediate reward + discounted future value

# 4. Compute current Q-values
current_q = online_net(state)[action_idx]

# 5. MSE loss and backprop
loss = MSE(current_q, target_q)
optimizer.zero_grad()
loss.backward()
optimizer.step()
```

### ParameterizedDQNModel Differences

The only differences from plain DQN:
- Output is 45-dimensional (15 actions × 3 intensities)
- `_combined_idx(action_idx, intensity) = action_idx * 3 + intensity`
- Action masking: only indices for available actions × all intensities are unmasked
- Epsilon decay is slower (1000 steps vs 500) because the action space is 3× larger

### Epsilon-Greedy Exploration

```python
epsilon = max(epsilon_end, epsilon - (epsilon_start - epsilon_end) / decay_steps)
if random.random() < epsilon:
    return random.choice(available_actions)   # explore
else:
    return argmax(Q[available_actions])       # exploit
```

At step 0: ε=1.0 → always random. After 500 steps: ε=0.1 → 10% random. The decay is linear, one decrement per call to `select_action`.

---

## 9. The Reward Function

**Source:** `src/aatf/reward.py`

```python
REWARD_DETECTED  = -1.0   # Suricata fired → punishment
REWARD_PROGRESS  = +1.0   # action completed and advanced the attack graph → reward
REWARD_STALL     = -0.1   # action completed but didn't advance the graph → small penalty
```

**Shaped reward (N3, applied in run_experiment.py):**
```python
shaped = step.reward - config.anomaly_lambda * step.anomaly_score
```

So with `anomaly_lambda=0.5` and a step where the attacker wasn't detected by Suricata (reward=+1.0 or -0.1) but got anomaly_score=0.7:
```
shaped = 1.0 - 0.5 × 0.7 = 1.0 - 0.35 = 0.65
```

Vs a step where anomaly_score=0.2 (stealthy):
```
shaped = 1.0 - 0.5 × 0.2 = 1.0 - 0.10 = 0.90
```

The DQN learns to prefer actions that both advance the attack AND produce low anomaly scores — exactly the behaviour needed to evade the ML detector.

---

## 10. The Attack Graph — Action Unlock Tree

Actions are not all available from the start. The attack graph models realistic recon-then-exploit sequencing:

**Entry points** (always available at episode start):
- `tcp_port_scan`
- `udp_sweep`
- `icmp_ping_sweep`
- `dns_subdomain_enum`

**Unlock chains:**
```
tcp_port_scan        → ssh_brute_force, ftp_brute_force, http_dir_scan, ssh_user_enum
udp_sweep            → dns_zone_transfer
icmp_ping_sweep      → ssh_version_probe
dns_subdomain_enum   → dns_zone_transfer
ssh_brute_force      → ssh_version_probe
http_dir_scan        → http_sqli_probe, http_xss_probe, http_basic_brute
http_sqli_probe      → http_exfil
dns_zone_transfer    → dns_exfil
```

**`available_actions(completed)` logic:**
```python
reachable = set(entry_points)
for action_id in completed:
    reachable |= edges.get(action_id, frozenset())
return sorted(reachable - completed)   # don't repeat actions
```

**Why this matters for DQN:** The DQN can't pick actions that aren't unlocked yet. So in early episodes it has only 4 choices; after doing `tcp_port_scan` it gains 4 more; etc. The attack graph forces a realistic "recon first" ordering.

---

## 11. Episode Loop — Step by Step

**Source:** `src/aatf/episode.py`, `run_episode()`

For each step within an episode:

```
1. attack_graph.available_actions(completed)  → list of reachable unfinished actions
2. if none available → episode completed (True)
3. if step >= max_steps (100) → episode timed out (False)
4. attacker.choose_action(available, context)  → action_id
   └─ DQN: builds context vector, runs QNetwork, epsilon-greedy, returns action_id
          (also records last_state, last_action_id, last_intensity for step 8)
5. execute_fn(action_id)
   └─ Lab mode: ActionExecutor sends real packets to 172.28.0.2; sleep 1.5s
   └─ Sim mode: lambda _: None  (no-op)
6. parameterize_fn(action_id) → intensity-adjusted parameters dict
   └─ ParameterizedDQN: calls get_params_for_intensity(action_id, last_intensity, ...)
   └─ Others: action_def.default_parameters
7. defence.observe(Action(action_id, params, ...)) → DetectionResult
   └─ Lab (CompositeDefence):
       ├─ SuricataDefence reads eve.json for new alerts → alerted: bool, rule_ids: list
       └─ MLAnomalyDefence encodes action → IsolationForest.score + cosine_boost → anomaly_score
   └─ Sim (MLAnomalyDefence): same but no Suricata; alerted = (anomaly_score >= threshold)
   └─ NullDefence (λ=0): always alerted=False, anomaly_score=0.0
8. collect_feedback(episode_state, action_id, alert_fired)
   └─ detected = alert_fired
   └─ stage_progress = action unlocked new actions in the attack graph?
   └─ updates episode_state: completed_actions, detection_history, alert_history, fired_categories
9. compute_reward(detected, stage_progress)  → +1.0 / -1.0 / -0.1
10. append StepRecord(action_id, detected, stage_progress, reward, anomaly_score)
11. total_reward += reward
```

**After all steps (in run_experiment.py, not in episode.py):**
```
12. for each step: shaped = reward − λ × anomaly_score
13. attacker.observe(action_id, context, shaped)
    └─ DQN: buffer.push(last_state, last_action_idx, shaped, current_state)
            if buffer >= 32: sample batch, compute target_q, backprop
14. EpisodeRecord(steps, total_reward, completed, episode_index) → records list
```

---

## 12. Lab Mode vs Sim Mode — What's Different

| Aspect | Sim Mode (λ=0) | Sim Mode (λ>0) | Lab Mode |
|---|---|---|---|
| `execute_fn` | no-op | no-op | `ActionExecutor.execute()` → real socket calls |
| Defence | `NullDefence` | `MLAnomalyDefence` | `CompositeDefence(SuricataDefence, MLAnomalyDefence)` |
| Suricata alerts | never | never | real — reads `eve.json` from Docker container |
| Anomaly score | always 0.0 | IsolationForest score | IsolationForest score |
| Detection = | never | anomaly_score ≥ threshold | Suricata alert OR anomaly_score ≥ threshold |
| Between-step delay | none | none | `time.sleep(1.5)` to let Suricata process packets |
| BSP calculation | skipped | skipped | computed (disabled SIDs vs reported blind spots) |
| Episode length | fast (<1s) | fast (<1s) | ~30s per episode (15 steps × 1.5s sleep) |
| IsolationForest | n/a | fresh at startup | fresh at startup |

---

## 13. Intensity Override Table — Exact Numbers

For the 6 actions that have intensity overrides (others use `default_parameters` for all intensities):

### `ssh_brute_force`
| Intensity | attempts | interval_ms |
|---|---|---|
| low (0) | **2** | 2000 |
| medium (1) | 10 | 500 |
| high (2) | 100 | 100 |

*Suricata threshold: 3+ attempts = alert. Low intensity (2 attempts) stays below.*

### `ftp_brute_force`
| Intensity | attempts | interval_ms |
|---|---|---|
| low (0) | **2** | 2000 |
| medium (1) | 8 | 600 |
| high (2) | 50 | 100 |

### `http_basic_brute`
| Intensity | attempts | interval_ms |
|---|---|---|
| low (0) | **2** | 2000 |
| medium (1) | 12 | 300 |
| high (2) | 50 | 100 |

### `http_dir_scan`
| Intensity | wordlist_size | rate_rps |
|---|---|---|
| low (0) | **3** | 1 |
| medium (1) | 50 | 5 |
| high (2) | 100 | 10 |

### `dns_subdomain_enum`
| Intensity | wordlist_size | rate_rps |
|---|---|---|
| low (0) | **3** | 1 |
| medium (1) | 20 | 3 |
| high (2) | 100 | 10 |

### `tcp_port_scan`
| Intensity | port_range | rate_pps | timing_ms |
|---|---|---|---|
| low (0) | **1-100** | **2** | 100 |
| medium (1) | 1-1024 | 10 | 100 |
| high (2) | 1-1024 | 100 | 10 |

**The 9 remaining actions** (`udp_sweep`, `icmp_ping_sweep`, `ssh_user_enum`, `ssh_version_probe`, `http_sqli_probe`, `http_xss_probe`, `http_exfil`, `dns_exfil`, `dns_zone_transfer`) use `default_parameters` regardless of intensity — they have no meaningful knobs for stealth.

---

## 14. The Auto-Remediation Algorithm (N2) — Step by Step

**Called after a run completes in `run_experiment.py`:**

```python
auto_remediate(ml_defence, records, evasion_threshold=0.3)
```

**Steps:**
```
1. Scan all EpisodeRecord.steps where:
   - step.detected == False   (evaded Suricata)
   - step.anomaly_score < 0.3 (evaded ML detector — score well below threshold)
   These are "double blind spots"

2. Deduplicate by action_id (keep one representative per action)

3. For each unique evaded action:
   - Re-encode it with ActionFeatureEncoder (same 7-dim vector)
   - Record original score (avg before)

4. Shallow-copy the MLAnomalyDefence
   new_defence._evasive_cache = old_cache + new evasive vectors

5. Re-score the same actions with the patched defence:
   new_score = new_defence.observe(action)
   Count how many now score ≥ detection_threshold → gaps_closed

6. Save evasive cache to .npy:
   np.save(path, np.vstack(evasive_cache))

7. Return (new_defence, RemediationReport)
   - total_evaded, gaps_closed, avg_score_before, avg_score_after, remediated_action_ids
```

**Why the evasion threshold is 0.3 (not 0.63):** The ML detector threshold is 0.63, but we use 0.3 for identifying "truly invisible" actions — those scoring well below detection. Actions scoring 0.5–0.62 are near the boundary and might get boosted above threshold with a small perturbation, so we don't need to cache them.

---

## 15. File Structure — What Lives Where

```
src/
├── aatf/
│   ├── action_executor.py      # Sends real network packets (lab mode only)
│   ├── action_intensity.py     # Intensity override table (6 actions, 3 levels each)
│   ├── action_library.py       # REGISTRY: 15 ActionDefinition objects
│   ├── attack_graph.py         # ATTACK_GRAPH: which actions unlock which
│   ├── attacker.py             # RandomAttacker, FixedScriptAttacker, LinUCBAttacker
│   ├── config.py               # ExperimentConfig Pydantic model + load_config()
│   ├── context_vector.py       # build_context() → 50-dim float32 array
│   ├── contracts.py            # Action, DetectionResult dataclasses
│   ├── defence.py              # Defence ABC, NullDefence, CompositeDefence
│   ├── dqn_attacker.py         # QNetwork, DQNModel, DQNAttacker, ParameterizedDQN*
│   ├── episode.py              # run_episode(), StepRecord, EpisodeResult
│   ├── explainability.py       # explain_evasions() → ActionExplanation list
│   ├── feedback.py             # collect_feedback() → updates EpisodeState
│   ├── gate.py                 # phase1_gate() → GateResult with pass/fail
│   ├── ground_truth.py         # validate_blind_spots() → BSP calculation
│   ├── linucb.py               # LinUCBModel for contextual bandit attacker
│   ├── manifest.py             # write_manifest() → run_manifest_*.json
│   ├── metrics.py              # detection_rate(), robustness_score(), CAE, EpisodeRecord
│   ├── ml_defence.py           # IsolationForest, MLAnomalyDefence, auto_remediate()
│   ├── report.py               # generate_report() → Jinja2 → .md file
│   ├── reward.py               # compute_reward() → +1.0 / -1.0 / -0.1
│   ├── seeding.py              # seed_everything(seed)
│   ├── statistics.py           # summarise_metric() → bootstrap CI
│   ├── suricata_defence.py     # SuricataDefence: reads eve.json in lab mode
│   └── templates/
│       └── report.md.j2        # Jinja2 report template
├── dashboard/
│   ├── app.py                  # Flask routes: /, /report/<run_dir>
│   └── templates/
│       └── dashboard.html      # Full dashboard UI with Chart.js
├── run_experiment.py           # Main entrypoint: loads config, runs episodes, saves output
├── run_multiseed.py            # Multi-seed aggregation with bootstrap CI
├── run_sweep.py                # 5×5 hyperparameter grid sweep
└── run_arms_race.py            # N-round arms race loop

outputs/
├── run_001/                    # RandomAttacker baseline
├── run_002/                    # DQNAttacker
├── run_003/                    # ParameterizedDQN (no ML)
├── run_003_ml/                 # ParameterizedDQN + ML (evasion case)
│   └── evasive_cache.npy       # 15 × 7 array of evasive feature vectors
├── run_004/                    # ParameterizedDQN + ML + cache (defender adapts)
├── run_lab/                    # Real Suricata + ML + cache
├── ablation_no_n1/             # DQN + cache (no intensity, N1 removed)
├── ablation_no_n3/             # ParameterizedDQN, λ=0 (no ML reward, N3 removed)
└── sweep_summary.json          # 25-cell DR/CAE heatmap results

lab/
├── docker-compose.yml          # Suricata 7.0.5 + nginx + SSH containers
├── rules/
│   └── disabled.conf           # List of intentionally disabled Suricata SIDs
└── baselines/
    └── normal_baseline.npy     # Real captured normal-traffic vectors (optional)

config.yaml                     # Default config
config_round3_ml.yaml           # ParameterizedDQN + ML, no cache
config_round4.yaml              # ParameterizedDQN + ML + evasive cache
config_lab_run.yaml             # Lab mode, 50 episodes
config_ablation_no_n1.yaml      # Ablation: DQN + cache
config_ablation_no_n3.yaml      # Ablation: ParameterizedDQN + λ=0
config_transfer_sim.yaml        # Transfer: seed=99
Makefile                        # All make targets
```

---

## 16. Output Files — What Gets Written After Each Run

| File | What's in it |
|---|---|
| `report_<ts>.md` | Jinja2-rendered Markdown: config, blind spots, ML analysis, Phase 1 gate, XAI |
| `run_manifest_<ts>.json` | JSON: config + all metrics (DR, RS, CAE, BSP, blind spots, gate pass/fail, git hash) |
| `policy_<ts>.json` | `{"ssh_brute_force": {"low": -0.2, "medium": 0.1, "high": 0.3}, ...}` — Q-values per (action, intensity) |
| `learning_curve_<ts>.json` | `[{"episode": 0, "total_reward": ..., "detected": ..., "mean_anomaly": ...}, ...]` |
| `evasive_cache.npy` | NumPy array (n_evaded × 7) — feature vectors of double blind spots |
| `dqn_checkpoint.pt` | PyTorch state_dict — online net weights, optimizer state, epsilon, step counts |

---

## 17. Data Flow Diagram — One Complete Step

```
config.yaml
    │ load_config()
    ▼
ExperimentConfig(episodes=200, seed=42, attacker_class="ParameterizedDQNAttacker", ...)
    │
    ├─ seed_everything(42) → sets random/np/torch seeds
    │
    ├─ _make_attacker() → ParameterizedDQNAttacker(ParameterizedDQNModel(50, 15, 3))
    │                        └─ online_net: Linear(50,64)→ReLU→Linear(64,64)→ReLU→Linear(64,45)
    │                        └─ target_net: copy of online_net
    │                        └─ buffer: deque(maxlen=4000)
    │
    └─ MLAnomalyDefence(threshold=0.63)
         └─ IsolationForest.fit(500 × 7 normal vectors)

For each episode i=0..199:
    │
    ├─ EpisodeState() — fresh state: completed={}, step=0, alerts=[]
    │
    └─ run_episode(state, action_selector, execute_fn, defence, parameterize_fn):
         │
         ├─ available = attack_graph.available_actions(completed)
         │   → [icmp_ping_sweep, tcp_port_scan, udp_sweep, dns_subdomain_enum]  (first step)
         │
         ├─ action_selector(available, state):
         │   │ ctx = build_context(state)  → float32[50]
         │   │   ├─ alert_history[-10:]   padded to 10 dims
         │   │   ├─ completed ∈ actions   15 dims (one-hot)
         │   │   ├─ detection_history rates  15 dims
         │   │   ├─ step/100, elapsed/3600  2 dims
         │   │   └─ fired ET categories  8 dims
         │   └─ attacker.choose_action(available, ctx)
         │       └─ ParameterizedDQNModel.select_action_with_intensity():
         │           ├─ online_net(ctx) → q[45]
         │           ├─ mask: set -inf for (action, intensity) pairs not in available
         │           ├─ if random() < ε: random (action, intensity) [exploration]
         │           └─ else: argmax(masked q) → (action_idx=3, intensity=0)
         │                    → "tcp_port_scan", intensity=0 (low)
         │
         ├─ execute_fn("tcp_port_scan")
         │   └─ sim: no-op
         │   └─ lab: ActionExecutor.execute(Action(..., port_range="1-100", rate_pps=2))
         │            → socket calls to 172.28.0.2; sleep(1.5)
         │
         ├─ parameterize_fn("tcp_port_scan")
         │   └─ get_params_for_intensity("tcp_port_scan", 0, ...)
         │       → {port_range: "1-100", rate_pps: 2, timing_ms: 100}
         │
         ├─ Action(action_id="tcp_port_scan", params={...}, timestamp=now)
         │
         ├─ MLAnomalyDefence.observe(action):
         │   ├─ encoder.encode(action) → feat[7]:
         │   │   feat[0] = 0/5 = 0.0          (category=scan)
         │   │   feat[1] = hash("tcp_port_scan") % 1000 / 1000 = 0.713
         │   │   feat[2] = 1/65535 = 0.000015  (port_range_start=1)
         │   │   feat[3] = 100/65535 = 0.0015  (port_range_end=100)
         │   │   feat[4] = 0.0                 (no attempts field)
         │   │   feat[5] = 100/10000 = 0.01    (timing_ms=100)
         │   │   feat[6] = 0.0                 (no wordlist)
         │   ├─ base_score = sigmoid(-IsolationForest.score_samples(feat)) = 0.61
         │   ├─ boost = _similarity_boost(feat)
         │   │   └─ if evasive_cache loaded: cosine_sim(feat, cached) → boost
         │   │   └─ if no cache: 0.0
         │   └─ DetectionResult(alerted=0.61<0.63→False, anomaly_score=0.61)
         │
         ├─ collect_feedback(state, "tcp_port_scan", alerted=False)
         │   ├─ detected = False
         │   ├─ stage_progress = "tcp_port_scan" unlocks ssh_brute_force etc → True
         │   └─ updates state: completed.add("tcp_port_scan"), alert_history.append(False)
         │
         ├─ compute_reward(detected=False, stage_progress=True) → +1.0
         │
         └─ StepRecord(action_id="tcp_port_scan", detected=False,
                        stage_progress=True, reward=1.0, anomaly_score=0.61)

    After episode completes:
         │
         ├─ for each step:
         │   shaped = step.reward - 0.5 * step.anomaly_score
         │   = 1.0 - 0.5 * 0.61 = 0.695
         │
         ├─ attacker.observe("tcp_port_scan", ctx_after, 0.695):
         │   └─ buffer.push(ctx_before, combined_idx(3, 0)=9, 0.695, ctx_after)
         │   └─ if buffer >= 32: sample 32, compute target_q, backprop
         │
         └─ EpisodeRecord(steps=[...], total_reward=..., completed=True, episode_index=0)
```

---

## 18. Key Metrics — How They're Computed

**Detection Rate (DR):**
```python
dr = sum(any(s.detected for s in r.steps) for r in records) / len(records)
# fraction of episodes where at least one step was detected
```

**Robustness Score (RS):**
```python
window = records[-10:]  # last 10 episodes
rs = sum(any(s.detected for s in r.steps) for r in window) / len(window)
# DR but only over the last 10 episodes — measures stability of current policy
```

**Cumulative Anomaly Exposure (CAE):**
```python
cae = sum(s.anomaly_score for r in records for s in r.steps)
# total ML anomaly signal accumulated across entire run
```

**Blind Spot Precision (BSP):**
```python
# From explain_evasions(): identify which action_ids evaded Suricata ≥50% of the time
# From validate_blind_spots(): cross-reference with lab/rules/disabled.conf
bsp = true_positives / total_reported
# fraction of reported blind spots that match genuinely disabled Suricata SIDs
```
