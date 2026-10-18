"""mdconv: deterministic rich-HTML -> GFM block converter for eGain article content.

Implements ``algorithms/html-to-markdown-section-extraction.md`` (v0.15.0):

- total, deterministic two-context (block/inline) tree walk over a lenient
  lxml parse (BeautifulSoup is the parser of record: fragments stay flat);
- text fidelity: decorative spans/divs unwrap, ``&nbsp;`` -> space,
  zero-width junk removed, whitespace runs collapsed to a single space;
- emphasis/code/strikethrough markers hug their content (E10: empty
  emphasis is dropped); one space is inserted only between touching
  emphasis markers (E8) or between a non-word boundary and a word start,
  so punctuation never glues to a following word (TESTS case 13);
- tables are GFM: first row is the header, ragged rows padded (E12),
  literal pipes escaped exactly once (E13); a table inside a cell renders
  as an aligned box-drawing monospace table in a ``<pre>`` block —
  cells wrapped at W = 48 rendered columns, one blank spacer row between
  data rows, box borders are not pipes (D13, B20, ``_render_table_inline``); a table whose
  every row's first cell leads with a heading is a *layout frame* and
  dissolves into real headings at their native level with block-rendered
  content (D5, ``_render_layout_frame``);
- layout frames dissolve by *row kind* (D8): a heading label (T1), a
  plain-text section-mark or meta label with exactly two visible cells (T2,
  B6), or an all-empty row (T3, renders nothing); a label that normalizes
  exactly to ``Change Date`` renders as the GFM quote block
  ``> **Change Date**`` + ``> {date}`` (B11, both the T1 and T2 paths);
- a decorative block-level ``<hr>`` (eGain wraps every layout-frame row in
  pure-``<hr>`` wrapper divs) renders nothing — the same layout-decoration
  class as the dissolved tables — but still delimits blocks (D9, B13);
- named anchors — an ``<a>`` with an ``id``/``name`` but no usable link
  target — are preserved as self-closing ``<a id=...></a>`` markers,
  namespaced per article (``art_<id>_``) and hoisted to their own line
  before headings; fragment-only hrefs (``#frag``) are rewritten into the
  same namespace while a bare ``#`` is left untouched (D6, ``_anchor_marker``
  / ``_collect_named_anchors``);
- inline-level content (text, emphasis, links, named anchors, and inline-only
  containers) accumulates into one paragraph run that is flushed at
  block-element boundaries; only containers holding a real block element
  split the run (D7, ``_contains_block_el``);
- orphan table parts (``caption``/``tbody``/``tfoot``/``thead``/``tr``/
  ``th``/``td``) in block position unwrap with the same D7 semantics as
  containers — block content recurses, inline content joins the run — and
  are never dropped (D14, ``_TABLE_PART``);
- ``javascript:`` hrefs are dropped (E6); empty-text links use their URL
  (E7); eGain article URLs are canonicalized (query string dropped);
- output = blocks joined by ``"\\n\\n"`` + exactly one trailing ``"\\n"``.

Pure and side-effect free: same input + same ``base_url`` => byte-identical
output. No timestamps, no randomness, no sorting, no dedupe.
"""

import re

from bs4 import BeautifulSoup, NavigableString, Tag

__all__ = ["HtmlConversionError", "convert"]

_WS_RUN = re.compile(r"[ \t\r\n\f\v]+")
_ZERO_WIDTH = ("\u200b", "\ufeff", "\u200e", "\u200f")
_ARTICLE_URL = re.compile(r"^(https?://[^/]+/system/ws/v\d+/ss/article/)(\d+)(\?.*)?$")
_MARKER = set("*_`~")
_HEADING = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_UNWRAP_BLOCK = frozenset({"div", "span", "font", "center"})
# D14: orphan table parts unwrap in block context with D7 semantics. Kept
# separate from _UNWRAP_BLOCK: that set also drives D12 frame
# classification, and adding table parts there would change frame
# decisions for malformed input.
_TABLE_PART = frozenset({"caption", "tbody", "tfoot", "th", "thead", "tr", "td"})
_LIST = frozenset({"ul", "ol"})
_BLOCK = _HEADING | {"p", "ul", "ol", "table", "blockquote", "pre", "hr"}  # D7: no div
_INLINE_UNWRAP = _HEADING | {
    "p",
    "div",
    "span",
    "font",
    "u",
    "center",
    "small",
    "big",
    "sup",
    "sub",
    "blockquote",
}
# D8 (B6): generalized layout-frame row classification
_SECTION_MARK = re.compile(r"^[IVXLC]+\.\s?(?:iv|iii|ii|i)(?:\.\s?[A-Za-z0-9]+)*\.\s")
_META_LABELS = frozenset({"Introduction", "Change Date", "In This Section", "Overview"})
_CHANGE_DATE = "Change Date"
_VISIBLE_BLOCK = frozenset({"img", "table", "ul", "ol"})
# D11 (B10): dead legacy portal host -> canonical live host. The host must
# be followed by /, ?, #, or end-of-string, so look-alike hosts
# (vaww.vrm.km.va.gov.evil.example) do not match.
_LEGACY_HOST = re.compile(r"^(https?://)vaww\.vrm\.km\.va\.gov(?=[/?#]|$)")
_LIVE_HOST = "www.knowva.ebenefits.va.gov"


