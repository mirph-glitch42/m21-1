#!/usr/bin/env python3
"""Regenerate the B20 render-test sample (section B of b20-nested-table.md).

Sample under review: a nested Step/Action table (source article
`554400000181476`, section `I.i.2.B.1.g`) rendered as a box-drawing
monospace table inside a ``<pre>`` block, embedded in the outer If/Then
GFM table cell.

Approved rules (user sign-off targets):
- Cell TEXT is verbatim: same words, same order, same emphasis/links.
  Only whitespace between words is normalized to single spaces.
- Wrap width W = 48 *rendered* characters. "Rendered" = markdown inline
  syntax stripped the way the renderer displays it: images -> alt text,
  links -> link text, code spans -> inner text, emphasis markers (*, _)
  dropped entirely (so ``***Note***`` counts 4, not 10).
- Greedy wrap: a unit joins the current line iff ``cur + 1 + w <= W``.
- Atomic units (image, link, code span, emphasis run) never split.
- Every border aligns when the renderer strips markdown: each line's
  rendered width is exactly 59 (1 pipe + 6 + 1 pipe + 50 + 1 pipe), where
  the 50-wide action cell = 1 leading space + up to W=48 text + >=1 pad.

Usage:  python render-test/gen_b20_nested_table.py   (run from repo root)

The script self-verifies (border alignment, no orphaned words that fit,
verbatim text) before writing the file.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "render-test" / "b20-nested-table.md"

W = 48  # Max action-cell text width, in rendered characters.
STEP_W = 6  # Step cell width, rendered (1 leading space + <=5 text).
ACT_CELL = W + 2  # Action cell width, rendered (1 lead + <=W text + >=1 trail).
LINE_W = 1 + STEP_W + 1 + ACT_CELL + 1  # rendered width of every line: 59.

# Verbatim cell content from the source article (one continuous string in
# the source HTML; no line breaks). The 3-space gap before ***Note*** is a
# source artifact; it normalizes to a single space in the wrapped output.
LINK = "[OGC accreditation list](https://www.va.gov/ogc/apps/accreditation/)"
ROWS: list[tuple[str, str]] = [
    ("1", "Navigate to the POWER OF ATTORNEY box within the letter template."),
    ("2", "Delete the existing representative listed, if applicable."),
    ("3", "Add the new representation information using the ADD button."),
    (
        "4",
        "Begin typing the name of the representative in the SEARCH POA\u2019S field. "
        "A list will appear. Choose the correct representative if listed. "
        "The address will automatically populate.   ***Note***: If the name is not "
        "listed, manually enter the information required. Ensure the address is "
        "current by checking against the " + LINK + ".",
    ),
    ("5", "Save the information using the SAVE POA button."),
    (
        "6",
        "Prior to finalizing the letter, preview it to ensure that the "
        "information populated correctly.",
    ),
]
HEADER_STEP = "**Step**"
HEADER_ACTION = "**Action**"
INTRO = "refer to the steps in the table below. "


def rendered_width(s: str) -> int:
    """Rendered display width: markdown inline syntax stripped, as displayed."""
    s = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", s)  # image -> alt
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)  # link -> text
    s = re.sub(r"`([^`]*)`", r"\1", s)  # code -> inner
    s = s.replace("*", "").replace("_", "")  # emphasis markers drop
    return len(s)


# Atomic inline units, longest/most-specific first. Emphasis = 1-3 paired
# markers around a run that starts with a non-space, non-marker char.
TOKEN_RE = re.compile(
    r"!\[[^\]]*\]\([^)]*\)"  # image
    r"|\[[^\]]*\]\([^)]*\)"  # link
    r"|`[^`\n]*`"  # code span
    r"|[*_]{1,3}[^\s*_][^*_]*[*_]{1,3}"  # emphasis run
)


def tokenize(md: str) -> list[tuple[str, bool]]:
    """Split markdown into (unit, sep) pairs: links/images/code/emphasis stay
    whole; plain text splits into words. sep is True iff the source had
    whitespace immediately before the unit (a space belongs between it and the
    previous unit); False means the source attached it directly (e.g.
    ``***Note***:`` or ``[link].``) and no space may be inserted."""
    units: list[tuple[str, bool]] = []

    def add_plain(gap: str, first: bool) -> None:
        frags = gap.split()
        leading_ws = bool(gap) and gap[0].isspace()
        for j, frag in enumerate(frags):
            sep = True if j > 0 else (not first) and leading_ws
            units.append((frag, sep))

    pos = 0
    for m in TOKEN_RE.finditer(md):
        add_plain(md[pos : m.start()], first=not units)
        sep = m.start() > pos and md[m.start() - 1].isspace()
        units.append((m.group(0), sep))
        pos = m.end()
    add_plain(md[pos:], first=not units)
    return units


def join_units(units: list[tuple[str, bool]]) -> str:
    """Rejoin units, inserting a space only where the source had one."""
    out = ""
    for i, (text, sep) in enumerate(units):
        if i > 0 and sep:
            out += " "
        out += text
    return out


def wrap(md: str, width: int) -> list[str]:
    """Greedy wrap at `width` rendered characters; atomic units never split;
    source adjacency (no space) is preserved across the join."""
    lines: list[str] = []
    cur: list[tuple[str, bool]] = []
    cur_w = 0
    for text, sep in tokenize(md):
        w = rendered_width(text)
        join_w = 1 if (cur and sep) else 0
        if cur and cur_w + join_w + w > width:
            lines.append(join_units(cur))
            cur, cur_w = [(text, False)], w
        elif not cur:
            cur, cur_w = [(text, False)], w
        else:
            cur.append((text, sep))
            cur_w += join_w + w
    if cur:
        lines.append(join_units(cur))
    return lines


def pad(text: str, width: int) -> str:
    """Cell area: leading space + text + rendered-width padding to `width`."""
    return " " + text + " " * (width - 1 - rendered_width(text))


def build_box(rows: list[tuple[str, str]]) -> str:
    """One box; each step-row is its own height, with a single blank spacer row
    between steps (not padded to the tallest row)."""
    wrapped = [(step, wrap(action, W)) for step, action in rows]
    top = "\u250c" + "\u2500" * STEP_W + "\u252c" + "\u2500" * ACT_CELL + "\u2510"
    mid = "\u251c" + "\u2500" * STEP_W + "\u253c" + "\u2500" * ACT_CELL + "\u2524"
    bot = "\u2514" + "\u2500" * STEP_W + "\u2534" + "\u2500" * ACT_CELL + "\u2518"
    out = [
        top,
        "\u2502" + pad(HEADER_STEP, STEP_W) + "\u2502" + pad(HEADER_ACTION, ACT_CELL) + "\u2502",
        mid,
    ]
    for idx, (step, act_lines) in enumerate(wrapped):
        for i, line in enumerate(act_lines):
            left = pad(step, STEP_W) if i == 0 else pad("", STEP_W)
            out.append("\u2502" + left + "\u2502" + pad(line, ACT_CELL) + "\u2502")
        if idx < len(wrapped) - 1:  # single spacer row between steps
            out.append("\u2502" + pad("", STEP_W) + "\u2502" + pad("", ACT_CELL) + "\u2502")
    out.append(bot)
    return "\n".join(out)


def verify(box: str, rows: list[tuple[str, str]]) -> None:
    for line in box.splitlines():
        rw = rendered_width(line)
        assert rw == LINE_W, f"border misalignment: rendered {rw} != {LINE_W}: {line!r}"

    # Verbatim text: word multiset/order preserved (whitespace-normalized).
    def words(s: str) -> list[str]:
        return [re.sub(r"[*_`\[\]()]", "", t).strip() for t, _ in tokenize(s)]

    box_text = re.sub(r"[│┌┬┐├┼┤└┴┘─]+", " ", box)
    got = words(box_text)
    want = words(HEADER_STEP) + words(HEADER_ACTION)
    for step, action in rows:
        want += [step] + words(action)
    assert got == want, f"text drift:\n got={got}\nwant={want}"


def main() -> int:
    box = build_box(ROWS)
    verify(box, ROWS)

    pre = "<pre>" + box.replace("\n", "<br>") + "</pre>"
    if "|" in pre:
        pre = pre.replace("|", "\\|")
    new_row = (
        "| a private attorney or agent is not already selected, or; the user needs to "
        "change the representation for the specific correspondence | " + INTRO + "<br>" + pre + " |"
    )

    old = FIXTURE.read_text(encoding="utf-8")
    lines = old.split("\n")
    target = "## B. AFTER (proposed B20)"
    idx = next(i for i, line in enumerate(lines) if line.startswith(target))
    # Replace the section-B data rows (from the first '| a private' after idx)
    # up to end of file with the same first row + regenerated nested-table row.
    data_start = next(
        i
        for i in range(idx, len(lines))
        if lines[i].startswith("| a private attorney or agent is already selected")
    )
    first_data_row = lines[data_start]
    new_lines = lines[:data_start] + [first_data_row, new_row]
    FIXTURE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    # Console report (rendered widths per row for review)
    print(f"fixture written: {FIXTURE}")
    print(f"pre-block lines: {len(box.splitlines())}, rendered line width: {LINE_W}")
    wrapped = {step: wrap(action, W) for step, action in ROWS}
    for step, act in wrapped.items():
        widths = [rendered_width(line) for line in act]
        print(f"  step {step}: {len(act)} lines, widths={widths}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
