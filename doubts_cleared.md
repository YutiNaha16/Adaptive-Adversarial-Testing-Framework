# Doubts Cleared — AATF Paper Verification

All numbers verified directly from `run_manifest_*.json` files and source code.

---

## 1. Is 89.87% or 89.97% correct?

**89.87% is correct.**

From `outputs/run_004/run_manifest_*.json`:
```
"detection_rate": 0.8986666...
```
`0.8986... × 100 = 89.87%` (rounded to 2 decimal places).

The dashboard displayed `89.9%` (rounded to 1 dp), which may have looked like `89.97%` at a glance — it isn't. The paper body and abstract both say `89.87%`. **No fix needed.**

---

## 2. Abstract says 15.57% DR but §6.9 table says 12.33% — which is right?

**Both numbers exist in the data but refer to different runs. This is a real inconsistency that needs a fix.**

| Run | Output directory | Attacker | Episodes | DR |
|-----|-----------------|----------|----------|----|
| Background lab task | `outputs/run_lab/` | ParameterizedDQN | 200 | **15.57%** |
| `config_lab_200.yaml` run (with cache) | `outputs/run_lab_200/` | ParameterizedDQN | 200 | **12.33%** |

The paper body (§6.9 Table 16) reports `12.33%` — this is from `run_lab_200`, the deliberate cache-loaded lab run described in that section.

The abstract says `15.57%` — this is from `run_lab`, a different background task run (no explicit cache).

**Fix needed:** Change the abstract's `15.57%` → `12.33%` so it matches the body. The relevant sentence is:

> "loading a simulation-derived cache in lab mode achieves only **15.57%** DR"

Should become:

> "loading a simulation-derived cache in lab mode achieves only **12.33%** DR"

Also update the second instance in §4.2 (Contributions bullet) if it mentions 15.57%.

---

## 3. Table 17 (DQN Lab) — which run does it refer to: `dqn_run_001` or `run_dqn_lab`?

**Table 17 refers to `run_dqn_lab`. The two runs are completely different experiments.**

| Run | Config | Attacker | Episodes | λ | Mode | DR | CAE |
|-----|--------|----------|----------|---|------|----|-----|
| `dqn_run_001` | `config_dqn.yaml` | DQNAttacker | 200 | 1.0 | LAB (Suricata only) | ~13.3% | 0.0 |
| `run_dqn_lab` | `config_dqn_lab.yaml` | DQNAttacker | 100 | 0.0 | LAB (Suricata+ML) | **13.27%** | **9.27** |

Table 17 shows DR=13.27%, CAE=9.27, λ=0.0, 100 episodes — these all match `run_dqn_lab` exactly.

`dqn_run_001` used λ=1.0, ran 200 episodes, and was Suricata-only (no ML composite defence), giving CAE≈0. It was an earlier exploratory run and is not the run cited in the paper.

---

## 4. If λ=0.0 means no anomaly penalty, why does Table 17 show CAE=9.27 (not zero)?

**Because in LAB mode, the ML detector always runs regardless of λ.**

Here is how `run_experiment.py` works:

```
LAB mode (--lab flag):
  → Always instantiates: CompositeDefence(SuricataDefence, MLAnomalyDefence)
  → ML detector scores every action → anomaly_score > 0 → CAE > 0
  → λ only controls reward shaping: shaped_reward = base_reward − λ × anomaly_score
  → With λ=0: anomaly_score is computed but doesn't change reward

SIM mode (no --lab):
  → If λ > 0: instantiates MLAnomalyDefence
  → If λ = 0: instantiates NullDefence → anomaly_score = 0.0 → CAE = 0.0
```

So:
- **Ablation –N3** (SIM mode, λ=0) → NullDefence → CAE=0.0 ✓ (footnote † is correct for this case)
- **run_dqn_lab** (LAB mode, λ=0) → MLAnomalyDefence still active → CAE=9.27 ✓ (correct)

The footnote in §6.3 says "all anomaly_score values = 0.0" — that is only true for the SIM-mode ablation, not for any LAB-mode run. The paper's existing † footnote is technically correct for the ablation but could confuse readers about the DQN lab run. Consider adding a clarifying note in §6.10 like: "Note: λ=0 suppresses the anomaly penalty in the reward signal but does not disable the ML detector; the IsolationForest scores all steps and contributes to CAE."

