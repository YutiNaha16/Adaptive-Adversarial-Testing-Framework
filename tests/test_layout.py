"""Layout & architectural-boundary tests (FR-001, FR-002, constitution Principle III)."""

import importlib
import sys


def test_layers_import():
    """Both architectural layers import cleanly as skeletons (FR-001)."""
    assert importlib.import_module("aatf.live") is not None
    assert importlib.import_module("aatf.analysis") is not None


def test_live_layer_imports_no_concrete_defence():
    """Importing the live-loop layer must pull in no concrete defence module (Principle III).

    The live layer may depend only on shared contracts/interfaces — never on a specific
    detector (Suricata, ML NIDS, ...). With empty skeletons this passes trivially and stands
    as a regression guard for every later feature.
    """
    # Drop any cached live-layer modules so the import is observed fresh.
    for name in [m for m in list(sys.modules) if m.startswith("aatf.live")]:
        del sys.modules[name]

    importlib.import_module("aatf.live")

    offenders = [
        name
        for name in sys.modules
        if name.startswith("aatf.")
        and ("defence" in name.lower() or "defense" in name.lower() or "suricata" in name.lower())
    ]
    assert offenders == [], f"live layer imported concrete defence module(s): {offenders}"
