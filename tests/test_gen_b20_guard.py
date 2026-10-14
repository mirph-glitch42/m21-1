"""gen_b20: write-sink containment for the fixture path (TDD, SonarCloud S2083).

The guard must accept the repo-derived ``FIXTURE`` path and refuse any
path that resolves outside ``render-test/`` (``..`` or absolute).
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "render-test" / "gen_b20_nested_table.py"


def _load():
    spec = importlib.util.spec_from_file_location("gen_b20_nested_table", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


gb = _load()


def test_resolve_fixture_accepts_fixture() -> None:
    got = gb._resolve_fixture(gb.FIXTURE)
    assert os.path.realpath(got) == os.path.realpath(REPO / "render-test" / "b20-nested-table.md")


def test_resolve_fixture_rejects_dotdot_escape() -> None:
    with pytest.raises(ValueError, match="refusing to write outside render-test"):
        gb._resolve_fixture(REPO / "render-test" / ".." / "evil.md")


def test_resolve_fixture_rejects_absolute_outside(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="refusing to write outside render-test"):
        gb._resolve_fixture(tmp_path / "evil.md")
