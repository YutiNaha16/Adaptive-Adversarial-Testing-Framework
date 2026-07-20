# Adaptive Adversarial Testing Framework (AATF)

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Black Hat Europe 2026](https://img.shields.io/badge/Black%20Hat-Europe%202026-black.svg)](https://www.blackhat.com/eu-26/)

> **An autonomous RL measurement instrument that discovers structural blind spots in network intrusion-detection rulesets — then explains them to a defender.**

AATF deploys a reinforcement-learning attacker (DQN with parameter variation) against a live Suricata + ET Open deployment inside an isolated Docker lab. After every episode the attacker learns which actions and intensities evade detection; after N episodes the framework explains *why* they worked and recommends exactly which rule categories need retraining or threshold tuning.

---

## Key Results (Black Hat Europe 2026)

| Round | Attacker | Episodes | Detection Rate | Evasion Improvement |
|-------|----------|----------|---------------|---------------------|
| 1 | Random baseline | 100 | 13.3% | — |
| 2 | DQN (λ=0.5) | 200 | 13.3% | 0% (fixed params) |
| 3 | **Parameterized DQN** (λ=0.5) | 200 | **7.7%** | **+42%** |

**Novel contributions:**
1. **Action Parameter Variation** — DQN selects both action *and* execution intensity (low/medium/high), enabling sub-threshold evasion (2 SSH attempts < 5-attempt Suricata rule)
2. **Auto-Remediation** — automatically identifies double blind spots (evaded Suricata AND ML detector) and patches the anomaly scorer using cosine-similarity boosting

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Isolated Docker Lab                    │
│  ┌──────────────┐  actions   ┌────────────────────────┐ │
│  │ RL Attacker  │ ─────────► │  Real Services         │ │
│  │ (ParameterizedDQN)        │  nginx  172.28.0.3:80  │ │
│  │              │            │  sshd   172.28.0.2:22  │ │
│  └──────┬───────┘            └────────────────────────┘ │
│         │ reward signal                ▲                 │
│         ▼                             │ traffic          │
│  ┌──────────────┐            ┌────────┴───────────────┐ │
│  │ CompositeDefence          │  Suricata 7.0.5        │ │
│  │  SuricataDefence  ───────►│  ET Open ruleset       │ │
│  │  MLAnomalyDefence│        │  eve.json              │ │
│  └──────────────┘            └────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         │
         ▼
  ┌──────────────────────────────────────┐
  │  Phase 1 Gate + Explainability       │
  │  Blind-spot report (Markdown)        │
  │  ML Anomaly Defence Analysis         │
  │  Auto-Remediation Report             │
  │  Live Dashboard (Flask + Chart.js)   │
  └──────────────────────────────────────┘
```

---

## One-Command Setup

```bash
git clone https://github.com/yourusername/aatf.git
cd aatf
make setup          # create .venv + install all deps (~3 min for torch)
make demo           # 5-episode demo (no Docker needed) — ~30 s
```

**Full lab with real services:**

```bash
make lab-up         # start nginx + sshd + Suricata in isolated Docker network
make lab-traffic    # generate benign baseline traffic
make run            # 100 episodes (RandomAttacker)
make dashboard      # open http://localhost:5050 — live metrics
```

**Black Hat live demo sequence:**

```bash
make demo           # show terminal results in ~30 s
make dashboard      # open browser, show round comparison chart
```

---

## Requirements

| Tool | Version |
|------|---------|
| Python | 3.12 |
| GNU Make | any |
| Docker Engine | ≥ 20 (optional, for lab) |
| Docker Compose V2 | any (optional, for lab) |

Python dependencies are pinned and hash-verified in `requirements.txt`.

---

## Available Make Targets

```
make setup            Create .venv and install all deps (run once)
make test             Run pytest test suite (no Docker needed)
make lint             ruff check + format
make run              Run 100-episode experiment (simulation mode)
make demo             5-episode demo with ParameterizedDQN (~30 s)
make dashboard        Start live dashboard at http://localhost:5050
make lab-up           Build Docker lab (nginx + sshd + Suricata)
make lab-down         Stop and remove lab containers
make lab-traffic      Generate benign HTTP/SSH baseline traffic
make lab-smoke        Verify Suricata SID fires in eve.json
make lab-check        Verify lab has no outbound internet access
make lab-status       Show lab container health
make transferability  Two-config blind-spot comparison (structural gaps)
```

---

## Experiment Configurations

| Config | Attacker | Episodes | Purpose |
|--------|----------|----------|---------|
| `config.yaml` | RandomAttacker | 100 | Phase 1 baseline |
| `config_round2.yaml` | DQNAttacker | 200 | RL without param variation |
| `config_round3.yaml` | ParameterizedDQNAttacker | 200 | Full novelty (BH demo) |
| `config_demo.yaml` | ParameterizedDQNAttacker | 5 | Live demo (fast) |
| `config_transfer.yaml` | ParameterizedDQNAttacker | 200 | Transferability test |

---

## How It Works

### Phase 1 — Suricata Rule Measurement

The framework runs N episodes. Each episode the RL attacker selects an action (tcp_port_scan, ssh_brute_force, http_dir_scan, …) and an intensity (low/medium/high). The `ActionExecutor` sends real traffic to the Docker targets; `SuricataDefence` checks eve.json for alerts.

Blind spots = actions that consistently evade Suricata. The `explainability` module maps each blind spot to the specific ET Open SID categories that should cover it, giving defenders an actionable fix list.

### Phase 2 — ML Anomaly Detection

`MLAnomalyDefence` wraps an `IsolationForest` trained on a synthetic normal-traffic baseline. It scores each action on a 7-dimensional feature vector (category, action hash, port range, attempt count, timing, wordlist size). Scores are combined with Suricata alerts via `CompositeDefence`.

`anomaly_lambda` in the shaped reward `r' = r - λ·anomaly_score` teaches the DQN to prefer low-intensity variants that fly under the ML radar.

### Novelty 1 — Action Parameter Variation

`ParameterizedDQNAttacker` uses a 45-output Q-network (15 actions × 3 intensities). At intensity 0 (low), `ssh_brute_force` sends 2 attempts — below Suricata's 5-attempt detection threshold. This produced the 42% improvement in Round 3.

### Novelty 2 — Auto-Remediation

After each run, `auto_remediate()` identifies double blind spots (not detected by Suricata AND anomaly_score < 0.3). Their feature vectors are cached. Future observations near these vectors get a cosine-similarity score boost, progressively closing the gaps without retraining the IsolationForest.

---

## Transferability Test

The transferability test proves blind spots are *structural*, not artefacts of a specific disabled-rules config:

```bash
make transferability
```

Runs the same ParameterizedDQN attacker against two different `disabled.conf` files (different SIDs suppressed) and shows the overlap. Actions that evade both configs are genuine ruleset gaps, not measurement artefacts.

---

## Novelty Position vs. Prior Work

| System | Side | Domain | Evasion | Attacker adaptive? |
|--------|------|--------|---------|-------------------|
| AMIDES (USENIX '24) | Defender | Windows host logs | Hand-crafted | No |
| Finding Needles ('24) | Defender | Network PCAP | Statistical | No |
| **AATF (this work)** | **Attacker** | **Network + ML** | **RL-discovered** | **Yes (DQN)** |

AATF is the first *attacker-side* autonomous measurement instrument for network signature detection that simultaneously optimises against both rule-based and ML-based defences.

---

## Project Structure

```
src/aatf/
├── config.py              ExperimentConfig (Pydantic V2)
├── action_library.py      15 network attack actions registry
├── action_intensity.py    Novelty 1: intensity override table
├── action_executor.py     Sends real traffic to lab targets
├── dqn_attacker.py        DQNAttacker + ParameterizedDQNAttacker
├── ml_defence.py          IsolationForest + auto_remediate (Novelty 2)
├── defence.py             CompositeDefence (Suricata + ML)
├── suricata_defence.py    SuricataDefence (eve.json reader)
├── episode.py             Episode loop, StepRecord
├── metrics.py             detection_rate, robustness_score, CAE
├── explainability.py      Blind-spot → SID category mapping
├── report.py              Jinja2 Markdown report generator
└── templates/
    └── report.md.j2       Report template (includes ML section)
src/dashboard/
└── app.py                 Flask live metrics dashboard
lab/
├── docker-compose.yml     nginx + sshd + Suricata in isolated network
├── Dockerfile.target-web  nginx:alpine web target (172.28.0.3)
├── Dockerfile.target-ssh  Alpine + openssh SSH target (172.28.0.2)
├── Dockerfile.suricata    Suricata 7.0.5 + ET Open rules (baked in)
└── scripts/               check-isolation, lab-status, lab-smoke, compare-blind-spots
docs/explainer/
├── 01-overview.md         ...
└── 09-ml-phase.md         ML anomaly detection + DQN architecture explainer
```

---

## Reproducibility

All dependencies are pinned and hash-verified (`requirements.txt`). Every run produces a `run_manifest_<ISO>.json` capturing seed, git commit, package versions, and config snapshot. Same seed + same config = identical results.

---

## Safety

All attacker traffic is confined to the isolated `aatf-lab` Docker network (`internal: true`). The lab has no outbound internet access (`make lab-check` verifies this). The framework is a *measurement instrument for defenders*, not an attack tool.

---

## License

MIT. Intended for authorized security research and education only.
