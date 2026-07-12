"""Report generator — renders blind-spot Markdown report from episode logs."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from aatf.action_library import ActionRegistry
from aatf.explainability import explain_evasions
from aatf.metrics import EpisodeRecord, detection_rate, robustness_score
from aatf.statistics import summarise_metric

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def generate_report(
    records: list[EpisodeRecord],
    registry: ActionRegistry,
    output_path: str | Path,
    *,
    generated_at: datetime | None = None,
) -> str:
    out = Path(output_path)
    if not out.parent.exists():
        raise FileNotFoundError(f"Output directory does not exist: {out.parent}")

    if generated_at is None:
        generated_at = datetime.now(UTC)

    attacker_classes = sorted({r.attacker_class for r in records})
    seeds = sorted({r.seed for r in records})
    episode_count = len(records)
    window = min(10, len(records))
    dr = detection_rate(records)
    rs = robustness_score(records, window=window)
    reward_values = [r.total_reward for r in records]
    reward_summary = summarise_metric("total_reward", reward_values) if reward_values else None
    explanations = explain_evasions(records, registry)

    ctx = {
        "attacker_classes": attacker_classes,
        "seeds": seeds,
        "episode_count": episode_count,
        "generated_at": generated_at.isoformat(),
        "detection_rate": dr,
        "robustness_score": rs,
        "robustness_window": window,
        "reward_mean": reward_summary.mean if reward_summary else None,
        "reward_std": reward_summary.std if reward_summary else None,
        "reward_ci_low": reward_summary.ci_low if reward_summary else None,
        "reward_ci_high": reward_summary.ci_high if reward_summary else None,
        "explanations": explanations,
    }

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = env.get_template("report.md.j2")
    rendered = template.render(**ctx)

    out.write_text(rendered, encoding="utf-8")
    return rendered
