"""Ground-truth validation harness — computes Blind-Spot Precision against disabled SIDs."""
from __future__ import annotations

from dataclasses import dataclass

from aatf.explainability import ActionExplanation

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
        return self.blind_spot_precision >= 0.8


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
