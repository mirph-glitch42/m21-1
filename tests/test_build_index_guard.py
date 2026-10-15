"""build_index: path-containment guard for the LLM-supplied ``doc`` arg (TDD).

The script under test is loaded from ``scripts/build_index.py``; the guard
must accept a document inside ``algorithms/`` and refuse anything that
resolves outside it (``..`` or absolute) — exit 2, nothing touched.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "build_index.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_index", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


bi = _load()


def test_resolve_inside_accepts_algorithm_doc() -> None:
    base = str(REPO / "algorithms")
    got = bi._resolve_inside(base, "html-to-markdown-section-extraction.md")
    assert os.path.realpath(got) == os.path.realpath(
        REPO / "algorithms" / "html-to-markdown-section-extraction.md"
    )


def test_read_doc_refuses_escape(tmp_path: Path) -> None:
    """The read sink itself rejects escapes, even when the target file exists."""
    (tmp_path / "outside.md").write_text("secret", encoding="utf-8")
    with pytest.raises(bi.StructuralError, match="outside the algorithms dir"):
        bi._read_doc(str(tmp_path), "../outside.md")


def test_write_doc_refuses_escape(tmp_path: Path) -> None:
    """The write sink itself rejects escapes, even when the target exists."""
    (tmp_path / "outside.md").write_text("do not touch", encoding="utf-8")
    with pytest.raises(bi.StructuralError, match="outside the algorithms dir"):
        bi._write_doc(str(tmp_path), "../outside.md", "evil")
    assert (tmp_path / "outside.md").read_text(encoding="utf-8") == "do not touch"


def test_cli_refuses_escape_before_any_io(tmp_path: Path) -> None:
    outside = tmp_path / "escape.md"
    outside.write_text("do not touch", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(outside), "--check"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "refusing path outside the algorithms dir" in proc.stderr
    assert outside.read_text(encoding="utf-8") == "do not touch"
