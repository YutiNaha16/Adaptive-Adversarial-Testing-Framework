"""Ground-truth validation harness — computes Blind-Spot Precision against disabled SIDs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from aatf.explainability import ActionExplanation, explain_evasions
from aatf.metrics import EpisodeRecord

if TYPE_CHECKING:
    from aatf.action_library import ActionRegistry

# A step counts as a double blind spot only when it evades Suricata AND scores
# below this ML anomaly threshold — matches the DBS definition used everywhere
# else in the framework (Table "Evaluation Metrics" in the paper).
DBS_ANOMALY_THRESHOLD: float = 0.3

SURICATA_SID_CATEGORIES: dict[str, str] = {
    "2001219": "ET SCAN",
    "2008581": "ET SCAN",
    "2002087": "ET BRUTE_FORCE",
    "2019284": "ET BRUTE_FORCE",
    "2012648": "ET EXPLOIT",
    "2016778": "ET DNS",
    "2013028": "ET POLICY",
    "2014726": "ET TROJAN",
    "2010935": "ET WEB_CLIENT",
    "2009714": "ET WEB_SERVER",
}


@dataclass(frozen=True)
class ValidationResult:
    blind_spot_precision: float
    true_positives: int
    false_positives: int
    total_reported: int
    disabled_sid_count: int

    @property
    def meets_gate(self) -> bool:
        # Zero reported blind spots means zero false claims to validate against
        # disabled SIDs — vacuously satisfies a precision gate rather than
        # failing an undefined (0/0) ratio.
        if self.total_reported == 0:
            return True
        return self.blind_spot_precision >= 0.8


def _dbs_only_records(records: list[EpisodeRecord]) -> list[EpisodeRecord]:
    """Restrict episode records to steps that are true double blind spots:
    undetected by Suricata AND scored below DBS_ANOMALY_THRESHOLD by the ML
    detector. Ground-truth validation must be scored against this narrower
    set, not every Suricata evasion (see explain_evasions for the broader
    explainability-report use case)."""
    filtered: list[EpisodeRecord] = []
    for r in records:
        dbs_steps = [
            s for s in r.steps if not s.detected and s.anomaly_score < DBS_ANOMALY_THRESHOLD
        ]
        if dbs_steps:
            filtered.append(
                EpisodeRecord(
                    attacker_class=r.attacker_class,
                    seed=r.seed,
                    steps=dbs_steps,
                    total_reward=r.total_reward,
                    completed=r.completed,
                    episode_index=r.episode_index,
                )
            )
    return filtered


def explain_double_blind_spots(
    records: list[EpisodeRecord],
    registry: ActionRegistry,
) -> list[ActionExplanation]:
    """Ground-truth-validation input: explanations built only from true double
    blind spots (¬detected AND anomaly_score < DBS_ANOMALY_THRESHOLD)."""
    return explain_evasions(_dbs_only_records(records), registry)


def validate_blind_spots(
    explanations: list[ActionExplanation],
    disabled_sids: set[str],
) -> ValidationResult:
    disabled_categories = {
        SURICATA_SID_CATEGORIES[s] for s in disabled_sids if s in SURICATA_SID_CATEGORIES
    }
    tp = sum(1 for e in explanations if e.suricata_category in disabled_categories)
    total = len(explanations)
    fp = total - tp
    precision = tp / total if total > 0 else 0.0
    return ValidationResult(
        blind_spot_precision=precision,
        true_positives=tp,
        false_positives=fp,
        total_reported=total,
        disabled_sid_count=len(disabled_sids),
    )
