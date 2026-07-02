"""Offline analysis pipeline layer.

Home for the evaluator, explainability engine, and report generator (added by later features).
This layer operates only on logged artifacts produced by the live loop — it never re-runs the
experiment or depends on defence internals.
"""
