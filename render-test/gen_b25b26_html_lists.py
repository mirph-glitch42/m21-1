#!/usr/bin/env python3
"""Render test: B25/B26 list-in-cell, driven by **real** ``<ul>``/``<ol>`` HTML.

This generator feeds actual ``<ul>``/``<ol>`` markup through the **production**
:func:`m21_crawl.mdconv._render_list_inline` to capture the *current* output,
and runs the *proposed* fix (emit the list as real HTML) on the same markup.
The BEFORE column is therefore the real current behaviour — the symptoms are
reproduced, not asserted.

Preferred method (user): embed the list as HTML ``<ul>``/``<ol>``/``<li>`` in
the cell. It renders as a real list on every renderer (VMD, GitHub, ...),
preserves the list organization (no text/organization change), and needs no
``<br>``/``&nbsp;`` shims.

Cases: flat ``<ul>``, flat ``<ol>``, nested ``<ul>``, nested ``<ol>``, and a
mixed ``<ul>`` with a nested ``<ol>``.

Self-verifies that the current code shows the symptoms (B26 ``"; "``-flattening
and lost ``<ol>`` numbering; B25 duplication of nested children) and that the
proposed HTML output preserves each item exactly once with correct nesting.

Usage:  python render-test/gen_b25b26_html_lists.py   (run from repo root)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
FIXTURE_NAME = "b25b26-html-lists.md"


class StructuralError(Exception):
    """The fixture path escapes the render-test tree; the write cannot proceed."""


def _resolve_inside(base: str, rel: str) -> str:
    """Resolve *rel* against *base* and prove the result stays inside *base*
    (``commonpath``, not a string prefix; symlink/``..`` escapes blocked)."""
    root = os.path.realpath(base)
    target = os.path.realpath(os.path.join(root, rel))
    if os.path.commonpath([root, target]) != root:
        raise StructuralError(f"refusing to write outside render-test/: {rel!r}")
    return target


def _write_fixture(base: str, rel: str, text: str) -> None:
    target = _resolve_inside(base, rel)
    try:
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(text)
    except OSError as exc:
        raise StructuralError(f"cannot write {target}: {exc}") from exc


# Make the src-layout package importable without an editable install (mirrors
# pyproject ``pythonpath = ["src"]`` used by pytest).
sys.path.insert(0, os.path.realpath(str(SRC)))

from bs4 import BeautifulSoup, Tag  # noqa: E402

from m21_crawl.mdconv import (  # noqa: E402
    _render_inline_piece,
    _render_list_inline,
)

BASE_URL = "https://www.knowva.ebenefits.va.gov/m21/"
NS = ""  # text-only lists: the anchor namespace is unused
_LIST = ("ul", "ol")


def _parse(html: str) -> Tag:
    node = BeautifulSoup(html, "html.parser").find(["ul", "ol"])
    assert node is not None, f"no list found in: {html!r}"
    return node


def current(html: str) -> str:
    """The production ``_render_list_inline`` (current, buggy) output."""
    return _render_list_inline(_parse(html), BASE_URL, NS, "inline")


def proposed_html(el: Tag, base_url: str, ns: str, anchor_mode: str = "inline") -> str:
    """Proposed inline list: emit real HTML ``<ul>``/``<ol>``/``<li>``,
    preserving nesting.

    Iterate *direct* ``<li>`` only (each item once — no B25 duplication).
    Each ``<li>`` keeps its inline content (rendered as Markdown via
    ``_render_inline_piece``) followed by any nested list (recursed). No
    flattening (no B26), no ``<br>``/``&nbsp;`` shims — the renderer draws a
    real list inside the cell.
    """
    tag = el.name or "ul"
    parts: list[str] = ["<" + tag + ">"]
    for li in [c for c in el.children if isinstance(c, Tag) and (c.name or "") == "li"]:
        seq: list[str] = []
        for c in li.children:
            if isinstance(c, Tag) and (c.name or "") in _LIST:
                seq.append(proposed_html(c, base_url, ns, anchor_mode))
            else:
                seq.append(_render_inline_piece(c, base_url, ns, anchor_mode))
        content = "".join(seq).strip()
        if content:
            parts.append("<li>" + content + "</li>")
    parts.append("</" + tag + ">")
    return "".join(parts)


def proposed_str(html: str) -> str:
    return proposed_html(_parse(html), BASE_URL, NS, "inline")


# --- test data (real <ul>/<ol> markup) ---------------------------------------

C1_HTML = (
    "<ul><li>cord</li><li>string</li><li>twine</li>"
    "<li>masking tape, or</li><li>cellophane tape</li></ul>"
)
C1_AFTER = C1_HTML

C2_HTML = (
    "<ol><li>Open the template</li>"
    "<li>Select the representative</li><li>Verify the address</li></ol>"
)
C2_AFTER = C2_HTML

C3_HTML = (
    "<ul><li>such as"
    "<ul><li>eating</li><li>dressing</li><li>grooming, and</li>"
    "<li>carrying out personal hygiene</li></ul></li></ul>"
)
C3_AFTER = C3_HTML

C4_HTML = "<ol><li>first step<ol><li>sub a</li><li>sub b</li></ol></li></ol>"
C4_AFTER = C4_HTML

C5_HTML = (
    "<ul><li>self-care, such as<ol><li>eating</li><li>dressing</li><li>grooming</li></ol></li></ul>"
)
C5_AFTER = C5_HTML

CASES: list[tuple[str, str, str]] = [
    ("Case 1 — flat `<ul>`", C1_HTML, C1_AFTER),
    ("Case 2 — flat `<ol>` (numbering)", C2_HTML, C2_AFTER),
    ("Case 3 — nested `<ul>`", C3_HTML, C3_AFTER),
    ("Case 4 — nested `<ol>` (numbering)", C4_HTML, C4_AFTER),
    ("Case 5 — mixed `<ul>` with a nested `<ol>`", C5_HTML, C5_AFTER),
]


# --- self-verification -------------------------------------------------------


def verify() -> None:
    for title, html, after in CASES:
        b, a = current(html), proposed_str(html)
        assert "; " in b, f"{title}: BEFORE should be '; '-flattened: {b!r}"
        assert a == after, f"{title}: AFTER html mismatch\n got: {a!r}\n exp: {after!r}"
        assert "; " not in a, f"{title}: AFTER still flattened: {a!r}"

    # B25 (duplication): the current code emits nested children twice.
    assert current(C3_HTML).count("eating") == 2, f"C3 BEFORE duplicates: {current(C3_HTML)!r}"
    assert current(C4_HTML).count("sub a") == 2, f"C4 BEFORE duplicates: {current(C4_HTML)!r}"
    assert current(C5_HTML).count("eating") == 2, f"C5 BEFORE duplicates: {current(C5_HTML)!r}"

    # B26 (flattening / lost numbering): current code drops <ol> numbering.
    assert "1. " not in current(C2_HTML), f"C2 BEFORE should lose numbering: {current(C2_HTML)!r}"
    assert "<ol>" in proposed_str(C2_HTML), "C2 AFTER should keep <ol>"

    # AFTER: no duplication — each item's <li> appears exactly as in the input.
    assert proposed_str(C3_HTML).count("<li>") == 5, "C3 AFTER: 1 parent + 4 children"
    assert proposed_str(C4_HTML).count("<li>") == 3, "C4 AFTER: 1 parent + 2 children"
    assert proposed_str(C5_HTML).count("<li>") == 4, "C5 AFTER: 1 parent + 3 children"


# --- fixture -----------------------------------------------------------------


def _cell(s: str) -> str:
    """Escape pipes so the rendered output can live inside a GFM cell."""
    return s.replace("|", "\\|")


def block(title: str, html: str, after: str) -> str:
    b = _cell(current(html))
    a = _cell(after)
    return (
        f"## {title}\n"
        "\n"
        "Input (HTML):\n"
        "\n"
        f"```html\n{html}\n```\n"
        "\n"
        "| Variant | Rendered in a GFM table cell |\n"
        "| --- | --- |\n"
        f"| **BEFORE** — current `_render_list_inline` | {b} |\n"
        f"| **AFTER** — proposed (embedded HTML list) | {a} |\n"
    )


def build_fixture() -> str:
    parts: list[str] = [
        "# B25/B26 render test — lists in a cell, driven by real `<ul>`/`<ol>` HTML",
        "",
        "This test feeds actual list markup through the production",
        "``_render_list_inline`` (BEFORE) and the proposed fix (AFTER). The BEFORE",
        "column is the **real current output** — the symptoms are reproduced, not",
        "asserted.",
        "",
        "Symptoms under test: **B26** (a flat list is flattened to `; `-joined text;",
        "`<ol>` numbering is lost) and **B25** (nested-list children are emitted",
        "twice).",
        "",
        "**Preferred method (user):** embed the list as HTML `<ul>`/`<ol>`/`<li>` in",
        "the cell. It renders as a real list on every renderer (VMD, GitHub, ...),",
        "preserves the list organization (no text/organization change), and needs no",
        "`<br>`/`&nbsp;` shims. The AFTER cell below shows the list exactly as it",
        "will render in the manual.",
        "",
    ]
    for title, html, after in CASES:
        parts.append(block(title, html, after))
        parts.append("")
    parts.extend(
        [
            "---",
            "",
            "**Implementation:** `_render_list_inline` is rewritten to emit real HTML",
            "`<ul>`/`<ol>`/`<li>` (iterate *direct* `<li>` only; keep each `<li>`'s",
            "inline content; recurse into nested lists). That single change removes",
            "B25 (duplication) and B26 (flattening / lost numbering) while preserving",
            "the list's organization — matching the standing no-text / no-organization",
            "change goal.",
            "",
        ]
    )
    return "\n".join(parts) + "\n"


def main() -> int:
    verify()
    base = os.path.realpath(str(REPO_ROOT / "render-test"))
    try:
        _write_fixture(base, FIXTURE_NAME, build_fixture())
    except StructuralError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"fixture written: {REPO_ROOT / 'render-test' / FIXTURE_NAME}")
    print(
        "self-verification passed: current code shows B25/B26; proposed HTML output "
        "preserves each list item once with correct nesting (flat, nested, mixed)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
