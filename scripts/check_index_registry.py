#!/usr/bin/env python3
"""Verify that ``algorithms/INDEX.md`` is in sync with the algorithm docs.

The registry (``algorithms/INDEX.md``) is a hand-maintained table with one
row per algorithm document. Nothing else enforces it: ``doc-index-check``
deliberately skips ``*/INDEX.md``, so a stale row — a ``Version`` that lags
the document's ``METADATA`` version, a ``Status`` drift, a missing row, or
an orphaned row — slips through both the local gate and CI. This script is
that gate (``INDEX.md`` rules 3 and 5).

Checks (per ``algorithms/INDEX.md`` rules 3 and 5):

* every ``algorithms/*.md`` (except ``INDEX.md``) has **exactly one**
  registry row, matched by the row's ``Slug`` or its ``File`` link;
* that row's ``Version`` equals the document's ``METADATA`` ``Version``;
* that row's ``Status`` equals the document's ``METADATA`` ``Status``;
* that row's ``File`` link target exists and is the document itself;
* every registry row points at an existing registered document (no orphans).

Stdlib-only and deterministic, so it runs on the CI runner (no ``.venv``
required). Exit codes: ``0`` = in sync; ``1`` = drift (offending rows
named); ``2`` = structural error (the registry or a document is malformed).

Usage:
    python3 scripts/check_index_registry.py             # check ./algorithms
    python3 scripts/check_index_registry.py --dir DIR   # check another dir
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass

REGISTRY_NAME = "INDEX.md"
EXPECTED_CELLS = 6  # Slug | Name | Version | Status | File | One-line summary

# Split a table row on *unescaped* pipes only (a ``\|`` stays inside a cell).
CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")
# The ``File`` column carries a Markdown link ``[text](target)``; keep target.
FILE_LINK_RE = re.compile(r"\]\(([^)]+)\)")
# METADATA table rows. The ``Status`` pattern is anchored so it does NOT match
# the ``| Status history |`` row.
VERSION_RE = re.compile(r"^\|\s*Version\s*\|\s*([^|]+?)\s*\|\s*$")
STATUS_RE = re.compile(r"^\|\s*Status\s*\|\s*([^|]+?)\s*\|\s*$")
SECTION_MARK_RE = re.compile(r"^<!--\s*SECTION:([A-Z0-9_]+)\s*-->\s*$")
SEPARATOR_RE = re.compile(r"^\|[\s:\-|]+\|$")


class StructuralError(Exception):
    """The registry or a document is malformed; validation cannot proceed."""


@dataclass(frozen=True)
class Row:
    """One parsed registry data row."""

    slug: str
    name: str
    version: str
    status: str
    file_target: str
    summary: str
    line_no: int  # 1-indexed line in INDEX.md, for precise error messages


@dataclass(frozen=True)
class Metadata:
    """The ``Version``/``Status`` fields of a document's METADATA table."""

    version: str
    status: str


def _read_lines(path: str) -> list[str]:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().split("\n")
    except OSError as exc:
        raise StructuralError(f"cannot read {path}: {exc}") from exc


def _split_row(line: str) -> list[str]:
    """Split a ``| a | b |`` row into its cells, preserving interior empties."""
    parts = CELL_SPLIT_RE.split(line)
    if parts and parts[0].strip() == "":
        parts = parts[1:]  # leading pipe
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]  # trailing pipe
    return [p.strip() for p in parts]


def parse_registry(lines: list[str]) -> list[Row]:
    """Parse the single registry table out of ``INDEX.md`` lines."""
    rows: list[Row] = []
    in_table = False
    for i, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not in_table:
            if line.startswith("|") and "Slug" in line and "Version" in line and "Status" in line:
                in_table = True
            continue
        if not line.startswith("|"):
            if rows:
                break  # table ended
            continue
        if SEPARATOR_RE.match(line):
            continue
        cells = _split_row(line)
        if len(cells) != EXPECTED_CELLS:
            raise StructuralError(
                f"INDEX.md line {i}: expected {EXPECTED_CELLS} cells, found {len(cells)}"
            )
        slug, name, version, status, file_cell, summary = cells
        link = FILE_LINK_RE.search(file_cell)
        file_target = link.group(1).strip() if link else file_cell
        rows.append(Row(slug, name, version, status, file_target, summary, i))
    if not in_table:
        raise StructuralError("INDEX.md: registry table header not found")
    if not rows:
        raise StructuralError("INDEX.md: registry table has no data rows")
    return rows


