#!/usr/bin/env python3
"""Compare blind spots across two experiment output dirs.

Usage:
    python3 lab/scripts/compare-blind-spots.py outputs/run_003 outputs/run_transfer

Prints a table of actions that evaded BOTH configs — structural weaknesses
that are ruleset-independent, which is the key transferability claim.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _load_latest_manifest(output_dir: Path) -> dict:
    manifests = sorted(output_dir.glob("run_manifest_*.json"))
    if not manifests:
        raise FileNotFoundError(f"No manifest in {output_dir}")
    return json.loads(manifests[-1].read_text())


def _load_report(output_dir: Path) -> str:
    reports = sorted(output_dir.glob("report_*.md"))
    if not reports:
        return ""
    return reports[-1].read_text()


def _extract_blind_spots(report: str) -> set[str]:
    """Extract action IDs from the Blind Spots table in a report."""
    blind_spots: set[str] = set()
    in_table = False
    for line in report.splitlines():
        if "| Action ID" in line and "Detection Rate" in line:
            in_table = True
            continue
        if in_table:
            if not line.startswith("|") or line.startswith("|-"):
                in_table = False
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if parts:
                blind_spots.add(parts[0])
    return blind_spots


def main(dir_a: str, dir_b: str) -> None:
    path_a = Path(dir_a)
    path_b = Path(dir_b)

    manifest_a = _load_latest_manifest(path_a)
    manifest_b = _load_latest_manifest(path_b)

    report_a = _load_report(path_a)
    report_b = _load_report(path_b)

    blind_a = _extract_blind_spots(report_a)
    blind_b = _extract_blind_spots(report_b)

    overlap = blind_a & blind_b
    only_a = blind_a - blind_b
    only_b = blind_b - blind_a

    cfg_a = manifest_a.get("config_snapshot", {})
    cfg_b = manifest_b.get("config_snapshot", {})

    print("=" * 60)
    print("AATF Transferability Report")
    print("=" * 60)
    atk_a = cfg_a.get("attacker_class", "?")
    atk_b = cfg_b.get("attacker_class", "?")
    print(f"Config A : {path_a} ({atk_a}, {cfg_a.get('episodes', '?')} ep)")
    print(f"Config B : {path_b} ({atk_b}, {cfg_b.get('episodes', '?')} ep)")
    print()
    print(f"Blind spots in A only : {sorted(only_a) or 'none'}")
    print(f"Blind spots in B only : {sorted(only_b) or 'none'}")
    print()
    print(f"STRUCTURAL BLIND SPOTS (both configs) [{len(overlap)}]:")
    if overlap:
        for action in sorted(overlap):
            print(f"  - {action}")
        print()
        print("These actions evade detection regardless of which SIDs are disabled.")
        print("Conclusion: structural weaknesses in ET Open ruleset coverage.")
    else:
        print("  None — all blind spots are config-specific.")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <dir_a> <dir_b>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
