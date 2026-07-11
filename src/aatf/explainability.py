"""Explainability engine — maps evaded actions to ranked remediation hints."""

from __future__ import annotations

from dataclasses import dataclass

from aatf.action_library import ActionRegistry
from aatf.metrics import EpisodeRecord

_FALLBACK: tuple[str, str] = (
    "Review and update Suricata rule signatures for this technique category; "
    "consult the ET PRO ruleset documentation for coverage recommendations.",
    "Unknown: assess false-positive risk empirically against your environment's "
    "baseline traffic before enabling.",
)

REMEDIATION_TABLE: dict[str, tuple[str, str]] = {
    "ET SCAN": (
        "Review ET SCAN ruleset thresholds; consider lowering scan detection sensitivity "
        "or narrowing source IP ranges. Verify scan interval thresholds match your "
        "environment's normal discovery traffic.",
        "High: network scan rules frequently trigger on legitimate discovery tools and "
        "asset-management probes.",
    ),
    "ET BRUTE_FORCE": (
        "Enable or tighten ET BRUTE_FORCE rules; set login-attempt thresholds to match "
        "your environment's expected authentication volume. Consider adding detection for "
        "slow-rate credential stuffing.",
        "Medium: high-frequency legitimate login systems (CI/CD, SSO agents) may trigger "
        "brute-force rules.",
    ),
    "ET EXPLOIT": (
        "Activate and tune ET EXPLOIT signatures for the specific service version targeted. "
        "Ensure vulnerability scanner traffic is excluded from triggering these rules.",
        "Low: exploit signatures are highly specific; false positives are rare but possible "
        "on unusual protocol implementations.",
    ),
    "ET DNS": (
        "Enable ET DNS rules for zone transfer and subdomain enumeration; tune query-rate "
        "thresholds to your resolver's legitimate query volume.",
        "Medium: high-volume DNS resolvers and CDN prefetching can generate patterns "
        "resembling DNS reconnaissance.",
    ),
    "ET POLICY": (
        "Review ET POLICY rules for data-exfiltration patterns; enable DNS and HTTP "
        "exfiltration signatures and set volume thresholds appropriate to baseline traffic.",
        "High: policy rules covering large data transfers can trigger on legitimate backup "
        "or sync traffic.",
    ),
    "ET TROJAN": (
        "Enable ET TROJAN signatures covering HTTP-based C2 patterns; update rule sets "
        "frequently as evasion techniques evolve rapidly in this category.",
        "Low: trojan signatures are narrow; false positives are uncommon but possible with "
        "custom internal tooling using similar HTTP patterns.",
    ),
    "ET WEB_CLIENT": (
        "Enable ET WEB_CLIENT rules for XSS probe patterns; ensure your web application "
        "firewall is configured to complement Suricata detections.",
        "Medium: legitimate security scanners and browser automation tools may trigger "
        "XSS detection rules.",
    ),
    "ET WEB_SERVER": (
        "Enable ET WEB_SERVER directory scan and SQLi probe signatures; tune to exclude "
        "known-safe scanner IPs and internal penetration testing ranges.",
        "Medium: automated vulnerability scanners and web crawlers frequently trigger "
        "directory scan rules.",
    ),
}


@dataclass(frozen=True)
class ActionExplanation:
    action_id: str
    suricata_category: str
    description: str
    evasion_count: int
    total_count: int
    evasion_rate: float
    remediation: str
    false_positive_risk: str


def explain_evasions(
    records: list[EpisodeRecord],
    registry: ActionRegistry,
) -> list[ActionExplanation]:
    counts: dict[str, list[int]] = {}
    for record in records:
        for step in record.steps:
            if step.action_id not in counts:
                counts[step.action_id] = [0, 0]
            counts[step.action_id][1] += 1
            if not step.detected:
                counts[step.action_id][0] += 1

    result: list[ActionExplanation] = []
    for action_id, (evaded, total) in counts.items():
        if evaded == 0:
            continue
        defn = registry.get_action(action_id)
        remediation, fpr = REMEDIATION_TABLE.get(defn.suricata_category, _FALLBACK)
        result.append(
            ActionExplanation(
                action_id=action_id,
                suricata_category=defn.suricata_category,
                description=defn.description,
                evasion_count=evaded,
                total_count=total,
                evasion_rate=evaded / total,
                remediation=remediation,
                false_positive_risk=fpr,
            )
        )

    return sorted(result, key=lambda x: (-x.evasion_rate, x.action_id))