class HtmlConversionError(RuntimeError):
    """Raised when an article's HTML cannot be parsed at all (doc 2.7)."""

    def __init__(self, article_id: str, cause: BaseException) -> None:
        super().__init__(f"HTML conversion failed for article '{article_id}': {cause}")
        self.article_id = article_id
        self.cause = cause


def _parse(html: str) -> BeautifulSoup:
    """Lenient tree parse (lxml). Module-level seam for failure injection."""
    return BeautifulSoup(html, "lxml")


def convert(html: str | None, *, base_url: str, article_id: str = "") -> str:
    """Convert one article's HTML fragment to a GFM string (doc contract 2.1).

    ``None`` / ``""`` / whitespace-only input returns ``""`` (rule 4).
    Parser-level failure raises :class:`HtmlConversionError`; the caller
    (assemble step) decides how to record it (doc 2.7).
    """
    if html is None:
        return ""
    if not isinstance(html, str):
        raise TypeError("html must be a str or None")
    if html.strip() == "":
        return ""
    try:
        soup = _parse(html)
    except Exception as cause:  # parser-level failure (doc 2.7)
        raise HtmlConversionError(article_id, cause) from cause
    # The lxml builder wraps a fragment in <html><body>; render the innermost
    # body's children (the fragment's top level) in block context.
    root = soup.find("body")
    if root is None:
        root = soup
    ns = f"art_{article_id}_" if article_id else ""  # D6: per-article anchor namespace
    blocks = [b for b in _render_block_list(root.contents, base_url, ns) if b != ""]
    if not blocks:
        return ""
    return "\n\n".join(blocks) + "\n"


# --- block context -----------------------------------------------------------


def _render_block_list(children, base_url: str, ns: str) -> list[str]:
    # D7: only _BLOCK elements start a new block; everything else is
    # inline-level and accumulates in ``run``. The run is flushed -- pieces
    # joined one by one (E8), stripped, appended if non-empty -- at each
    # block element and at the end of the list.
    blocks: list[str] = []
    run: list[str] = []

    def flush() -> None:
        t = ""
        for piece in run:
            t = _join_inline(t, piece)
        t = t.strip()
        run.clear()
        if t != "":
            blocks.append(t)

    for child in children:
        if isinstance(child, NavigableString):
            t = _normalize_text(str(child))
            if t.strip() != "":
                run.append(t)  # D7: unstripped; boundary whitespace survives the join
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name or ""
        if name in _BLOCK:
            flush()
            if name in _HEADING:
                for m in _collect_named_anchors(child, base_url, ns):  # D6: hoist to own lines
                    blocks.append(m)
                t = _render_inline_children(child, base_url, ns, anchor_mode="text").strip()
                if t != "":
                    blocks.append("#" * int(name[1]) + " " + t)
            elif name == "p":
                t = _render_inline_children(child, base_url, ns).strip()
                if t != "":
                    blocks.append(t)
            elif name in _LIST:
                b = _render_list(child, base_url, ns)
                if b != "":
                    blocks.append(b)
            elif name == "table":
                b = _render_table(child, base_url, ns)
                if b != "":
                    blocks.append(b)
            elif name == "hr":
                pass  # D9 (B13): decorative eGain rule — flush already ran; render nothing
            elif name == "blockquote":
                inner = [x for x in _render_block_list(child.children, base_url, ns) if x != ""]
                if inner:
                    body = "\n\n".join(inner)
                    blocks.append("\n".join("> " + line for line in body.split("\n")))
            elif name == "pre":
                code = child.get_text()  # newlines/indentation preserved verbatim
                fence = "````" if "```" in code else "```"
                blocks.append(f"{fence}\n{code}\n{fence}")
        elif name == "div":  # D16 (B21): an inline-only div is a paragraph boundary
            if _contains_block_el(child) or _contains_div(child):  # D16: block or child-div group
                flush()
                blocks.extend(_render_block_list(child.children, base_url, ns))
            else:  # D16: inline-only div -> its inline content becomes its own block
                flush()
                t = _render_inline_children(child, base_url, ns).strip()
                if t:
                    blocks.append(t)
        elif name in _UNWRAP_BLOCK or name in _TABLE_PART:  # D14: table parts
            if _contains_block_el(child):  # D7: real block structure inside
                flush()
                blocks.extend(_render_block_list(child.children, base_url, ns))
            else:  # D7: inline-only container flattens into the run
                for c in child.children:
                    run.append(_render_inline_piece(c, base_url, ns))
        elif name == "a":
            m = _anchor_marker(child, base_url, ns)  # D6: None unless a named anchor
            if m is not None and _contains_block_el(child):  # D6: block-level anchor
                flush()
                blocks.append(m)  # marker as its own block line
                blocks.extend(_render_block_list(child.children, base_url, ns))
            elif m is not None:  # D7: inline-level anchor joins the run
                run.append(m + _render_inline_children(child, base_url, ns))
            elif _contains_block_el(child):  # link holding blocks: drop it
                flush()
                blocks.extend(_render_block_list(child.children, base_url, ns))
            else:  # D7: plain link in the run
                inner = _render_inline_children(child, base_url, ns).strip()
                if inner == "":
                    continue  # empty link, no marker: nothing
                url = _rewrite_url(child.get("href"), base_url, ns)
                if url is not None:
                    run.append(f"[{inner}]({url})")
                else:  # E6: no usable href -> plain text
                    run.append(inner)
        else:
            # D15: unknown/malformed tag in block position.
            if _contains_block_el(child):  # block-holding unknown: unwrap as wrapper
                flush()
                blocks.extend(_render_block_list(child.children, base_url, ns))
            else:  # inline-only unknown: keep the run behavior (no regression)
                run.append(_render_inline_piece(child, base_url, ns))
    flush()
    return blocks