---

## 5. §1.1 says "Section 8 concludes" — is this correct?

**No. This is a cross-reference error.**

Section 8 in the paper is "Related Work (Expanded)". Section 9 is "Conclusion".

**Fix:** In §1.1 change "Section 8 concludes" → "Section 9 concludes".

---

## 6. §4.6 says "ablation (Section 6.4)" — is this correct?

**No. Another cross-reference error.**

Section 6.3 is the Ablation Study. Section 6.4 is the Hyperparameter Sweep.

**Fix:** In §4.6 change "ablation (Section 6.4)" → "ablation (Section 6.3)".

---

## 7. `velan2015survey` cited for "port-scan detectors" in §8.2 — is this right?

**No. Wrong citation.**

`velan2015survey` is a survey on encrypted traffic classification (network flow categorisation). It is not about port-scan detection.

**Fix options:**
- Drop the clause "port-scan detectors [23]" if you cannot find a suitable replacement.
- Replace with a proper port-scan detection paper (e.g., Paxson 1998 "Bro" or Jung et al. 2004 "Fast portscan detection").

---

## 8. Table 7 Mode column — screenshot shows `config_round2.yaml` was run with `--lab` flag, but Table 7 says "Sim"

**This is a real inconsistency.**

The terminal screenshot shows:
```
python src/run_experiment.py --lab --config config_round2.yaml
```

But Table 7 (8-Round Arms Race) lists config_round2.yaml with Mode = "Sim".

**Fix:** Update Table 7 Row 2 Mode column from "Sim" → "Lab". (Check config_round1.yaml as well — if it was also run with --lab, update that row too.)

---

## 9. §6.1 Baseline Table shows DR=100% for Random/FixedScript/LinUCB, but lab screenshots show ~12-13% — contradiction?

**Not a contradiction. They are different experiment modes.**

- **Table 9 (§6.1 Baseline Comparison)** reports SIM mode results (IsolationForest detector, no Suricata). Against the simulated IsolationForest with proper λ=0.5 shaping, Random/FixedScript/LinUCB are detected 100% of the time because they make no attempt to evade ML scoring.

- **Lab screenshots** show the same attacker classes run in LAB mode (real Suricata + ML). Detection rate drops to ~12-13% in lab because Suricata's ET Open ruleset misses many simulated attack patterns (the sim-to-lab gap).

These are intentionally separate rows in your experimental design. There is no error in the paper — the table footnote should clarify these are SIM-mode baselines if it doesn't already.

---

## 10. ET Open Disclosure — status?

**Not done yet.** The paper says "will be reported to the ET Open maintainers prior to publication" — that wording is correct and is a future commitment. You need to actually submit the disclosure before submitting the paper. The Suricata ET Open project accepts rule gap reports via their GitHub issues at `https://github.com/proofpoint/et-open`.

---

## Summary of fixes required in PAPER_DRAFT.md

| # | Location | Issue | Fix |
|---|----------|-------|-----|
| 1 | Abstract | "15.57% DR" (cache-loaded lab) | Change to **12.33%** |
| 2 | §4.2 (if present) | Same 15.57% figure in contributions | Change to **12.33%** |
| 3 | §1.1 | "Section 8 concludes" | Change to **Section 9 concludes** |
| 4 | §4.6 | "ablation (Section 6.4)" | Change to **ablation (Section 6.3)** |
| 5 | §8.2 | velan2015survey cited for "port-scan detectors" | Drop clause or replace citation |
| 6 | Table 7 Row 2 | Mode = "Sim" for config_round2.yaml | Change to **Lab** |
| 7 | §6.10 (optional) | λ=0 in LAB mode still has ML active | Add a one-line clarification note |

Numbers that are **already correct** and need no change:
- 89.87% auto-remediation DR ✓
- §6.9 table 12.33% cache-loaded lab DR ✓  
- Table 17 DR=13.27%, CAE=9.27, λ=0.0, 100 episodes ✓
- §6.3 ablation –N3 CAE=0.0 ✓ (applies to SIM mode only)

---

*Verified 2026-07-24 from: `outputs/run_004/`, `outputs/run_lab/`, `outputs/run_lab_200/`, `outputs/run_dqn_lab/`, `outputs/dqn_run_001/`, `src/run_experiment.py` lines 91–144.*
