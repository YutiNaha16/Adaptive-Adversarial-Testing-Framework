"""AATF Live Dashboard — Flask backend serving experiment metrics and reports.

Start: python src/dashboard/app.py   or   make dashboard
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from flask import Flask, jsonify, render_template

app = Flask(__name__)

_OUTPUTS_DIR = Path(os.environ.get("AATF_OUTPUTS", "outputs"))

# Canonical display order for BH story: Random → DQN → ParameterizedDQN
_CANONICAL = ["run_001", "run_002", "run_003"]

# Attacker short labels
_ATTACKER_SHORT = {
    "RandomAttacker": "Random",
    "DQNAttacker": "DQN",
    "ParameterizedDQNAttacker": "Param-DQN",
    "LinUCBAttacker": "LinUCB",
    "FixedScriptAttacker": "Fixed",
}

# Category colours for blind-spot table
_CAT_COLOUR = {
    "ET SCAN": "#58a6ff",
    "ET BRUTE_FORCE": "#f85149",
    "ET WEB_SERVER": "#e3b341",
    "ET WEB_CLIENT": "#e3b341",
    "ET DNS": "#bc8cff",
    "ET POLICY": "#3fb950",
    "ET TROJAN": "#ff7b72",
    "ET EXPLOIT": "#ffa657",
}


# ---------------------------------------------------------------------------
# Markdown report parsers
# ---------------------------------------------------------------------------


def _table_rows(report: str, header_marker: str) -> list[list[str]]:
    """Generic table row extractor that tolerates blank lines between rows."""
    rows: list[list[str]] = []
    in_table = False
    past_separator = False
    for line in report.splitlines():
        stripped = line.strip()
        if header_marker in stripped and stripped.startswith("|"):
            in_table = True
            past_separator = False
            continue
        if not in_table:
            continue
        if stripped.startswith("|-"):
            past_separator = True
            continue
        if not stripped:
            continue  # blank lines between rows are fine — keep scanning
        if not stripped.startswith("|"):
            in_table = False  # non-pipe non-blank line ends the table
            continue
        if past_separator:
            parts = [p.strip() for p in stripped.split("|") if p.strip()]
            if parts:
                rows.append(parts)
    return rows


def _parse_blind_spots(report: str) -> list[dict]:
    """Extract rows from the Blind Spots table in a report."""
    rows: list[dict] = []
    for parts in _table_rows(report, "Evasion Rate"):
        if len(parts) < 4:
            continue
        try:
            evasion_pct = float(parts[2].rstrip("%"))
        except ValueError:
            continue
        rows.append(
            {
                "action": parts[0],
                "category": parts[1],
                "evasion_pct": evasion_pct,
                "evaded": int(parts[3]) if parts[3].isdigit() else 0,
                "total": int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0,
                "cat_colour": _CAT_COLOUR.get(parts[1], "#8b949e"),
            }
        )
    return sorted(rows, key=lambda r: -r["evasion_pct"])


def _parse_ml_evasive(report: str) -> list[dict]:
    rows: list[dict] = []
    for parts in _table_rows(report, "Mean Anomaly (undetected)"):
        if len(parts) < 4:
            continue
        try:
            rows.append(
                {
                    "action": parts[0],
                    "category": parts[1],
                    "mean_anomaly": float(parts[2]),
                    "undetected_steps": int(parts[3]),
                }
            )
        except (ValueError, IndexError):
            continue
    return rows


def _parse_ml_suspicious(report: str) -> list[dict]:
    rows: list[dict] = []
    for parts in _table_rows(report, "Mean Anomaly (all steps)"):
        if len(parts) < 4:
            continue
        try:
            rows.append(
                {
                    "action": parts[0],
                    "category": parts[1],
                    "mean_anomaly": float(parts[2]),
                    "total_steps": int(parts[3]),
                }
            )
        except (ValueError, IndexError):
            continue
    return rows


def _parse_cae_from_report(report: str) -> float | None:
    """Extract CAE value from the ML section header line."""
    m = re.search(r"CAE\s*=\s*([\d.]+)", report)
    return float(m.group(1)) if m else None


def _parse_retrain_categories(report: str) -> list[str]:
    """Extract retraining categories from the ML section."""
    cats: list[str] = []
    in_retrain = False
    for line in report.splitlines():
        if "Retraining Recommendation" in line:
            in_retrain = True
            continue
        if in_retrain:
            if line.startswith("#"):
                break
            m = re.match(r"\s*[-*]\s*\*\*(.+?)\*\*", line)
            if m:
                cats.append(m.group(1))
    return cats


# ---------------------------------------------------------------------------
# Run loader
# ---------------------------------------------------------------------------


def _load_runs() -> list[dict]:
    """Load one entry per run_dir (latest manifest wins), sorted by timestamp."""
    by_dir: dict[str, dict] = {}

    if not _OUTPUTS_DIR.exists():
        return []

    for manifest_path in sorted(_OUTPUTS_DIR.rglob("run_manifest_*.json")):
        try:
            data = json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        run_dir = manifest_path.parent.name
        cfg = data.get("config_snapshot", {})
        gate = data.get("phase1_gate", {})
        criteria = {c["name"]: c for c in gate.get("criteria", [])}

        dr = data.get("detection_rate") or criteria.get("detection_rate", {}).get("value", 0.0)
        rs = data.get("robustness_score") or criteria.get("robustness_score", {}).get("value", 0.0)
        cae_val = data.get("cae")

        # Latest report in the same dir
        reports = sorted(manifest_path.parent.glob("report_*.md"))
        report_text = reports[-1].read_text() if reports else ""

        blind_spots = _parse_blind_spots(report_text)
        ml_evasive = _parse_ml_evasive(report_text)
        ml_suspicious = _parse_ml_suspicious(report_text)
        retrain_cats = _parse_retrain_categories(report_text)

        # Use report CAE if manifest doesn't have it
        if cae_val is None:
            cae_val = _parse_cae_from_report(report_text)

        attacker_raw = cfg.get("attacker_class", "?")
        entry = {
            "run_dir": run_dir,
            "timestamp": data.get("timestamp", ""),
            "attacker": attacker_raw,
            "attacker_short": _ATTACKER_SHORT.get(attacker_raw, attacker_raw[:10]),
            "episodes": cfg.get("episodes", 0),
            "seed": cfg.get("seed", 42),
            "detection_rate": round(float(dr), 4),
            "robustness_score": round(float(rs), 4),
            "cae": round(float(cae_val), 4) if cae_val is not None else None,
            "phase1_passed": gate.get("passed", False),
            "git_commit": data.get("git_commit", "")[:8],
            "blind_spots": blind_spots,
            "ml_evasive": ml_evasive,
            "ml_suspicious": ml_suspicious,
            "retrain_categories": retrain_cats,
            "n_blind_spots": len(blind_spots),
            "is_canonical": run_dir in _CANONICAL,
        }

        # Keep the later timestamp per run_dir
        prev = by_dir.get(run_dir)
        if prev is None or entry["timestamp"] > prev["timestamp"]:
            by_dir[run_dir] = entry

    all_runs = sorted(by_dir.values(), key=lambda r: r["timestamp"])
    return all_runs


def _canonical_runs(all_runs: list[dict]) -> list[dict]:
    by_dir = {r["run_dir"]: r for r in all_runs}
    return [by_dir[k] for k in _CANONICAL if k in by_dir]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    all_runs = _load_runs()
    canonical = _canonical_runs(all_runs)

    # Chart data for canonical rounds
    c_labels = [f"Round {i + 1}\n{r['attacker_short']}" for i, r in enumerate(canonical)]
    c_dr = [round(r["detection_rate"] * 100, 2) for r in canonical]
    c_rs = [round(r["robustness_score"] * 100, 2) for r in canonical]
    c_cae = [r["cae"] if r["cae"] is not None else 0 for r in canonical]

    # Latest canonical round for KPIs
    latest = canonical[-1] if canonical else None
    baseline = canonical[0] if canonical else None

    evasion_improvement = None
    if latest and baseline and baseline["detection_rate"] > 0:
        evasion_improvement = round(
            (1 - latest["detection_rate"] / baseline["detection_rate"]) * 100, 1
        )

    # All-runs timeline (only those with detection_rate > 0)
    timeline_runs = [r for r in all_runs if r["detection_rate"] > 0]
    t_labels = [f"{r['run_dir']}" for r in timeline_runs]
    t_dr = [round(r["detection_rate"] * 100, 2) for r in timeline_runs]

    return render_template(
        "dashboard.html",
        canonical=canonical,
        all_runs=all_runs,
        latest=latest,
        baseline=baseline,
        evasion_improvement=evasion_improvement,
        c_labels=json.dumps(c_labels),
        c_dr=json.dumps(c_dr),
        c_rs=json.dumps(c_rs),
        c_cae=json.dumps(c_cae),
        t_labels=json.dumps(t_labels),
        t_dr=json.dumps(t_dr),
    )


@app.route("/api/runs")
def api_runs():
    runs = _load_runs()
    # Remove blind_spots list from JSON (too large for API response)
    slim = [
        {k: v for k, v in r.items() if k not in ("blind_spots", "ml_evasive", "ml_suspicious")}
        for r in runs
    ]
    return jsonify(slim)


if __name__ == "__main__":
    port = int(os.environ.get("AATF_PORT", 5050))
    print(f"AATF Dashboard → http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