def parse_metadata(lines: list[str]) -> Metadata:
    """Read a document's ``METADATA`` ``Version``/``Status``.

    Scoped to the ``<!-- SECTION:METADATA -->`` block when present (falling
    back to the whole file), so the ``Status history`` row is never confused
    for ``Status``.
    """
    start = None
    for i, line in enumerate(lines):
        mark = SECTION_MARK_RE.match(line)
        if mark and mark.group(1) == "METADATA":
            start = i + 1
            break
    if start is None:
        end = len(lines)
    else:
        end = len(lines)
        for j in range(start, len(lines)):
            if SECTION_MARK_RE.match(lines[j]):
                end = j
                break

    version = status = None
    for line in lines[start:end]:
        if version is None:
            mv = VERSION_RE.match(line.strip())
            if mv:
                version = mv.group(1).strip()
        if status is None:
            ms = STATUS_RE.match(line.strip())
            if ms:
                status = ms.group(1).strip()
    if version is None or status is None:
        raise StructuralError("document METADATA is missing a Version or Status row")
    return Metadata(version, status)


def _list_docs(alg: str) -> dict[str, str]:
    """Map each registered document slug to its file name (top-level only)."""
    docs: dict[str, str] = {}
    for entry in sorted(os.listdir(alg)):
        full = os.path.join(alg, entry)
        if entry.endswith(".md") and entry != REGISTRY_NAME and os.path.isfile(full):
            docs[entry[: -len(".md")]] = entry
    return docs


def validate(algorithms_dir: str) -> list[str]:
    """Return human-readable drift messages; an empty list means in sync.

    Raises :class:`StructuralError` (exit 2) when the registry or a document
    is malformed.
    """
    alg = os.path.abspath(algorithms_dir)
    if not os.path.isdir(alg):
        raise StructuralError(f"algorithms dir not found: {alg}")
    rows = parse_registry(_read_lines(os.path.join(alg, REGISTRY_NAME)))
    docs = _list_docs(alg)

    errors: list[str] = []
    bound: set[int] = set()

    for slug, filename in docs.items():
        meta = parse_metadata(_read_lines(os.path.join(alg, filename)))
        matches = [r for r in rows if r.slug == slug or os.path.basename(r.file_target) == filename]
        bound.update(r.line_no for r in matches)
        if not matches:
            errors.append(f"{filename}: no registry row (expected Slug '{slug}')")
            continue
        if len(matches) > 1:
            where = ", ".join(str(r.line_no) for r in matches)
            errors.append(
                f"{filename}: {len(matches)} registry rows (INDEX.md lines {where}); "
                "expected exactly 1"
            )
            continue
        row = matches[0]
        if row.version != meta.version:
            errors.append(
                f"{filename}: registry Version '{row.version}' != METADATA "
                f"Version '{meta.version}' (INDEX.md line {row.line_no})"
            )
        if row.status != meta.status:
            errors.append(
                f"{filename}: registry Status '{row.status}' != METADATA "
                f"Status '{meta.status}' (INDEX.md line {row.line_no})"
            )
        if os.path.basename(row.file_target) != filename:
            errors.append(
                f"{filename}: registry File '{row.file_target}' does not point at "
                f"the document itself (INDEX.md line {row.line_no})"
            )
        if not os.path.isfile(os.path.join(alg, row.file_target)):
            errors.append(
                f"{filename}: registry File target '{row.file_target}' does not "
                f"exist (INDEX.md line {row.line_no})"
            )

    for row in rows:
        if row.line_no not in bound:
            missing = "" if os.path.isfile(os.path.join(alg, row.file_target)) else ", file missing"
            errors.append(
                f"INDEX.md line {row.line_no}: orphan row (Slug '{row.slug}', "
                f"File '{row.file_target}'{missing})"
            )
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verify algorithms/INDEX.md is in sync with the algorithm docs."
    )
    ap.add_argument(
        "--dir",
        default="algorithms",
        help="path to the algorithms directory (default: ./algorithms)",
    )
    args = ap.parse_args()
    try:
        errors = validate(args.dir)
    except StructuralError as exc:
        print(f"check_index_registry: {exc}", file=sys.stderr)
        return 2
    if errors:
        for err in errors:
            print(f"check_index_registry: {err}", file=sys.stderr)
        print(f"check_index_registry: {len(errors)} problem(s) found", file=sys.stderr)
        return 1
    print("check_index_registry: algorithms/INDEX.md in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