def _contains_block_el(el: Tag) -> bool:
    """D7: True if ``el`` has a descendant tag in :data:`_BLOCK`.

    Containers (``div``/``span``/``font``/``center``) are deliberately not
    in ``_BLOCK``: a container holding only inline content is inline-level
    and coalesces into the current run instead of splitting it.
    """
    return any(isinstance(d, Tag) and (d.name or "") in _BLOCK for d in el.descendants)


def _contains_div(el: Tag) -> bool:
    """D16 (B21): True if ``el`` has a descendant ``<div>``.

    A ``<div>`` that groups child ``<div>``s (e.g. the §II.iii.1.A.2.d Example
    and Analysis blocks, each in its own inner ``<div>``) is a paragraph
    container: it recurses so each child ``<div>`` becomes its own paragraph
    instead of the whole group flattening into one merged paragraph.
    """
    return any(isinstance(d, Tag) and (d.name or "") == "div" for d in el.descendants)


# --- inline context ----------------------------------------------------------


def _render_inline_children(
    el: Tag, base_url: str, ns: str, anchor_mode: str = "inline", pre_ctx: bool = False
) -> str:
    out = ""
    for child in el.children:
        out = _join_inline(out, _render_inline_piece(child, base_url, ns, anchor_mode, pre_ctx))
    return out


def _join_inline(left: str, right: str) -> str:
    """Join two inline pieces (doc rule E8 + TESTS case 13/25 boundaries).

    One space is inserted only where the concatenation would be ambiguous or
    glue a word onto a preceding non-word boundary; otherwise pieces join
    verbatim (document order preserved).
    """
    if left == "" or right == "":
        return left + right
    if left[-1] == " " or right[0] == " ":
        return left + right
    if left[-1] in _MARKER and right[0] in _MARKER:
        return left + " " + right  # E8: adjacent emphasis markers disambiguated
    if not left[-1].isalnum() and left[-1] not in _MARKER and right[0].isalnum():
        return left + " " + right  # word after punctuation (TESTS case 13)
    return left + right


def _render_inline_piece(
    child, base_url: str, ns: str, anchor_mode: str = "inline", pre_ctx: bool = False
) -> str:
    if isinstance(child, NavigableString):
        return _normalize_text(str(child))
    name = child.name or ""
    if name in {"b", "strong"}:
        return _wrap(_render_inline_children(child, base_url, ns, anchor_mode, pre_ctx), "**")
    if name in {"i", "em"}:
        return _wrap(_render_inline_children(child, base_url, ns, anchor_mode, pre_ctx), "*")
    if name in {"s", "strike", "del"}:
        return _wrap(_render_inline_children(child, base_url, ns, anchor_mode, pre_ctx), "~~")
    if name == "code":
        text = child.get_text().strip()
        return f"`{text}`" if text != "" else ""
    if name == "a":
        inner = _render_inline_children(child, base_url, ns, anchor_mode, pre_ctx).strip()
        url = _rewrite_url(child.get("href"), base_url, ns)
        if url is not None:
            if inner == "":
                inner = url  # E7: link with no text uses its URL
            return f"[{inner}]({url})"  # D6: a live link wins; id/name dropped
        m = _anchor_marker(child, base_url, ns)  # D6: None unless a named anchor
        if m is not None:
            if anchor_mode == "text":
                return inner  # marker hoisted by the caller
            return m + inner  # inline: marker immediately before the anchor text
        return inner  # E6: no usable href, no id/name -> plain text
    if name == "br":
        return " "  # E9
    if name == "img":
        src = child.get("src")
        if src is None:
            return ""
        url = _rewrite_url(src, base_url, ns)
        if url is None:
            return ""
        alt = child.get("alt") or ""
        return f"![{alt}]({url})"
    if name in _LIST:
        return _render_list_inline(child, base_url, ns, anchor_mode, pre_ctx)
    if name == "table":
        return _render_table_inline(child, base_url, ns)
    if name in _INLINE_UNWRAP:
        return _render_inline_children(
            child, base_url, ns, anchor_mode, pre_ctx
        )  # level lost in cells
    if name == "hr":
        return " — "  # hr in inline position
    if name == "pre":
        return child.get_text()
    return _render_inline_children(
        child, base_url, ns, anchor_mode, pre_ctx
    )  # unknown: unwrap (totality)


def _wrap(inner: str, marker: str) -> str:
    inner = inner.strip()
    return "" if inner == "" else marker + inner + marker  # E10: never empty markers


# --- tables ------------------------------------------------------------------


