from __future__ import annotations

import numpy as np
import pytest

from aatf.attacker import Attacker, FixedScriptAttacker, LinUCBAttacker, RandomAttacker
from aatf.linucb import LinUCBModel


def test_c001_all_classes_are_attacker_instances() -> None:
    model = LinUCBModel(d=1)
    assert isinstance(RandomAttacker(), Attacker)
    assert isinstance(FixedScriptAttacker(), Attacker)
    assert isinstance(LinUCBAttacker(model), Attacker)


def test_c002_choose_action_returns_from_available() -> None:
    available = ["tcp_port_scan", "icmp_ping_sweep", "dns_subdomain_enum"]
    ctx = np.zeros(1)
    model = LinUCBModel(d=1)
    for attacker in [RandomAttacker(), FixedScriptAttacker(), LinUCBAttacker(model)]:
        result = attacker.choose_action(available, ctx)
        assert result in available


def test_c003_observe_no_error_all_implementations() -> None:
    ctx = np.array([1.0])
    model = LinUCBModel(d=1)
    for attacker in [RandomAttacker(), FixedScriptAttacker(), LinUCBAttacker(model)]:
        attacker.observe("tcp_port_scan", ctx, reward=1.0)


def test_c004_random_attacker_seeded_determinism() -> None:
    available = ["a", "b", "c"]
    ctx = np.zeros(1)
    rng1 = RandomAttacker(seed=42)
    seq1 = [rng1.choose_action(available, ctx) for _ in range(5)]
    rng2 = RandomAttacker(seed=42)
    seq2 = [rng2.choose_action(available, ctx) for _ in range(5)]
    assert seq1 == seq2


def test_c005_random_attacker_single_element() -> None:
    attacker = RandomAttacker(seed=0)
    for _ in range(10):
        assert attacker.choose_action(["only_action"], np.zeros(1)) == "only_action"


def test_c006_random_attacker_empty_available_raises() -> None:
    attacker = RandomAttacker()
    with pytest.raises(ValueError):
        attacker.choose_action([], np.zeros(1))


def test_c007_random_attacker_observe_noop() -> None:
    r1 = RandomAttacker(seed=7)
    r2 = RandomAttacker(seed=7)
    available = ["x", "y", "z"]
    ctx = np.zeros(1)
    r1.choose_action(available, ctx)  # r1: pos 1
    r1.observe("x", ctx, reward=-1.0)  # must not advance RNG
    r1.choose_action(available, ctx)  # r1: pos 2
    r2.choose_action(available, ctx)  # r2: pos 1
    r2.choose_action(available, ctx)  # r2: pos 2 — align with r1
    # 3rd call on both must be equal (observe did not advance r1's RNG)
    assert r1.choose_action(available, ctx) == r2.choose_action(available, ctx)


def test_c008_fixed_script_attacker_explicit_cycle() -> None:
    attacker = FixedScriptAttacker(script=["x", "y"])
    ctx = np.zeros(1)
    results = [attacker.choose_action(["x", "y"], ctx) for _ in range(4)]
    assert results == ["x", "y", "x", "y"]


def test_c009_fixed_script_attacker_default_alphabetical() -> None:
    attacker = FixedScriptAttacker()
    ctx = np.zeros(1)
    first = attacker.choose_action(["c_action", "a_action", "b_action"], ctx)
    assert first == "a_action"
    assert attacker.choose_action(["c_action", "a_action", "b_action"], ctx) == "b_action"
    assert attacker.choose_action(["c_action", "a_action", "b_action"], ctx) == "c_action"
    assert attacker.choose_action(["c_action", "a_action", "b_action"], ctx) == "a_action"


def test_c010_fixed_script_attacker_single_element() -> None:
    attacker = FixedScriptAttacker(script=["only"])
    ctx = np.zeros(1)
    for _ in range(5):
        assert attacker.choose_action(["only"], ctx) == "only"


def test_c011_linucb_attacker_observe_mutates_model() -> None:
    model = LinUCBModel(d=1, alpha=1.0)
    attacker = LinUCBAttacker(model)
    ctx = np.array([1.0])
    attacker.observe("scan", ctx, reward=1.0)
    assert "scan" in model._arms
    _, b = model._arms["scan"]
    assert abs(b[0] - 1.0) < 1e-9


def test_c012_linucb_attacker_choose_action_matches_model() -> None:
    model = LinUCBModel(d=1, alpha=1.0)
    attacker = LinUCBAttacker(model)
    ctx = np.array([1.0])
    available = ["a_action", "b_action"]
    assert attacker.choose_action(available, ctx) == model.select_action(available, ctx)
