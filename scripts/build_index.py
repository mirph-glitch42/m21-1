#!/usr/bin/env python3
"""Regenerate the machine-parsable line index of an algorithm document.

An algorithm document contains:
  - a block delimited by `<!-- INDEX:BEGIN ... -->` and `<!-- INDEX:END -->`
  - sections, each starting with a line `<!-- SECTION:<ID> -->`
    where <ID> matches [A-Z0-9_]+

A section spans from its marker line to the line before the next
section's marker, or to the last line of the file for the final section.

This script rewrites the interior of the index block as a TSV table:

    id	start_line	end_line
    INDEX_BLOCK	3	12
    METADATA	14	26
    ...

Line numbers are 1-indexed and count every physical line of the file.
The first row always describes the index block itself, so the index is
inclusive of itself.

Usage:
    python3 build_index.py <doc.md>          # rewrite the index in place
    python3 build_index.py <doc.md> --check  # verify only; exit 1 if stale

Vendored (unmodified) from the algorithm-records-keeper skill so CI can
enforce the index contract without depending on a local skill directory.
"""

from __future__ import annotations

import argparse
import re
import sys

BEGIN_RE = re.compile(r"^<!--\s*INDEX:BEGIN\b.*?-->\s*$")
END_RE = re.compile(r"^<!--\s*INDEX:END\s*-->\s*$")
SECTION_RE = re.compile(r"^<!--\s*SECTION:([A-Z0-9_]+)\s*-->\s*$")
TSV_HEADER = "id\tstart_line\tend_line"


def fail(msg: str) -> None:
    print(f"build_index: {msg}", file=sys.stderr)
    sys.exit(2)


def find_index_block(lines: list[str]) -> tuple[int, int]:
    begin = end = None
    for i, line in enumerate(lines):
        if begin is None and BEGIN_RE.match(line):
            begin = i
        elif begin is not None and END_RE.match(line):
            end = i
            break
    if begin is None or end is None:
        fail("missing <!-- INDEX:BEGIN --> / <!-- INDEX:END --> markers")
    if end <= begin + 1:
        fail("index block is empty or malformed (needs interior lines between BEGIN and END)")
    return begin, end


def find_sections(lines: list[str], index_end: int) -> list[tuple[str, int]]:
    sections: list[tuple[str, int]] = []
    seen: set[str] = set()
    for i, line in enumerate(lines):
        m = SECTION_RE.match(line)
        if not m:
            continue
        sid = m.group(1)
        if sid in seen:
            fail(f"duplicate section id: {sid}")
        seen.add(sid)
        if i <= index_end:
            fail(
                "section "
                + sid
                + " starts at or inside the index block; sections must come after INDEX:END"
            )
        sections.append((sid, i + 1))  # 1-indexed start line
    if not sections:
        fail("no <!-- SECTION:<ID> --> markers found")
    return sections


def build_rows(
    sections: list[tuple[str, int]], total_lines: int, begin: int, end: int
) -> list[tuple[str, int, int]]:
    """Rows are expressed in the line numbers of the FILE AFTER REWRITE.

    Rewriting the index interior changes its length, which shifts every
    section that follows. `delta` is that shift; all reported line numbers
    already include it, so the result is idempotent under --check.
    """
    old_interior = end - begin - 1
    n_rows = 1 + len(sections)  # INDEX_BLOCK + one row per section
    new_interior = 1 + n_rows  # TSV header + rows
    delta = new_interior - old_interior

    # 0-indexed: BEGIN at `begin`, interior at begin+1 .. begin+new_interior, END after that.
    rows = [("INDEX_BLOCK", begin + 1, begin + new_interior + 2)]
    for idx, (sid, start) in enumerate(sections):
        nxt = sections[idx + 1][1] - 1 + delta if idx + 1 < len(sections) else total_lines + delta
        rows.append((sid, start + delta, nxt))
    return rows


def render(rows: list[tuple[str, int, int]]) -> list[str]:
    out = [TSV_HEADER]
    out.extend(f"{sid}\t{a}\t{b}" for sid, a, b in rows)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Regenerate the line index of an algorithm document.")
    ap.add_argument("doc", help="path to the algorithm document")
    ap.add_argument(
        "--check", action="store_true", help="verify the index is current; exit 1 if stale"
    )
    args = ap.parse_args()

    with open(args.doc, encoding="utf-8") as fh:
        raw = fh.read()
    had_trailing_newline = raw.endswith("\n")
    lines = raw.splitlines()
    total = len(lines)

    begin, end = find_index_block(lines)
    sections = find_sections(lines, end)
    rows = build_rows(sections, total, begin, end)
    block = render(rows)

    if args.check:
        if lines[begin + 1 : end] == block:
            print(f"{args.doc}: index OK ({len(rows)} entries)")
            return
        print(f"{args.doc}: index STALE -- rerun without --check", file=sys.stderr)
        sys.exit(1)

    new_lines = lines[: begin + 1] + block + lines[end:]
    out = "\n".join(new_lines)
    if had_trailing_newline:
        out += "\n"
    with open(args.doc, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"{args.doc}: index updated ({len(rows)} entries)")


if __name__ == "__main__":
    main()