def _render_table(el: Tag, base_url: str, ns: str) -> str:
    if _is_layout_frame(el):
        return _render_layout_frame(el, base_url, ns)  # D5: dissolve the frame
    rows: list[list[str]] = []
    for tr in _table_rows(el):
        cells = [_render_cell(c, base_url, ns) for c in _cells_of(tr)]
        if cells:  # non-empty cell list (doc render_table)
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]  # E12: pad ragged rows
    lines = [
        "| " + " | ".join(_escape_pipe(c) for c in rows[0]) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    for r in rows[1:]:
        lines.append("| " + " | ".join(_escape_pipe(c) for c in r) + " |")
    return "\n".join(lines)


def _layout_heading(cell: Tag) -> Tag | None:
    """D5+D12: the cell's first significant child, if it is a heading ``h1``-``h6``.

    Whitespace-only text is skipped; decorative containers
    (``_UNWRAP_BLOCK``) are followed transparently, so a heading wrapped in
    a ``<span>``, ``<font>``, ``<center>``, or ``<div>`` still leads the
    cell (D12). Any other first child (visible text, ``p``, ``th``, a
    list, ...) disqualifies; an all-empty container returns ``None``.
    The conservative GFM fallback never drops text.
    """
    node: Tag = cell
    while True:
        first: Tag | None = None
        for child in node.children:
            if isinstance(child, NavigableString):
                if _normalize_text(str(child)).strip() != "":
                    return None  # text first: not a label cell
                continue
            if isinstance(child, Tag):
                first = child
                break
            return None  # comments and other nodes disqualify
        if first is None:
            return None
        name = first.name or ""
        if name in _HEADING:
            return first
        if name in _UNWRAP_BLOCK:
            node = first  # follow the decorative container (D12)
            continue
        return None


def _cell_visible(cell: Tag) -> bool:
    """D8: a cell is *visible* if it shows text or a block-level element.

    Whitespace-only spacers are invisible; a cell holding an ``img``/
    ``table``/list but no text still counts (TESTS case44 image cell).
    """
    if _normalize_text(cell.get_text()).strip() != "":
        return True
    return any(isinstance(d, Tag) and (d.name or "") in _VISIBLE_BLOCK for d in cell.descendants)


def _plain_label(cell: Tag) -> str:
    """D8: the label cell's normalized plain text (stripped)."""
    return _normalize_text(cell.get_text()).strip()


def _label_inline_equiv(cell: Tag) -> bool:
    """D12: the T2 inline guard, relaxed (doc D12).

    Every block-level descendant (per ``_BLOCK``) must be a ``p`` — a
    ``p``-wrapped inline label renders identically to the bare label; any
    other block element (heading, list, table, ...) disqualifies. A label
    with no block descendants is inline-equivalent.
    """
    return all(
        (d.name or "") == "p"
        for d in cell.descendants
        if isinstance(d, Tag) and (d.name or "") in _BLOCK
    )


def _rest_children(children, heading: Tag) -> list:
    """D12: a label cell's content other than ``heading``, in document order.

    Decorative containers (``_UNWRAP_BLOCK``) are unwrapped transparently
    so a container wrapping the heading contributes its *other* children
    (text is never dropped); the heading itself is excluded.
    """
    out: list = []
    for node in children:
        if node is heading:
            continue
        if isinstance(node, Tag) and (node.name or "") in _UNWRAP_BLOCK:
            out.extend(_rest_children(node.children, heading))
        else:
            out.append(node)
    return out


def _frame_row_kind(tr: Tag) -> str | None:
    """D8: classify one frame row (doc 2.2).

    ``T1`` — the first heading-bearing cell leads with a heading
    (D5∪D12: ``cells[0]`` visibility-agnostic, else the first visible
    cell; the heading may sit in a decorative container); ``T2`` — after
    stripping invisible spacers exactly two visible cells remain and the
    first is an inline-equivalent label (B6 plain label; D12 relaxed
    guard) whose text is a section mark or a meta label; ``T3`` — no
    visible cell (renders nothing); ``None`` — a genuine data row, which
    disqualifies the whole table.
    """
    cells = _cells_of(tr)
    if not cells:
        return None
    visible = [c for c in cells if _cell_visible(c)]
    if not visible:
        return "T3"
    if _layout_heading(cells[0]) is not None:
        return "T1"
    if _layout_heading(visible[0]) is not None:
        return "T1"
    if len(visible) != 2 or not _label_inline_equiv(visible[0]):
        return None
    label = _plain_label(visible[0])
    if _SECTION_MARK.match(label) or label in _META_LABELS:
        return "T2"
    return None


def _is_layout_frame(el: Tag) -> bool:
    """D8: a table whose EVERY row classifies as T1/T2/T3 (doc 2.2).

    eGain wraps article content in ``label | spacer | content`` grids whose
    label cells carry section marks (``I.i.1.A.1.a. ...``) or meta labels
    (``Introduction``/``Change Date``/``In This Section``/``Overview``), in
    either a heading (T1) or plain text (T2). A single genuine data row
    (``None``) disqualifies the whole table, which keeps GFM rendering.
    """
    rows = _table_rows(el)
    return bool(rows) and all(_frame_row_kind(tr) is not None for tr in rows)


def _change_date_blocks(body: list[str]) -> list[str]:
    """B11: a Change Date frame renders as a GFM quote block.

    Single-line body -> a two-line quote (marker line + date line); a
    multi-block body -> the marker line alone, then the body blocks after
    it (never drop text).
    """
    if len(body) == 1 and "\n" not in body[0]:
        return [f"> **Change Date**\n> {body[0]}"]
    return ["> **Change Date**", *body]


def _render_layout_frame(el: Tag, base_url: str, ns: str) -> str:
    """D8: dissolve a layout frame row by row (doc 2.2).

    T1 — the first heading-bearing cell leads with a heading
    (D5∪D12: ``cells[0]`` visibility-agnostic, else the first visible
    cell; MRS): emit it at
    its *native level* (named anchors hoisted first, D6), keep the label
    cell's non-heading children (D12: decorative containers unwrapped,
    text never dropped), then block-render the remaining cells so nested
    data tables surface as real GFM tables. T2 — a plain-text label (section mark or
    meta label): emit ``### `` + the label (anchors hoisted) then
    block-render the content cell. T3 — a row with no visible cell renders
    nothing. B11: a label normalizing exactly to ``Change Date`` renders
    as a quote block instead of a heading, on both the T1 and T2 paths.
    A T3-only frame returns ``""`` and the caller drops it (the
    ``if b != ""`` guard in :func:`_render_block_list`).
    """
    blocks: list[str] = []
    for tr in _table_rows(el):
        cells = _cells_of(tr)
        if not cells:
            continue
        kind = _frame_row_kind(tr)
        if kind == "T3":
            continue
        if kind == "T1":
            visible = [c for c in cells if _cell_visible(c)]
            heading_first = _layout_heading(cells[0])
            label = cells[0] if heading_first is not None else visible[0]  # D5∪D12 (MRS)
            heading = _layout_heading(label)
            for m in _collect_named_anchors(heading, base_url, ns):  # D6: hoist
                blocks.append(m)
            t = _render_inline_children(heading, base_url, ns, anchor_mode="text").strip()
            rest: list[str] = []
            for node in _rest_children(label.children, heading):  # D12: keep the rest
                rest.extend(b for b in _render_block_list([node], base_url, ns) if b != "")
            for cell in cells:  # D12: all other cells, document order
                if cell is label:
                    continue
                rest.extend(b for b in _render_block_list(cell.children, base_url, ns) if b != "")
            if _plain_label(heading) == _CHANGE_DATE:  # B11+B15: plain text
                blocks.extend(_change_date_blocks(rest))
            else:
                if t != "":
                    blocks.append("#" * int(heading.name[1]) + " " + t)
                blocks.extend(rest)
        elif kind == "T2":
            visible = [c for c in cells if _cell_visible(c)][:2]
            label, content = visible[0], visible[1]
            for m in _collect_named_anchors(label, base_url, ns):  # D6: hoist
                blocks.append(m)
            if _plain_label(label) == _CHANGE_DATE:  # B11
                body = [b for b in _render_block_list(content.children, base_url, ns) if b != ""]
                blocks.extend(_change_date_blocks(body))
            else:
                blocks.append("### " + _plain_label(label))
                for b in _render_block_list(content.children, base_url, ns):
                    if b != "":
                        blocks.append(b)
    return "\n\n".join(blocks)


# --- nested-table box-drawing (D13, B20) ------------------------------------

_NESTED_W = 48  # wrap width for a nested-table cell, in rendered columns


def _rendered_width(s: str) -> int:
    """Rendered display width: markdown inline syntax stripped (D13).

    Image -> alt text, link -> link text, code span -> inner text, and
    emphasis markers (``*``/``_``) dropped, then count visible chars.
    The target renderers process markdown inside ``<pre>``, so box
    borders align on this width, not the source length.
    """
    t = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", s)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = t.replace("*", "").replace("_", "")
    return len(t)


_TOKEN_RE = re.compile(
    r"!\[[^\]]*\]\([^)]*\)"  # image
    r"|\[[^\]]*\]\([^)]*\)"  # link
    r"|`[^`\n]*`"  # code span
    r"|[*_]{1,3}[^\s*_][^*_]*[*_]{1,3}"  # emphasis run
)


def _tokenize(md: str) -> list[tuple[str, bool]]:
    """Split markdown into (unit, sep) pairs (D13).

    Image/link/code/emphasis runs stay atomic; plain text splits into
    words. ``sep`` is True iff the source had whitespace immediately
    before the unit, so the joiner never inserts a space where the
    source had none.
    """
    units: list[tuple[str, bool]] = []

    def add_plain(gap: str, first: bool) -> None:
        frags = gap.split()
        leading_ws = bool(gap) and gap[0].isspace()
        for j, frag in enumerate(frags):
            units.append((frag, True if j > 0 else (not first) and leading_ws))

    pos = 0
    for m in _TOKEN_RE.finditer(md):
        add_plain(md[pos : m.start()], first=not units)
        units.append((m.group(0), m.start() > pos and md[m.start() - 1].isspace()))
        pos = m.end()
    add_plain(md[pos:], first=not units)
    return units


def _join_units(units: list[tuple[str, bool]]) -> str:
    """Rejoin a line's units, inserting a space exactly where ``sep`` was."""
    out = ""
    for text, sep in units:
        if out and sep:
            out += " "
        out += text
    return out


def _wrap_cell(md: str, width: int) -> list[str]:
    """Greedy wrap at *width* rendered columns (D13).

    A piece that already fits within *width* is returned verbatim. This is
    what keeps a B27 raw-symbol list line's leading whitespace intact — its
    bullet/circle level indent and its hanging indent — because the word
    tokenizer would otherwise strip that whitespace when it rejoins the
    words (D17). Pieces that overflow are wrapped: atomic units never split,
    and an oversized atomic unit takes its own line.
    """
    if _rendered_width(md) <= width:
        return [md]
    lines: list[str] = []
    cur: list[tuple[str, bool]] = []
    cur_w = 0
    for text, sep in _tokenize(md):
        w = _rendered_width(text)
        join_w = 1 if (cur and sep) else 0
        if cur and cur_w + join_w + w > width:
            lines.append(_join_units(cur))
            cur, cur_w = [(text, False)], w
        else:
            cur.append((text, sep))
            cur_w += join_w + w
    if cur:
        lines.append(_join_units(cur))
    return lines if lines else [""]


_BOX_RE = re.compile(r"<pre>(.*?)</pre>", re.S)  # inner box within a cell (B20)


def _cell_lines(md: str) -> list[str]:
    """A cell's lines for the enclosing box: text wraps, boxes stay atomic (D13).

    A non-box segment is first split on ``<br>`` — each piece becomes its
    own line, which is what turns a B27 raw-symbol list (items joined with
    ``<br>``) into individual box lines — and each non-empty piece wraps at
    ``_NESTED_W``; a segment that is an inner ``<pre>`` box-drawing table is
    emitted line-for-line verbatim, because re-wrapping it would shred its
    borders.
    Whitespace-only text segments contribute no lines. A cell holding
    an inner box therefore stretches the outer row and its siblings
    pad with blanks; each inner box line is an opaque fixed-width line,
    so recursion keeps arbitrary nesting depth aligned (B20).
    """
    lines: list[str] = []
    pos = 0
    for m in _BOX_RE.finditer(md):
        seg = md[pos : m.start()]
        for piece in seg.split("<br>"):
            if piece.strip() != "":
                lines.extend(_wrap_cell(piece, _NESTED_W))
        lines.extend(m.group(1).split("<br>"))
        pos = m.end()
    tail = md[pos:]
    for piece in tail.split("<br>"):
        if piece.strip() != "":
            lines.extend(_wrap_cell(piece, _NESTED_W))
    return lines or [""]


def _render_table_inline(el: Tag, base_url: str, ns: str) -> str:
    """Nested table (inside a cell): an aligned box-drawing monospace
    table in a ``<pre>`` block (D13, B20).

    Border set ``┌┬┐│├┼┤└┴┘─``: top border, first (header) row, a
    separator row always under the first row, one blank spacer row
    between consecutive data rows, bottom border. Each cell wraps at
    W = 48 *rendered* columns (:func:`_rendered_width`), except a cell
    holding an inner box emits that box's lines verbatim as an atomic
    line-block (:func:`_cell_lines`) and the column widens to the widest
    such line, sibling cells padded on blank lines. Every box line has
    an identical rendered width, so the borders align after
    the renderer strips the markdown. Atomic units (image, link, code
    span, emphasis run) never split across lines, and no space is
    inserted where the source had none. Ragged rows pad with empty
    cells first so column widths are stable; a multi-line cell
    stretches its row and the other cells pad with blanks.

    Box characters are not ASCII pipes, so the enclosing
    :func:`_render_table` escapes every literal pipe in the cell
    exactly once (E13) and that pass is a no-op on the borders (D3);
    a literal ``|`` in cell content still escapes exactly once.
    """
    rows: list[list[str]] = []
    for tr in _table_rows(el):
        cells = [_render_cell(c, base_url, ns, pre_ctx=True) for c in _cells_of(tr)]
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]  # pad ragged rows
    wrapped = [[_cell_lines(c) for c in r] for r in rows]  # B20: inner boxes stay atomic
    col_w = [
        max(_rendered_width(line) for r in range(len(rows)) for line in wrapped[r][i]) + 2
        for i in range(width)
    ]  # +2: leading space + at least one trailing space

    def pad(line: str, w: int) -> str:
        return " " + line + " " * (w - 1 - _rendered_width(line))

    def rule(left: str, join: str, right: str) -> str:
        return left + join.join("─" * w for w in col_w) + right

    def emit_row(cell_lines: list[list[str]]) -> list[str]:
        n = max(len(cl) for cl in cell_lines)
        return [
            "│"
            + "".join(
                pad(cl[i] if i < len(cl) else "", w) + "│"
                for cl, w in zip(cell_lines, col_w, strict=True)
            )
            for i in range(n)
        ]

    lines: list[str] = [rule("┌", "┬", "┐"), *emit_row(wrapped[0]), rule("├", "┼", "┤")]
    for k in range(1, len(wrapped)):
        lines.extend(emit_row(wrapped[k]))
        if k < len(wrapped) - 1:
            lines.append("".join("│" + pad("", w) for w in col_w) + "│")
    lines.append(rule("└", "┴", "┘"))
    return "<pre>" + "<br>".join(lines) + "</pre>"


