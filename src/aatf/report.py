"""Report generator — renders blind-spot Markdown report from episode logs."""

from __future__ import annotations

import dataclasses
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from aatf.action_library import ActionRegistry
from aatf.explainability import explain_evasions
from aatf.metrics import (
    EpisodeRecord,
    cumulative_anomaly_exposure,
    detection_rate,
    robustness_score,
)
from aatf.statistics import summarise_metric

_TEMPLATE_DIR = Path(__file__).parent / "templates"

EVASION_THRESHOLD: float = 0.3


@dataclasses.dataclass(frozen=True)
class MLActionStats:
    action_id: str
    category: str
    mean_anomaly_all: float
    mean_anomaly_undetected: float
    total_steps: int
    undetected_steps: int


@dataclasses.dataclass(frozen=True)
class MLAnalysisSummary:
    cae: float
    episode_count: int
    evasive: list[MLActionStats]
    suspicious: list[MLActionStats]
    retrain_categories: list[str]


def _has_ml_scores(records: list[EpisodeRecord]) -> bool:
    return any(s.anomaly_score > 0 for r in records for s in r.steps)


def _compute_ml_summary(
    records: list[EpisodeRecord], registry: ActionRegistry
) -> MLAnalysisSummary:
    all_scores: dict[str, list[float]] = defaultdict(list)
    undetected_scores: dict[str, list[float]] = defaultdict(list)

    for r in records:
        for s in r.steps:
            all_scores[s.action_id].append(s.anomaly_score)
            if not s.detected:
                undetected_scores[s.action_id].append(s.anomaly_score)

    stats: list[MLActionStats] = []
    for action_id, scores in all_scores.items():
        try:
            category = registry.get_action(action_id).suricata_category
        except KeyError:
            category = "UNKNOWN"
        u_scores = undetected_scores.get(action_id, [])
        stats.append(
            MLActionStats(
                action_id=action_id,
                category=category,
                mean_anomaly_all=sum(scores) / len(scores),
                mean_anomaly_undetected=sum(u_scores) / len(u_scores) if u_scores else 0.0,
                total_steps=len(scores),
                undetected_steps=len(u_scores),
            )
        )

    evasive = sorted(
        (a for a in stats if a.undetected_steps > 0),
        key=lambda a: a.mean_anomaly_undetected,
    )[:5]

    suspicious = sorted(stats, key=lambda a: a.mean_anomaly_all, reverse=True)[:5]

    retrain_categories = sorted(
        {
            a.category
            for a in stats
            if a.undetected_steps > 0 and a.mean_anomaly_undetected < EVASION_THRESHOLD
        }
    )

    return MLAnalysisSummary(
        cae=cumulative_anomaly_exposure(records),
        episode_count=len(records),
        evasive=evasive,
        suspicious=suspicious,
        retrain_categories=retrain_categories,
    )


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

    ctx["ml_summary"] = _compute_ml_summary(records, registry) if _has_ml_scores(records) else None

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = env.get_template("report.md.j2")
    rendered = template.render(**ctx)

    out.write_text(rendered, encoding="utf-8")
    return rendered
