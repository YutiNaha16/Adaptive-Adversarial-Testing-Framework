from __future__ import annotations

import json

import numpy as np

from aatf.linucb import LinUCBModel


def test_c001_update_a_inv_analytic() -> None:
    model = LinUCBModel(d=1, alpha=1.0)
    ctx = np.array([1.0])
    model.update("a", ctx, reward=1.0)
    A_inv, _ = model._arms["a"]
    assert abs(A_inv[0, 0] - 0.5) < 1e-9


def test_c002_update_b_analytic() -> None:
    model = LinUCBModel(d=1, alpha=1.0)
    ctx = np.array([1.0])
    model.update("a", ctx, reward=2.0)
    _, b = model._arms["a"]
    assert abs(b[0] - 2.0) < 1e-9


def test_c003_update_lazy_init() -> None:
    model = LinUCBModel(d=2, alpha=1.0)
    assert "new_action" not in model._arms
    model.update("new_action", np.array([1.0, 0.0]), reward=0.0)
    assert "new_action" in model._arms
    _, b = model._arms["new_action"]
    assert np.allclose(b, np.zeros(2))


def test_c004_update_two_steps() -> None:
    model = LinUCBModel(d=2, alpha=1.0)
    model.update("a", np.array([1.0, 0.0]), reward=1.0)
    model.update("a", np.array([0.0, 1.0]), reward=0.5)
    A_inv, b = model._arms["a"]
    # Step 1: A_inv=[[0.5,0],[0,1]], b=[1,0]
    # Step 2: x=[0,1]; A_inv-=outer([0,1],[0,1])/2 → [[0.5,0],[0,0.5]], b=[1,0.5]
    assert np.allclose(A_inv, np.array([[0.5, 0.0], [0.0, 0.5]]), atol=1e-9)
    assert np.allclose(b, np.array([1.0, 0.5]), atol=1e-9)


def test_c005_select_trained_over_untrained() -> None:
    model = LinUCBModel(d=1, alpha=1.0)
    ctx = np.array([1.0])
    for _ in range(5):
        model.update("b_action", ctx, reward=1.0)
    assert model.select_action(["a_action", "b_action"], ctx) == "b_action"


def test_c006_select_alphabetical_tie_break() -> None:
    model = LinUCBModel(d=2, alpha=1.0)
    ctx = np.array([1.0, 1.0])
    winner = model.select_action(["z_action", "a_action", "m_action"], ctx)
    assert winner == "a_action"


def test_c007_select_alpha_zero_pure_greedy() -> None:
    model = LinUCBModel(d=1, alpha=0.0)
    ctx = np.array([1.0])
    model.update("good", ctx, reward=1.0)
    # "good": theta=[[0.5]]@[1]=[0.5], score=0.5+0=0.5
    # "other": theta=[[1]]@[0]=[0], score=0
    assert model.select_action(["good", "other"], ctx) == "good"


def test_c008_to_dict_json_serialisable() -> None:
    model = LinUCBModel(d=2, alpha=1.5)
    model.update("scan", np.array([1.0, 0.0]), reward=0.8)
    d = model.to_dict()
    serialised = json.dumps(d)  # must not raise
    assert '"scan"' in serialised
    assert d["alpha"] == 1.5
    assert d["d"] == 2


def test_c009_round_trip_identical_scores() -> None:
    model = LinUCBModel(d=2, alpha=1.0)
    ctx = np.array([1.0, 0.5])
    model.update("tcp_port_scan", ctx, reward=1.0)
    model.update("udp_sweep", ctx, reward=-1.0)
    restored = LinUCBModel.from_dict(model.to_dict())
    available = ["tcp_port_scan", "udp_sweep"]
    assert model.select_action(available, ctx) == restored.select_action(available, ctx)


def test_c010_round_trip_fresh_model() -> None:
    original = LinUCBModel(d=2, alpha=1.0)
    restored = LinUCBModel.from_dict(original.to_dict())
    ctx = np.array([1.0, 0.0])
    assert original.select_action(["a", "b"], ctx) == "a"
    assert restored.select_action(["a", "b"], ctx) == "a"