def _render_cell(cell: Tag, base_url: str, ns: str, pre_ctx: bool = False) -> str:
    return _render_inline_children(cell, base_url, ns, pre_ctx=pre_ctx).strip()


def _render_list_inline(
    el: Tag, base_url: str, ns: str, anchor_mode: str = "inline", pre_ctx: bool = False
) -> str:
    """List in inline position (inside a cell): emit real HTML ``<ul>/<ol>/<li>``.

    Direct ``<li>`` only — each item once, so nested children are never duplicated
    (B25: the old recursive ``find_all("li")`` emitted nested items twice); each
    ``<li>`` keeps its inline Markdown content and recurses into nested lists;
    the list is not ``"; "``-flattened, so ``<ol>`` numbering is preserved (B26).
    Renders as a real list in every renderer while preserving the list's
    organization (doc D13-adjacent in-cell rule; TESTS 19, 82-85).

    Inside a box-drawing ``<pre>`` table (``pre_ctx``) the HTML list tags would
    wrap across the fixed width and break the borders, so defer to the raw-symbol
    renderer instead (B27; doc D17; TESTS 84-86).
    """
    if pre_ctx:
        return _render_list_raw(el, base_url, ns, anchor_mode)

    def render(list_el: Tag) -> str:
        tag = list_el.name or "ul"
        parts: list[str] = ["<" + tag + ">"]
        for li in [c for c in list_el.children if isinstance(c, Tag) and (c.name or "") == "li"]:
            seq: list[str] = []
            for c in li.children:
                if isinstance(c, Tag) and (c.name or "") in _LIST:
                    seq.append(render(c))
                else:
                    seq.append(_render_inline_piece(c, base_url, ns, anchor_mode))
            content = "".join(seq).strip()
            if content:
                parts.append("<li>" + content + "</li>")
        parts.append("</" + tag + ">")
        return "".join(parts)

    return render(el)


