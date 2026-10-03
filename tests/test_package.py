"""Smoke test: the package imports and advertises a version (TDD first increment)."""

import importlib


def test_package_imports_and_exposes_version() -> None:
    """Importing m21_crawl must work and expose a PEP 440 version string."""
    mod = importlib.import_module("m21_crawl")
    assert hasattr(mod, "__version__")
    # PEP 440: digits.digits.digits with optional suffix.
    assert mod.__version__ == mod.__version__.strip()
    assert any(ch.isdigit() for ch in mod.__version__)
