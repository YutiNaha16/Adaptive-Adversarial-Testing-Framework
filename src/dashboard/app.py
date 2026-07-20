"""AATF Live Dashboard — Flask app that reads run manifests and renders metrics.

Start with:  python src/dashboard/app.py
Or:          make dashboard
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Flask, render_template

app = Flask(__name__)

_OUTPUTS_DIR = Path(os.environ.get("AATF_OUTPUTS", "outputs"))


def _load_runs() -> list[dict]:
    """Scan outputs/ for run manifests and return sorted run summaries."""
    runs: list[dict] = []
    if not _OUTPUTS_DIR.exists():
        return runs

    for manifest_path in sorted(_OUTPUTS_DIR.rglob("run_manifest_*.json")):
        try:
            data = json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        cfg = data.get("config_snapshot", {})
        gate = data.get("phase1_gate", {})
        criteria = {c["name"]: c for c in gate.get("criteria", [])}

        run_dir = manifest_path.parent.name
        dr = criteria.get("detection_rate", {}).get("value", 0.0)
        rs = criteria.get("robustness_score", {}).get("value", 0.0)
        cae = data.get("cae", None)

        # Find accompanying report for blind-spot table
        report_text = ""
        for rp in sorted(manifest_path.parent.glob("report_*.md")):
            report_text = rp.read_text()
            break

        runs.append(
            {
                "run_dir": run_dir,
                "timestamp": data.get("timestamp", "?"),
                "attacker": cfg.get("attacker_class", "?"),
                "episodes": cfg.get("episodes", 0),
                "seed": cfg.get("seed", 42),
                "detection_rate": round(dr, 4),
                "robustness_score": round(rs, 4),
                "cae": round(cae, 4) if cae is not None else "N/A",
                "phase1_passed": gate.get("passed", False),
                "git_commit": data.get("git_commit", "?")[:8],
                "report_excerpt": report_text[:500] if report_text else "",
            }
        )

    runs.sort(key=lambda r: r["timestamp"])
    return runs


@app.route("/")
def index():
    runs = _load_runs()
    labels = [f"{r['run_dir']}\n({r['attacker'][:6]})" for r in runs]
    dr_values = [r["detection_rate"] for r in runs]
    rs_values = [r["robustness_score"] for r in runs]
    cae_values = [r["cae"] if isinstance(r["cae"], float) else None for r in runs]
    return render_template(
        "dashboard.html",
        runs=runs,
        labels=json.dumps(labels),
        dr_values=json.dumps(dr_values),
        rs_values=json.dumps(rs_values),
        cae_values=json.dumps(cae_values),
    )


@app.route("/api/runs")
def api_runs():
    from flask import jsonify

    return jsonify(_load_runs())


if __name__ == "__main__":
    port = int(os.environ.get("AATF_PORT", 5050))
    print(f"AATF Dashboard running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