def _render_list_raw(
    el: Tag, base_url: str, ns: str, anchor_mode: str = "inline", level: int = 1
) -> str:
    """A list inside a box-drawing ``<pre>`` table (B27).

    HTML ``<ul>/<ol>/<li>`` tags would render as list elements that wrap
    across the fixed 48-column width and break the box borders, so emit raw
    text symbols instead: odd level = bullet ``\u2022``, even level = circle
    ``\u25e6``, deeper levels add two indent spaces. Each item's text is
    wrapped to ``(48 - prefix_width)`` rendered columns with a hanging indent —
    the first line carries the prefix, every continuation line is indented by
    the prefix width — so the text aligns and each line keeps an identical
    rendered width, keeping the box borders aligned. Items are joined with
    ``<br>`` so :func:`_cell_lines` splits them into individual box lines. An
    empty-text parent still emits its sub-items (no bare bullet).
    """
    symbol = "\u2022" if level % 2 == 1 else "\u25e6"
    prefix = "  " * (level - 1) + symbol + " "
    width = _NESTED_W - len(prefix)
    lines: list[str] = []
    for li in [c for c in el.children if isinstance(c, Tag) and (c.name or "") == "li"]:
        own: list[str] = []
        subs: list[Tag] = []
        for c in li.children:
            if isinstance(c, Tag) and (c.name or "") in _LIST:
                subs.append(c)
            else:
                own.append(_render_inline_piece(c, base_url, ns, anchor_mode, True))
        text = "".join(own).strip()
        if text != "":
            wrapped = _wrap_cell(text, width)
            lines.append(prefix + wrapped[0])
            for extra in wrapped[1:]:
                lines.append(" " * len(prefix) + extra)  # hanging indent
        for sub in subs:
            for line in _render_list_raw(sub, base_url, ns, anchor_mode, level + 1).split("<br>"):
                lines.append(line)
    return "<br>".join(lines)


