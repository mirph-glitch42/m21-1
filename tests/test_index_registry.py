"""check_index_registry: ``algorithms/INDEX.md`` staleness gate (TDD).

Fixtures are synthetic per the gate's contract; the script under test is
loaded from ``scripts/check_index_registry.py`` and exercised against a
temporary ``algorithms/`` tree — the in-sync case, every drift case, the
structural cases, and the subprocess exit codes (0 / 1 / 2).
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_index_registry.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_index_registry", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclass() looks the module up in sys.modules
    spec.loader.exec_module(mod)
    return mod


cix = _load()


def _doc(slug: str, title: str, version: str, status: str) -> str:
    """A minimal algorithm doc with the real METADATA table shape."""
    return (
        f"# {title}\n\n"
        "<!-- SECTION:METADATA -->\n"
        "## 1. Metadata\n\n"
        "| Field | Value |\n"
        "|---|---|\n"
        f"| Name | {title} |\n"
        f"| Slug | {slug} |\n"
        f"| Version | {version} |\n"
        f"| Status | {status} |\n"
        "| Status history | 0.1.0 (2026-01-01): initial |\n"
        "\n<!-- SECTION:THEORY -->\n"
        "## 2. Theory\n\nBody.\n"
    )


def _row(slug: str, name: str, version: str, status: str, target: str) -> str:
    return f"| {slug} | {name} | {version} | {status} | [{target}]({target}) | summary |"


def _index(*rows: str) -> str:
    body = "\n".join(rows)
    return (
        "# Algorithm Registry\n\n"
        "| Slug | Name | Version | Status | File | One-line summary |\n"
        "|---|---|---|---|---|---|\n"
        f"{body}\n"
        "\n## Rules\n\n1. rule\n"
    )


def _tree(tmp_path: Path, docs: dict[str, str], rows: list[str]) -> str:
    alg = tmp_path / "algorithms"
    alg.mkdir()
    for slug, content in docs.items():
        (alg / f"{slug}.md").write_text(content, encoding="utf-8")
    (alg / "INDEX.md").write_text(_index(*rows), encoding="utf-8")
    return str(alg)


def _run(alg: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--dir", alg],
        capture_output=True,
        text=True,
        check=False,
    )


# --- in sync -----------------------------------------------------------------


def test_in_sync_passes(tmp_path) -> None:
    alg = _tree(
        tmp_path,
        {"alpha": _doc("alpha", "Alpha", "1.0.0", "implemented")},
        [_row("alpha", "Alpha", "1.0.0", "implemented", "alpha.md")],
    )
    assert cix.validate(alg) == []


# --- drift (exit 1) ----------------------------------------------------------


def test_version_mismatch(tmp_path) -> None:
    alg = _tree(
        tmp_path,
        {"alpha": _doc("alpha", "Alpha", "1.0.0", "implemented")},
        [_row("alpha", "Alpha", "0.9.0", "implemented", "alpha.md")],
    )
    errs = cix.validate(alg)
    assert any("Version" in e and "0.9.0" in e and "1.0.0" in e for e in errs)


def test_status_mismatch(tmp_path) -> None:
    alg = _tree(
        tmp_path,
        {"alpha": _doc("alpha", "Alpha", "1.0.0", "implemented")},
        [_row("alpha", "Alpha", "1.0.0", "draft", "alpha.md")],
    )
    errs = cix.validate(alg)
    assert any("Status" in e and "draft" in e and "implemented" in e for e in errs)


def test_missing_row(tmp_path) -> None:
    alg = _tree(
        tmp_path,
        {
            "alpha": _doc("alpha", "Alpha", "1.0.0", "implemented"),
            "beta": _doc("beta", "Beta", "1.0.0", "implemented"),
        },
        [_row("beta", "Beta", "1.0.0", "implemented", "beta.md")],
    )
    errs = cix.validate(alg)
    assert any("alpha.md" in e and "no registry row" in e for e in errs)


def test_duplicate_rows(tmp_path) -> None:
    alg = _tree(
        tmp_path,
        {"alpha": _doc("alpha", "Alpha", "1.0.0", "implemented")},
        [
            _row("alpha", "Alpha", "1.0.0", "implemented", "alpha.md"),
            _row("alpha", "Alpha again", "1.0.0", "implemented", "alpha.md"),
        ],
    )
    errs = cix.validate(alg)
    assert any("2 registry rows" in e for e in errs)


def test_orphan_row(tmp_path) -> None:
    alg = _tree(tmp_path, {}, [_row("ghost", "Ghost", "1.0.0", "implemented", "ghost.md")])
    errs = cix.validate(alg)
    assert any("orphan row" in e and "ghost" in e for e in errs)


def test_file_target_missing(tmp_path) -> None:
    alg = _tree(
        tmp_path,
        {"alpha": _doc("alpha", "Alpha", "1.0.0", "implemented")},
        [_row("alpha", "Alpha", "1.0.0", "implemented", "nonexistent.md")],
    )
    errs = cix.validate(alg)
    assert any("does not exist" in e for e in errs)


# --- structural (exit 2) -----------------------------------------------------


def test_no_table_is_structural(tmp_path) -> None:
    alg = tmp_path / "algorithms"
    alg.mkdir()
    (alg / "INDEX.md").write_text("# Registry\n\nNo table here.\n", encoding="utf-8")
    with pytest.raises(cix.StructuralError):
        cix.validate(str(alg))


def test_bad_cell_count_is_structural(tmp_path) -> None:
    alg = tmp_path / "algorithms"
    alg.mkdir()
    (alg / "INDEX.md").write_text(
        "# Registry\n\n"
        "| Slug | Name | Version | Status | File | One-line summary |\n"
        "|---|---|---|---|---|---|\n"
        "| only | four | cells | here |\n",
        encoding="utf-8",
    )
    with pytest.raises(cix.StructuralError):
        cix.validate(str(alg))


def test_status_history_not_confused_with_status(tmp_path) -> None:
    text = _doc("alpha", "Alpha", "1.0.0", "implemented")
    meta = cix.parse_metadata(text.split("\n"))
    assert meta.status == "implemented"
    assert meta.version == "1.0.0"


# --- subprocess exit codes ---------------------------------------------------


def test_subprocess_in_sync_exit0(tmp_path) -> None:
    alg = _tree(
        tmp_path,
        {"alpha": _doc("alpha", "Alpha", "1.0.0", "implemented")},
        [_row("alpha", "Alpha", "1.0.0", "implemented", "alpha.md")],
    )
    res = _run(alg)
    assert res.returncode == 0, res.stderr


def test_subprocess_drift_exit1(tmp_path) -> None:
    alg = _tree(
        tmp_path,
        {"alpha": _doc("alpha", "Alpha", "1.0.0", "implemented")},
        [_row("alpha", "Alpha", "9.9.9", "implemented", "alpha.md")],
    )
    res = _run(alg)
    assert res.returncode == 1, res.stdout + res.stderr


def test_subprocess_structural_exit2(tmp_path) -> None:
    alg = tmp_path / "algorithms"
    alg.mkdir()
    (alg / "INDEX.md").write_text("No table.\n", encoding="utf-8")
    res = _run(alg)
    assert res.returncode == 2, res.stdout + res.stderr
