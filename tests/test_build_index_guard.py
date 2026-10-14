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


def test_resolve_doc_accepts_algorithm_doc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(REPO)
    got = bi._resolve_doc("algorithms/html-to-markdown-section-extraction.md")
    assert os.path.realpath(got) == os.path.realpath(
        REPO / "algorithms" / "html-to-markdown-section-extraction.md"
    )


def test_resolve_doc_rejects_dotdot_escape() -> None:
    with pytest.raises(SystemExit) as excinfo:
        bi._resolve_doc("../backlog.md")
    assert excinfo.value.code == 2


def test_resolve_doc_rejects_absolute_outside() -> None:
    with pytest.raises(SystemExit) as excinfo:
        bi._resolve_doc("/etc/hostname")
    assert excinfo.value.code == 2


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