def _escape_pipe(s: str) -> str:
    return s.replace("|", "\\|")  # E13


def _table_rows(table: Tag) -> list[Tag]:
    """``tr`` elements that belong to *this* table, in document order.

    ``find_all`` is recursive; rows of nested tables must not be rendered as
    rows of the outer table (TESTS case 13), so keep only rows whose nearest
    table ancestor is ``table`` itself.
    """
    rows = []
    for tr in table.find_all("tr"):
        if _nearest_ancestor(tr, {"table"}) is table:
            rows.append(tr)
    return rows


def _cells_of(tr: Tag) -> list[Tag]:
    """``td``/``th`` cells that belong to *this* row, in document order."""
    cells = []
    for c in tr.find_all(["td", "th"]):
        if _nearest_ancestor(c, {"tr"}) is tr:
            cells.append(c)
    return cells


def _nearest_ancestor(el: Tag, names: set[str]) -> Tag | None:
    for anc in el.parents:
        if isinstance(anc, Tag) and (anc.name or "") in names:
            return anc
    return None


# --- lists -------------------------------------------------------------------


def _render_list(el: Tag, base_url: str, ns: str) -> str:
    ordered = el.name == "ol"
    lines: list[str] = []
    i = 1
    for li in [
        c for c in el.children if isinstance(c, Tag) and (c.name or "") == "li"
    ]:  # direct <li> only
        marker = f"{i}. " if ordered else "- "  # E14
        inline_parts: list[str] = []
        sublists: list[Tag] = []
        for c in li.children:
            if isinstance(c, Tag) and (c.name or "") in _LIST:
                sublists.append(c)
            else:
                inline_parts.append(_render_inline_piece(c, base_url, ns))
        text = ""
        for piece in inline_parts:
            text = _join_inline(text, piece)
        if text.strip() != "":
            lines.append(marker + text.strip())
        for sl in sublists:  # E15: 4-space indent for nested lists
            for line in _render_list(sl, base_url, ns).split("\n"):
                lines.append("    " + line)
        i += 1
    return "\n".join(lines)


