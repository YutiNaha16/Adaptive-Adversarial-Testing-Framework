import random
import unittest.mock
from pathlib import Path

import numpy as np

from aatf.seeding import seed_everything


def test_seed_produces_deterministic_random():
    seed_everything(42)
    v1 = random.random()
    seed_everything(42)
    v2 = random.random()
    assert v1 == v2


def test_seed_produces_deterministic_numpy():
    seed_everything(42)
    v1 = np.random.random()
    seed_everything(42)
    v2 = np.random.random()
    assert v1 == v2


def test_different_seeds_differ():
    seed_everything(42)
    v42 = random.random()
    seed_everything(99)
    v99 = random.random()
    assert v42 != v99


def test_reseed_resets_state():
    seed_everything(42)
    first = random.random()
    _ = random.random()
    seed_everything(42)
    reset = random.random()
    assert first == reset


def test_torch_absent_no_error():
    real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

    def mock_import(name, *args, **kwargs):
        if name == "torch":
            raise ImportError("torch not installed")
        return real_import(name, *args, **kwargs)

    with unittest.mock.patch("builtins.__import__", side_effect=mock_import):
        seed_everything(42)


def test_no_direct_seeding_calls():
    src_root = Path("src/aatf")
    forbidden = [
        "random.seed(",
        "numpy.random.seed(",
        "np.random.seed(",
        "torch.manual_seed(",
    ]
    violations = []
    for py_file in src_root.rglob("*.py"):
        if py_file.name == "seeding.py":
            continue
        text = py_file.read_text()
        for pattern in forbidden:
            if pattern in text:
                violations.append(f"{py_file}: contains '{pattern}'")
    assert violations == [], "Direct seeding calls found outside seeding.py:\n" + "\n".join(
        violations
    )
