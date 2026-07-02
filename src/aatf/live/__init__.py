"""Live experiment loop layer.

Home for the attacker brain, action executor, and feedback collector (added by later features).

Architectural boundary (constitution Principle III — Pluggable Defence Interface): code in this
package MUST NOT import any concrete defence implementation. It depends only on shared
contracts/interfaces, so the defence can be swapped (Suricata, ML NIDS, ...) without changing this
layer. ``tests/test_layout.py`` enforces this invariant.
"""