# --- normalization and URLs --------------------------------------------------


def _normalize_text(s: str) -> str:
    """Nbsp -> space (FIRST), zero-width junk deleted, runs collapsed to one.

    Deliberately NOT stripped: inline pieces keep boundary whitespace so that
    ``&nbsp;`` separators survive (TESTS case 11); block boundaries apply
    ``strip()`` where a finished block is assembled.
    """
    s = s.replace("\u00a0", " ")
    for zw in _ZERO_WIDTH:
        s = s.replace(zw, "")
    return _WS_RUN.sub(" ", s)


# --- named anchors (D6) ------------------------------------------------------


def _escape_attr(v: str) -> str:
    return v.replace('"', "&quot;")


def _anchor_marker(a: Tag, base_url: str, ns: str) -> str | None:
    """D6: a self-closing marker for a *named anchor*, else ``None``.

    An ``<a>`` is a named anchor iff it carries a non-empty ``id`` and/or
    ``name`` **and** has no usable link target (``_rewrite_url`` -> None).
    A live link wins and its id/name are dropped (documented limitation).
    """
    if _rewrite_url(a.get("href"), base_url, ns) is not None:
        return None
    idv = a.get("id")
    namev = a.get("name")
    if (idv is None or idv == "") and (namev is None or namev == ""):
        return None
    out = "<a"
    if idv is not None and idv != "":
        out += f' id="{_escape_attr(ns + idv)}"'
    if namev is not None and namev != "":
        out += f' name="{_escape_attr(ns + namev)}"'
    return out + "></a>"


def _collect_named_anchors(el: Tag, base_url: str, ns: str) -> list[str]:
    """D6: markers for every named anchor in ``el``'s subtree, document order.

    Used to hoist heading/label anchors to their own lines (raw HTML inline
    in an ATX heading is the least renderer-portable spot).
    """
    out = []
    for node in el.descendants:
        if isinstance(node, Tag) and (node.name or "") == "a":
            m = _anchor_marker(node, base_url, ns)
            if m is not None:
                out.append(m)
    return out


def _encode_spaces(url: str) -> str:
    """D10: percent-encode raw spaces in an emitted link/image destination.

    A raw space ends a Markdown destination in most renderers, so only the
    space is encoded; every other character is left verbatim (backlog B9).
    Applied at emit time in :func:`_rewrite_url`, the single choke point for
    link and image destinations.
    """
    return url.replace(" ", "%20")


def _remap_legacy_host(url: str) -> str:
    """D11 (backlog B10): swap the dead legacy host for the live one.

    ``vaww.vrm.km.va.gov`` carries no DNS records (verified 2026-10-08:
    zero answer records from the authoritative ``va.gov`` zone while
    sibling hosts resolve), while ``www.knowva.ebenefits.va.gov`` serves
    every legacy path at the same location (36/36 ``/img/`` images and
    11/12 document URLs GET-verified live, content types checked). Only
    the host is replaced; scheme, path, query, and fragment are left
    verbatim. Applied in :func:`_rewrite_url` before :func:`_encode_spaces`
    (D10).
    """
    m = _LEGACY_HOST.match(url)
    if m is None:
        return url
    return m.group(1) + _LIVE_HOST + url[m.end() :]


def _rewrite_url(href: str | None, base_url: str, ns: str) -> str | None:
    """Resolve ``href`` to a canonical absolute URL, or ``None`` to drop it.

    ``javascript:`` hrefs are dropped (E6); fragment-only hrefs (``#frag``)
    are namespaced with ``ns`` (D6) while a bare ``#`` is left untouched;
    article URLs (``/system/ws/vNN/ss/article/{id}``) lose their query string
    because the id is already in the path; raw spaces are percent-encoded to
    ``%20`` at emit time (D10) — a raw space ends a Markdown destination in
    most renderers (backlog B9). Named-anchor markers are not encoded: their
    raw ``id``/``name`` attributes match the renderer-decoded fragment.
    Destinations on the dead legacy host ``vaww.vrm.km.va.gov`` are remapped
    to ``www.knowva.ebenefits.va.gov`` before that encoding (D11, backlog
    B10).
    """
    if href is None:
        return None
    h = href.strip()
    if h == "":
        return None
    if h.lower().startswith("javascript:"):  # E6
        return None
    if h.startswith("#"):  # D6: in-article fragment
        if h != "#" and ns != "":
            h = "#" + ns + h[1:]  # namespace the fragment
        if h == "#":
            return h  # null link: no fragment to encode
        return _encode_spaces(h)  # D10: raw space ends a destination
    if h.startswith("http://") or h.startswith("https://"):
        absolute = h
    elif h.startswith("//"):
        absolute = "https:" + h
    elif h.startswith("/"):
        absolute = base_url + h
    else:
        absolute = h  # scheme-relative oddities: keep verbatim (doc 3)
    m = _ARTICLE_URL.match(absolute)
    if m is not None:
        absolute = m.group(1) + m.group(2)
    return _encode_spaces(_remap_legacy_host(absolute))  # D11 then D10
