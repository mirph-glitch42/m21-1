"""gen_b20: write-sink containment for the fixture path (TDD, SonarCloud S2083).

The guard must accept the fixture name inside the ``render-test/`` base and
refuse any relative path that resolves outside the tree (``..`` or
absolute) — the read and write sinks raise ``StructuralError``, nothing
touched.
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


def test_resolve_inside_accepts_fixture() -> None:
    base = str(REPO / "render-test")
    got = gb._resolve_inside(base, "b20-nested-table.md")
    assert os.path.realpath(got) == os.path.realpath(REPO / "render-test" / "b20-nested-table.md")


def test_read_fixture_refuses_dotdot_escape(tmp_path: Path) -> None:
    """The read sink itself rejects escapes, even when the target file exists."""
    (tmp_path / "evil.md").write_text("secret", encoding="utf-8")
    with pytest.raises(gb.StructuralError, match="refusing to write outside render-test"):
        gb._read_fixture(str(tmp_path), "../evil.md")
    assert (tmp_path / "evil.md").read_text(encoding="utf-8") == "secret"


def test_write_fixture_refuses_absolute_outside(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(gb.StructuralError, match="refusing to write outside render-test"):
        gb._write_fixture(str(outside), str(tmp_path / "evil.md"), "evil")
    assert not (tmp_path / "evil.md").exists()
