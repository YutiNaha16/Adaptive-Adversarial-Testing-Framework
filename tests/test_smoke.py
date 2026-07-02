"""Smoke test: proves the pytest harness collects and runs on a clean checkout (FR-008)."""

import aatf


def test_harness_runs():
    assert True


def test_package_exposes_version():
    assert isinstance(aatf.__version__, str)
    assert aatf.__version__
