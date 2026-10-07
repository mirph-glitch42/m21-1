# Rich HTML → Markdown Block Converter (eGain Article Content Extraction)

<!-- INDEX:BEGIN format=tsv version=1 -->
id	start_line	end_line
INDEX_BLOCK	3	13
METADATA	15	36
THEORY	37	273
PSEUDOCODE	274	588
WALKTHROUGH	589	691
IMPLEMENTATION	692	808
TESTS	809	894
REFERENCES	895	910
<!-- INDEX:END -->

<!-- SECTION:METADATA -->
## 1. Metadata

| Field | Value |
|---|---|
| Name | Rich HTML → Markdown block converter for eGain article content |
| Slug | html-to-markdown-section-extraction |
| Version | 0.5.0 |
| Status | implemented |
| Author | Bionic agent (on behalf of murphyjj) |
| Created | 2026-10-02 |
| Last modified | 2026-10-06 |
| Status history | 0.1.0 (2026-10-02): initial draft; 0.2.0 (2026-10-03): implemented in src/m21_crawl/mdconv.py; 0.3.0 (2026-10-04): layout-frame dissolution (D5) — tables whose rows all lead with a heading dissolve into real headings + block content; TESTS case 13 rewritten, cases 26–30 added; 0.4.0 (2026-10-05): named-anchor preservation with per-article namespaces (D6) — an ``<a>`` that carries a non-empty ``id``/``name`` and no usable ``href`` is emitted as a raw-HTML marker element at its source position (hoisted to its own line before a heading), in-article ``#fragment`` links are rewritten to the matching ``art_{id}_`` namespace so the assembled manual keeps unique ids, and a layout label cell's non-heading content is no longer silently dropped; TESTS case 27 rewritten, cases 31–36 added; 0.5.0 (2026-10-06): inline-run coalescing in block context (D7) — text, inline tags, named anchors, and plain links sitting in a `div`/`span`/`font`/`center` container or at the fragment top level no longer fragment into standalone paragraphs: they join a current inline run that is flushed (joined per E8, stripped, appended if non-empty) at the next block element (`h1`–`h6`, `p`, `ul`, `ol`, `table`, `blockquote`, `pre`, `hr`) or at the end of the list, while a container holding a block element keeps the old flush-and-recurse split; TESTS cases 37–43 added |
| Languages | Python 3.12 (implementation); pseudocode is language-agnostic |
| Implementation location | src/m21_crawl/mdconv.py — HtmlConversionError L66–72; _parse L75–77; convert L80–106; block context L109–210 (inline-run coalescing D7: L112–200; _contains_block_el L203–210); inline context L213–293; tables L296–454 (layout frames D5: L320–392); lists L457–484; normalization, named anchors (D6), and URLs L487–576 (v0.5.0, 2026-10-06) |
| Time complexity | O(C) — C = characters of input HTML (single pass over the parsed tree) |
| Space complexity | O(C) — parsed tree + output string |
| Determinism | deterministic (no timestamps, no randomness, fixed BASE_URL constant) |
| Dependencies | beautifulsoup4 + lxml (lenient HTML parsing), both pinned in requirements.lock |
| Thread safety | pure function, no shared state; safe to call concurrently |
| Related documents | [manual-tree-crawl](manual-tree-crawl.md) (provides the article ordering this converter feeds) |

<!-- SECTION:THEORY -->
## 2. Theory

### 2.1 Problem definition

**Input.** One article's `content` field: an HTML *fragment* (not a full
document) produced by the eGain CMS, fetched from
`GET https://www.knowva.ebenefits.va.gov/system/ws/v11/ss/article/{articleId}?portalId=554400000001018&usertype=customer&$lang=en-US`.

Observed properties (verified on live samples, 2026-10-02; one article ~80 KB):

- Headings `h2`–`h4` (no `h1` in content; the title is a separate field).
- Heavy decorative markup: `<span style="...">`, `<div>`, `&nbsp;` — 542 spans
  in one sample article.
- **Tables, including layout tables with nested content tables** (31 tables in
  one sample; at least one nested-table case).
- `ul`/`ol`/`li` (114 `li` in the sample), `hr` (36), `em`/`strong`, `br`,
  and cross-article links:
  `<a class="eGainArticleLink" articleid="554400000181468" ...
  href="https://www.knowva.ebenefits.va.gov/system/ws/v11/ss/article/554400000181468?portalId=...">`.

**Output.** A GFM (GitHub Flavored Markdown) string.

**Contract.**

1. **Deterministic:** same input + same `base_url` ⇒ byte-identical output.
2. **Text fidelity:** no visible word is dropped or added; decorative markup
   (span/div/inline styles) is removed without altering text.
3. **Structure mapping:** each element type maps to exactly one output form
   (production tables in 2.6). Unknown elements fall back to *unwrap* (render
   their children), so the mapping is total.
4. **Empty input:** `None`, `""`, or whitespace-only ⇒ `""` (no blocks).
5. **Assembly:** output = blocks joined by `"\n\n"` + exactly one trailing
   `"\n"`; no blank lines inside blocks.
6. **Errors:** a parser-level failure raises `HtmlConversionError` (documented
   in 2.7); the *caller* (assemble step) decides how to record it.

**Forbidden.** Adding/removing words; timestamps or run-order-dependent
output; regex-based HTML parsing; reordering content.

### 2.2 Why this approach

Parse leniently into a tree (lxml via BeautifulSoup), then run a **total,
deterministic two-context (block/inline) tree walk** that constructs the
Markdown.

Rejected alternatives:

- **Regex over the HTML.** Rejected: cannot handle nested tables, malformed or
  unclosed tags, or attribute ordering; the CMS HTML is not well-formed XML.
- **html2text / markdownify libraries.** Rejected: their URL rewriting, style
  stripping, nested-table handling, and emphasis spacing are black boxes that
  change between versions; this contract (exact expected strings in TESTS)
  requires *pinned, testable rules*, and nested *layout* tables are a corner
  case those libraries do not define deterministically.
- **XSLT.** Rejected: same expressiveness as the tree walk, heavier toolchain,
  no benefit for a single-language project.

### 2.3 Correctness argument

The walk is a **total function** over the element vocabulary:

- Every element name is covered by exactly one row of the block-context table
  or the inline-context table (2.6); the fallback row (`unknown → unwrap`)
  covers everything else, so no input can reach an undefined case. The only
  structural classification beyond element names is the **layout-frame** test
  (D5), which reads the table's own rows and first cells — a pure tree
  property that adds no runtime choice.
- Traversal is pre-order over a finite tree ⇒ it terminates; each node is
  processed once per context ⇒ O(C) work.
- Text is emitted in document order (pre-order); the only insertion is a
  single space between adjacent emphasis markers (2.7 rule E8) where omitting
  it would produce ambiguous Markdown — a *disambiguation*, not a reordering.
- Determinism follows from: fixed production mapping, fixed normalization
  order (2.6), no environment reads other than the `base_url` argument, no
  randomness, no timestamps.

### 2.4 Complexity

One pass over the parsed tree; every text node and element is visited once in
the context it belongs to; string work per node is linear in its text length.
**Time: O(C)**, C = input characters (the lxml parse itself is linear in C).
**Space: O(C)** for the tree + output. The whitespace-normalization regex
`[ \t\r\n\f\v]+` is a non-overlapping literal character-class repetition —
linear, **no catastrophic backtracking** (no nested quantifiers, no
alternation).

### 2.5 Parser-class checklist

- **Formal rules:** the production tables in 2.6 (element → output), the
  `normalize_text` specification, and the `rewrite_url` specification are the
  formal rule set; the pseudocode in section 3 is the executable form.
- **Ambiguity policy:** element→output mapping is a single deterministic rule
  per element. The context-sensitivities are *block vs inline position*
  (structurally determined by the parent: a cell/list-item renders inline, a
  document top level renders block) and the *layout-frame* test (D5), which
  reads the table's own rows — both are structural tree properties, so there
  is no runtime choice.
- **Error model:** 2.7.
- **Whitespace policy:** 2.6, `normalize_text` + rule E11 (whitespace-only
  text nodes vanish in block context).
- **Depth/size limits:** recursion depth = HTML nesting depth. Input is
  server-bounded (one article; observed < 100 KB, max nesting ~6). No
  artificial cap; a pathologically nested input (~1000+ levels) would hit
  Python's recursion limit — accepted, documented risk (TESTS case 24 probes
  50 levels and must pass).
- **Idempotence:** `convert(convert(x))` is *not* claimed (Markdown is not in
  the input domain); the claimed property is **determinism**: two runs on the
  same input give identical bytes (TESTS property P1).
- **Backtracking budget:** none in the conversion (2.4).

### 2.6 Deviations

The pseudocode in section 3 is descriptive; where it contradicts the
byte-exact TESTS table (section 6 — the stated contract), the tests win.
The implementation therefore deviates as follows (all pinned by tests):

- **D1 — `normalize_text` does not strip.** Pseudocode 3 ends
  `normalize_text` with `s.strip()`. Stripping inline text pieces would
  destroy the boundary whitespace that `&nbsp;` separators provide (TESTS
  case 11: `red text` needs the space between `red` and `text` to survive
  inline rendering). The implementation therefore does **not** strip inside
  `_normalize_text`; stripping happens only at block boundaries (finished
  heading/paragraph/list-item/cell/text-node blocks).
- **D2 — `join_inline` also inserts one space before a word after
  punctuation.** Pseudocode 3's E8 inserts a space only where emphasis/code
  markers would touch. The implementation also inserts exactly one space
  when the left piece ends in a non-alphanumeric, non-marker character and
  the right piece starts with an alphanumeric (TESTS case 13: `...topics:
  Topic \| Name...` — the space after the colon is required by the expected
  output). All other joins are verbatim concatenation (TESTS case 25:
  `ab`).
- **D3 — Pipe escaping happens exactly once, in the outer table.**
  Pseudocode 3's `render_table_inline` escapes pipes *and* the outer
  `render_table` escapes again (double escape). The implementation leaves
  nested-table pipes raw inside `_render_table_inline` (cells joined with
  `" | "`, rows with `" <br> "`); the single escape pass in
  `_render_table` turns them into `\|` (TESTS case 13 expects a single
  `\|`).
- **D4 — lxml wraps fragments in `<html><body>`; the converter unwraps.**
  Section 5.5 (v0.1.0) claimed `soup.contents` on a fragment stays flat.
  In fact `BeautifulSoup(fragment, "lxml")` injects
  `<html><body>...</body></html>`; `convert` therefore renders the
  innermost `<body>`'s children (falling back to `soup.contents`) in block
  context. lxml remains the parser of record (lenient repair, predictable
  tree).
- **D5 — Layout frames are dissolved, not tabled.** eGain wraps most article
  content in *layout* tables: a `label | spacer | content` grid whose first
  cell of every row carries a heading (the section mark, e.g.
  `I.i.1.A.1.a. Description of PL 106-475`). GFM cells cannot hold headings,
  so the old rendering flattened every label to inline cell text — a wall of
  table borders that obscured the manual's structure (user goal 2, backlog
  B1) and forced nested data tables into `<br>`-joined inline rows (goal 3).
  The implementation therefore classifies each table structurally: a table is
  a **layout frame** when it has at least one row and **every** row's first
  cell *leads with* a heading (`h1`–`h6` as the first significant child;
  whitespace-only text is skipped, any other first child — text, `th`, list,
  … — disqualifies). A frame is dissolved: each row emits its label heading
  at the heading's **native level** with its text rendered verbatim, then
  renders every remaining cell's children in **block context**, so a real
  data table nested in the content column becomes a real GFM table. A table
  failing the rule renders as a GFM table exactly as before (headings in
  cells flattened to text, nested tables inline) — the conservative fallback
  guarantees no text is ever dropped. The classification is a pure structural
  read of the tree, so totality and determinism are preserved (TESTS case 13,
  cases 26–30).
- **D6 — Named anchors are preserved, namespaced per article.** eGain marks
  in-document jump targets with ``<a>`` elements that carry an ``id`` and/or
  ``name`` and **no usable ``href``** — most often wrapping a section mark's
  trailing punctuation (TESTS case 27: ``<a id="1a" name="1a">.</a>`` inside
  the label heading) or standing alone between blocks (``<a name="top"></a>``).
  The old rendering dropped the marker while keeping the ``#1a``/``#top`` links
  that point at it, leaving ~13,134 links dangling in the assembled manual
  (backlog B2). The implementation now recognizes a *named anchor* — an ``<a>``
  whose ``id`` and/or ``name`` is non-empty and whose ``href`` rewrites to
  ``None`` — and emits it as a **raw-HTML marker element**
  ``<a id="…" name="…"></a>`` carrying whichever identifier(s) are present
  (both, when both are). The marker is **namespaced** with the article prefix
  ``art_{article_id}_`` (empty when no ``article_id`` is supplied, e.g. unit
  tests): bare preservation would duplicate ids such as ``1a`` across the
  ~400 articles and ``#1a`` would silently resolve to the *first* article's
  section — worse than dead. Fragment-only ``href``s (``#top``, ``#1a`` — but
  never the ``#`` null link) are rewritten to the same namespace, so every
  in-article link targets its own article's anchor. Emission context: inside a
  heading or a layout label the marker is **hoisted** to its own block line
  immediately before the heading (inline raw HTML inside an ATX heading is the
  least renderer-portable position, so the heading's *text* — including the
  wrapped punctuation — renders verbatim and the marker sits above it); in
  paragraph / list / cell inline context the marker is emitted in place,
  immediately before the anchor's own text; a named anchor that is itself a
  top-level block emits the marker as its own block followed by its inner
  blocks. An ``<a>`` **with** a usable ``href`` is a link: the link rendering
  wins and any ``id``/``name`` is dropped (documented limitation, 5.2). The
  layout-frame label cell additionally renders any non-heading content after
  the heading (D5 rendered the heading only), so an anchor sibling of the
  label heading is preserved instead of silently dropped (goal 1: never drop
  text; TESTS case 36). The classification is a pure attribute + structural
  read of the tree, so totality and determinism are preserved (TESTS case 27,
  cases 31–36).
- **D7 — Inline runs coalesce in block context.** eGain wraps body text in
  bare ``<div>``/``<span>`` containers (and occasionally places it at the
  fragment top level), and the v0.4.0 block walk gave every child of an
  unwrapped container — and every top-level fragment child — its own block:
  a sentence with one ``<em>`` inside a ``<div>`` rendered as three
  paragraphs (≈9,851 fragmented runs in the assembled manual, backlog B4),
  violating goal 1 (do not change the manual's ORGANIZATION). User rule
  (2026-10-06): "if they would be in-line with real HTML, then they will be
  inline here as well." The block walk therefore recognizes only true block
  elements — ``h1``–``h6``, ``p``, ``ul``, ``ol``, ``table``,
  ``blockquote``, ``pre``, ``hr`` — as block delimiters. Everything else in
  block context is *inline-level*: text pieces, inline tags (``b``, ``i``,
  ``em``, ``strong``, ``s``, ``code``, ``u``, …), named anchors (D6 marker +
  inner text), and plain links (``[text](url)``) all accumulate in a current
  **inline run**. A container (``div``/``span``/``font``/``center``) that
  holds no block element contributes its children's inline pieces to the run
  (exactly as inline rendering would); a container that *does* hold a block
  element (heading, ``p``, list, table, quote, pre, hr) flushes the run and
  is recursed into, preserving the old block structure. The run is
  **flushed** at each block delimiter and at the end of the list: pieces
  joined one by one with the inline joiner (D2 spacing rules), stripped, and
  appended as one block when non-empty. Boundary whitespace in text pieces is
  preserved (D1) so ``An *initial claim* is …`` keeps its spaces. A run that
  degenerates to an isolated named anchor flushes to a marker-only line
  (TESTS cases 31/36 — byte-identical to v0.4.0 output). The classification
  is a pure structural read of the tree, so totality and determinism are
  preserved (TESTS cases 37–43).

### 2.7 Error model (summary)

| Situation | Behavior |
|---|---|
| `content` is `None` / `""` / whitespace-only | return `""` (not an error) |
| Malformed HTML (unclosed tags, stray `</div>`) | lxml repairs it; conversion proceeds (lenient parse) |
| BeautifulSoup/lxml raises (catastrophic) | raise `HtmlConversionError(article_id, cause)`; caller (assemble) substitutes the placeholder `> [content unavailable: {error}]` for that article, records the failure, and continues; the CLI exits non-zero if any article failed |
| Unrecognized element | unwrap (totality fallback) — never an error |
| `<a>` without usable `href` | render plain text (link dropped) — never an error |

<!-- SECTION:PSEUDOCODE -->
## 3. Pseudocode

```
BLOCK := {h1..h6, p, ul, ol, table, blockquote, pre, hr}    # D7: block delimiters
UNWRAP_BLOCK := {div, span, font, center}                   # containers

function convert(html, base_url, article_id="") -> str:
    # Pre: html is a str (or None), base_url is an absolute http(s) URL.
    # Post: a GFM string per contract 2.1, or "" per rule 4.
    if html is None or trim(html) == "":
        return ""
    try:
        soup <- parse_html(html)            # lenient tree parse (lxml)
    except Exception as cause:
        raise HtmlConversionError(article_id, cause)
    ns <- "art_" + article_id + "_" if article_id != "" else ""   # D6
    blocks <- render_block_list(soup.contents, base_url, ns)
    blocks <- [b for b in blocks if b != ""]
    if blocks is empty:
        return ""
    return join(blocks, "\n\n") + "\n"

# --- block context ---------------------------------------------------------
function render_block_list(children, base_url, ns) -> list[str]:
    # D7: only BLOCK elements start a new block; everything else is
    # inline-level and accumulates in `run`. The run is flushed — pieces
    # joined one by one per D2, stripped, appended if non-empty — at each
    # BLOCK element and at the end of the list.
    blocks <- []
    run <- []
    function flush():
        t <- run[0] if run is non-empty else ""
        for piece in run[1:]:
            t <- join_inline(t, piece)                  # D2, one by one
        t <- t.strip()
        run <- []
        if t != "": blocks.append(t)
    for child in children:
        if child is text:
            t <- normalize_text(child)
            if t.strip() != "":
                run.append(t)                           # D7: unstripped (D1):
                                                        # boundary whitespace
                                                        # survives to the join
        else if child.name in BLOCK:
            flush()
            if child.name in {h1..h6}:
                for m in collect_named_anchors(child, base_url, ns):  # D6: hoist
                    blocks.append(m)
                t <- render_inline_children(child, base_url, ns, anchor_mode="text")
                if t.strip() != "":
                    blocks.append(("#" * int(child.name[1])) + " " + t.strip())
            else if child.name == "p":
                t <- render_inline_children(child, base_url, ns)
                if t.strip() != "": blocks.append(t.strip())
            else if child.name in {ul, ol}:
                blocks.append(render_list(child, base_url, ns))
            else if child.name == "table":
                blocks.append(render_table(child, base_url, ns))
            else if child.name == "hr":
                blocks.append("---")
            else if child.name == "blockquote":
                inner <- render_block_list(child.children, base_url, ns)
                if inner is non-empty:
                    body <- join(inner, "\n\n")
                    blocks.append(prefix_every_line(body, "> "))
            else if child.name == "pre":
                code <- text_content(child)             # newlines preserved
                fence <- "```" if code does not contain "```" else "````"
                blocks.append(fence + "\n" + code + "\n" + fence)
        else if child.name in UNWRAP_BLOCK:             # container
            if contains_block_el(child):                # D7: real block structure
                flush()
                blocks.extend(render_block_list(child.children, base_url, ns))
            else:                                       # D7: inline-only: flatten
                for c in child.children:
                    run.append(render_inline_piece(c, base_url, ns))
        else if child.name == "a":
            m <- anchor_marker(child, base_url, ns)     # D6: None unless a named anchor
            if m is not None and contains_block_el(child):   # block-level anchor (D6)
                flush()
                blocks.append(m)                        # marker as its own block line
                blocks.extend(render_block_list(child.children, base_url, ns))
            else if m is not None:                      # D7: inline-level anchor
                run.append(m + render_inline_children(child, base_url, ns))
            else if contains_block_el(child):           # link holding blocks: drop it
                flush()
                blocks.extend(render_block_list(child.children, base_url, ns))
            else:                                       # D7: plain link in the run
                inner <- render_inline_children(child, base_url, ns).strip()
                if inner == "": pass                    # empty link, no marker: nothing
                else:
                    url <- rewrite_url(attr(child,"href"), base_url, ns)
                    if url is not None:
                        run.append("[" + inner + "](" + url + ")")   # D7: link in run
                    else:
                        run.append(inner)               # E6: plain text
        else if child is a tag (unknown or inline tag in block position):
            run.append(render_inline_piece(child, base_url, ns))    # D7: total
    flush()
    return blocks

function contains_block_el(el) -> bool:
    # D7: True if el has a descendant tag in BLOCK. Containers
    # (div/span/font/center) are deliberately NOT in BLOCK: a container
    # holding only inline content is inline-level and coalesces into the run.
    return any(d is a tag and d.name in BLOCK for d in el.descendants)

# --- inline context --------------------------------------------------------
function render_inline_children(el, base_url, ns, anchor_mode="inline") -> str:
    out <- ""
    for child in el.children:
        piece <- render_inline_piece(child, base_url, ns, anchor_mode)
        out <- join_inline(out, piece)      # rule E8
    return out

function join_inline(left, right) -> str:
    # E8: insert exactly one space when two emphasis/code markers would
    # touch, otherwise concatenate verbatim (document order preserved).
    if left ends with any of (*, _, `, ~) and right starts with any of (*, _, `, ~):
        return left + " " + right
    return left + right

function render_inline_piece(child, base_url, ns, anchor_mode="inline") -> str:
    if child is text: return normalize_text(child)
    name <- child.name
    if name in {b, strong}:      return wrap(render_inline_children(child, base_url, ns, anchor_mode), "**")
    if name in {i, em}:          return wrap(render_inline_children(child, base_url, ns, anchor_mode), "*")
    if name in {s, strike, del}: return wrap(render_inline_children(child, base_url, ns, anchor_mode), "~~")
    if name == "code":           return "`" + text_content(child) + "`" if text_content(child) != "" else ""
    if name == "a":
        inner <- render_inline_children(child, base_url, ns, anchor_mode)
        url   <- rewrite_url(attr(child, "href"), base_url, ns)
        if url is not None:                       # a link: its id/name are dropped (D6)
            if inner == "": inner <- url          # E7: link with no text uses its URL
            return "[" + inner + "](" + url + ")"
        m <- anchor_marker(child, base_url, ns)   # D6: None unless a named anchor
        if m is not None:
            if anchor_mode == "text": return inner    # marker hoisted by the caller
            return m + inner                          # inline: marker then anchor text
        return inner                              # no usable href, no id/name: plain text
    if name == "br": return " "                   # E9
    if name == "img":
        src <- attr(child, "src"); if src is None: return ""
        return "![ " ... -> "!" + "[" + attr(child,"alt") + "](" + rewrite_url(src, base_url, ns) + ")"
    if name in {ul, ol}:                                # list in inline position (cell)
        items <- [normalize_text(render_inline_piece(li, base_url, ns, anchor_mode))
                  for li in all li descendants in document order]
        return join([i for i in items if i != ""], "; ")
    if name == "table": return render_table_inline(child, base_url, ns)
    if name in {h1..h6, p, div, span, font, u, center, small, big, sup, sub, blockquote}:
        return render_inline_children(child, base_url, ns, anchor_mode)   # unwrap; heading level lost in cells
    if name == "hr": return " — "                         # hr in inline position
    if name == "pre": return text_content(child)
    return render_inline_children(child, base_url, ns, anchor_mode)        # unknown: unwrap (totality)

function wrap(inner, marker) -> str:
    return "" if inner == "" else marker + inner + marker    # E10: never empty **

# --- tables ----------------------------------------------------------------
function render_table(el, base_url, ns) -> str:
    if is_layout_frame(el):
        return render_layout_frame(el, base_url, ns)      # D5: dissolve the frame
    rows <- []
    for tr in all tr descendants in document order:
        cells <- [render_inline_children(c, base_url, ns) for c in tr's direct td/th]
        if cells is non-empty: rows.append(cells)
    if rows is empty: return ""
    width <- max(len(r) for r in rows)
    rows  <- [r + [""] * (width - len(r)) for r in rows]     # pad ragged rows (E12)
    esc   <- s.replace("|", "\\|")                            # E13
    lines <- ["| " + join(esc(c) for c in rows[0], " | ") + " |",
              "| " + join(["---"] * width, " | ") + " |"]
    for r in rows[1:]:
        lines.append("| " + join(esc(c) for c in r, " | ") + " |")
    return join(lines, "\n")

function layout_heading(cell) -> Tag | None:
    # D5: the cell's first significant child (whitespace-only text skipped);
    # returned when it is a heading, else None.
    for child in cell.children:
        if child is text:
            if trim(child) != "": return None          # text first: not a label cell
            continue
        if child is a tag:
            return child if child.name in {h1..h6} else None
        return None
    return None

function is_layout_frame(table) -> bool:
    # D5: non-empty, and EVERY row's first cell leads with a heading.
    rows <- the table's own tr rows (nearest-table rule)
    if rows is empty: return false
    for tr in rows:
        cells <- tr's direct td/th cells
        if cells is empty or layout_heading(cells[0]) is None:
            return false
    return true

function render_layout_frame(table, base_url, ns) -> str:
    # D5: dissolve — each row yields its label heading at the heading's
    # native level, then the remaining cells' children in BLOCK context
    # (nested data tables become real GFM tables; user goals 2/3).
    # D6: the label heading's named anchors are hoisted to their own lines
    # first, and the label cell's non-heading children are rendered in block
    # context after the heading (D5 used to drop them silently).
    blocks <- []
    for tr in the table's own tr rows (nearest-table rule):
        cells <- tr's direct td/th cells
        if cells is empty: continue
        heading <- layout_heading(cells[0])
        for m in collect_named_anchors(heading, base_url, ns):    # D6: hoist
            blocks.append(m)
        t <- render_inline_children(heading, base_url, ns, anchor_mode="text")
        if t != "":
            blocks.append(("#" * int(heading.name[1])) + " " + t)
        for sib in cells[0]'s children, excluding the heading:    # D6: keep
            blocks.extend([b for b in render_block_list([sib], base_url, ns)
                           if b != ""])
        for cell in cells[1:]:
            blocks.extend([b for b in render_block_list(cell.children, base_url, ns)
                           if b != ""])
    return join(blocks, "\n\n")

function render_table_inline(el, base_url, ns) -> str:
    # Nested table (inside a cell): one escaped-pipe row per <tr>,
    # rows joined by " <br> " (GitHub renders <br> inside cells).
    parts <- []
    for tr in all tr descendants in document order:
        cells <- [c.replace("|", "\\|") for c in (render_inline_children(td, base_url, ns)
                  for td in tr's direct td/th)]
        parts.append(join(cells, " \\| "))
    return join(parts, " <br> ")

function render_list(el, base_url, ns) -> str:
    ordered <- el.name == "ol"
    lines <- []
    i <- 1
    for li in el's direct li children:
        marker <- (str(i) + ". ") if ordered else "- "        # E14
        inline_parts <- []; sublists <- []
        for c in li.children:
            if c is a tag and c.name in {ul, ol}: sublists.append(c)
            else: inline_parts.append(render_inline_piece(c, base_url, ns))
        text <- join_inline_sequence(inline_parts)
        if text != "": lines.append(marker + text)
        for sl in sublists:                                   # E15: 4-space indent
            for line in render_list(sl, base_url, ns).split("\n"):
                lines.append("    " + line)
        i <- i + 1
    return join(lines, "\n")

# --- normalization and URLs ------------------------------------------------
function normalize_text(s) -> str:
    s <- s.replace(U+00A0, " ")        # &nbsp; -> space (before collapsing)
    s <- s.replace each of (U+200B, U+FEFF, U+200E, U+200F) with ""
    s <- regex_replace(s, "[ \t\r\n\f\v]+", " ")
    return s.strip()

# --- named anchors (D6) ----------------------------------------------------
function escape_attr(v) -> str:
    return v.replace('"', "&quot;")

function anchor_marker(a, base_url, ns) -> str | None:
    # D6: an <a> is a *named anchor* iff it has a non-empty id and/or name
    # AND rewrite_url(href, ...) is None (no usable link target). Emitted as
    # a self-closing marker element carrying its namespaced id/name; a link
    # (usable href) wins and any id/name on it is dropped.
    if rewrite_url(attr(a, "href"), base_url, ns) is not None: return None
    idv    <- attr(a, "id")
    namev  <- attr(a, "name")
    if (idv is None or idv == "") and (namev is None or namev == ""):
        return None
    out <- "<a"
    if idv   is not None and idv   != "":
        out <- out + " id=\"" + escape_attr(ns + idv) + "\""
    if namev is not None and namev != "":
        out <- out + " name=\"" + escape_attr(ns + namev) + "\""
    return out + "></a>"

function collect_named_anchors(el, base_url, ns) -> list[str]:
    # D6: document-order DFS; the marker for each named anchor in el's
    # subtree. Used to hoist heading/label anchors to their own lines (raw
    # HTML inline in an ATX heading is the least renderer-portable spot).
    out <- []
    for node in el's descendants in document order:
        if node is a tag and node.name == "a":
            m <- anchor_marker(node, base_url, ns)
            if m is not None: out.append(m)
    return out

function rewrite_url(href, base_url, ns) -> str | None:
    h <- trim(href); if h == "": return None
    if h starts with "javascript:" (case-insensitive): return None    # E6
    if h starts with "#":                                  # D6: in-article fragment
        if h == "#" or ns == "": return h                    # null link or no namespace
        return "#" + ns + h[1:]                              # namespace the fragment
    if h starts with "http://" or "https://":
        absolute <- h
    else if h starts with "//":
        absolute <- "https:" + h
    else if h starts with "/":
        absolute <- base_url + h
    else:
        absolute <- h                     # scheme-relative oddities: keep verbatim
    # Canonicalize article URLs: drop the query string (id is in the path).
    if absolute matches ^(https?://[^/]+/system/ws/v\d+/ss/article/)(\d+)(\?.*)?$:
        return group(1) + group(2)
    return absolute
```

Termination: pre-order walk over a finite tree; every branch terminates in a
string or a recursive call on a strictly smaller subtree.

<!-- SECTION:WALKTHROUGH -->
## 4. Walk-through (plain English)

### 4.1 Step-by-step

1. If the content is missing or blank, there is nothing to convert — return an
   empty string.
2. Parse the HTML leniently into a tree. The parser repairs whatever the CMS
   did wrong; we never see a "parse error", only a tree.
3. Walk the top level of the tree left to right. Only *block elements* —
   headings, paragraphs, lists, tables, rules, quotes, code blocks — start a
   new output block. Everything else is inline-level: it accumulates in an
   *inline run* that is flushed into a single paragraph when the next block
   element (or the end of the list) arrives (D7).
4. Containers (`div`, `span`, `font`) have no recipe of their own (that is
   how 500 decorative spans simply disappear). They split the run only when
   they actually hold a block element — then they recurse into block context.
   Otherwise their inline children are flattened straight into the current
   run, so `An <em>initial claim</em> is a …` inside a `div` stays one
   paragraph instead of fragmenting around the emphasized word (D7).
5. Text nodes, inline tags (`b`/`i`/`s`/`code`/`u`/`sub`/`sup`), anchors, and
   links all join the run; the run is flushed at block delimiters and at the
   end, so adjacent pieces merge with correct spacing (D2) rather than
   becoming standalone paragraphs (D7).
6. Everything textual passes through the normalizer: `&nbsp;` becomes a space,
   zero-width junk is deleted, and runs of whitespace become a single space.
7. Emphasis (`b`/`i`/`s`) and `code` wrap their already-rendered children in
   Markdown markers; if the child was empty, the marker is dropped entirely so
   we never emit a bare `**`.
8. Links get a URL rewrite: relative paths become absolute; `javascript:` is
   dropped (plain text); VA article URLs lose their query string so the manual
   contains stable, canonical links.
9. Named anchors — an `<a>` that carries an `id` or `name` but no usable link
   target — are preserved as self-closing marker elements (D6). Inside a
   heading or a table label the markers are hoisted onto their own line
   immediately before the heading (raw HTML inline in an ATX heading is the
   least renderer-portable spot); inside a paragraph or list item the marker
   sits inline right before the anchor text; a top-level anchor emits the
   marker on its own line followed by its block children. Every id/name is
   namespaced with the article id (`art_<id>_`) so anchors never collide
   across articles, and fragment-only links (`#1a`) are rewritten into the
   same namespace; a bare `#` (null link) is left untouched.
10. Tables are classified first: a *layout frame* — every row's first cell
   leads with a heading (eGain's `label | spacer | content` grid) — is
   dissolved into real headings at their native levels, with each remaining
   cell rendered in block context so nested data tables surface as real GFM
   tables (D5). Any other table is built row by row: the first row is the
   header, ragged rows are padded, pipes in cell text are escaped. A table
   *inside such a table's cell* is rendered as escaped rows joined by `<br>`.
11. Lists number or dash their items; nested lists indent by four spaces.
12. All finished blocks are joined with a blank line and one trailing newline.

### 4.2 Worked example

Input (synthetic, mirrors TESTS case 13 — the live portal's "In This Section"
layout pattern):

```html
<table><tbody><tr>
  <td><h3>In This Section</h3></td>
  <td>
    <div>This section contains the following topics:</div>
    <table>
      <tr><th>Topic</th><th>Name</th></tr>
      <tr><td>1</td><td>Alpha</td></tr>
    </table>
  </td>
</tr></tbody></table>
```

Trace:

1. `convert` sees one top-level child: `<table>` → `render_table`.
2. `is_layout_frame`: one row, and the first cell's first significant child is
   the `<h3>` → **layout frame** (D5) → `render_layout_frame`.
3. The row dissolves into blocks:
   - Label cell: `<h3>In This Section</h3>` → emitted at its *native* level:
     `### In This Section`.
   - Content cell, rendered in **block** context:
     - `<div>` → container unwrap → text block:
       `This section contains the following topics:`.
     - inner `<table>` → `render_table` → *not* a layout frame (its first
       cell leads with `<th>Topic`, not a heading) → a real GFM table:
       `| Topic | Name |`, `| --- | --- |`, `| 1 | Alpha |`.
4. Blocks are joined with a blank line, and `convert` appends the trailing
   newline. Final output (TESTS case 13 asserts byte equality):

   ```
   ### In This Section

   This section contains the following topics:

   | Topic | Name |
   | --- | --- |
   | 1 | Alpha |
   ```

Note what *did not* happen: the text was not touched or reordered, the
decorative `<div>`/`<td>` borders vanished without a trace, the label heading
became a real navigable heading (instead of flattened cell text), and the
nested data table became a real GFM table (instead of `<br>`-joined inline
rows).

<!-- SECTION:IMPLEMENTATION -->
## 5. Implementation notes (entry-level guide)

### 5.1 Data structures

No persistent state. Per call: a BeautifulSoup tree (lxml-backed), a `list[str]`
of finished blocks, and a growing inline string. Public surface:

```python
class HtmlConversionError(RuntimeError):
    def __init__(self, article_id: str, cause: BaseException): ...


def convert(html: str | None, *, base_url: str, article_id: str = "") -> str: ...
```

`base_url` is passed in (config supplies `https://www.knowva.ebenefits.va.gov`)
so the function stays pure and testable.

### 5.2 Edge cases and defined behavior

| Case | Defined behavior | Why |
|---|---|---|
| `None` / `""` / `"\n  \n"` | `""` | contract 4 |
| `<p>&nbsp;</p>` (whitespace-only cell) | empty block → omitted | no blank paragraphs |
| `<strong></strong>` (empty emphasis) | `""` — marker dropped (E10) | `**` alone is broken Markdown |
| `<b>a</b><i>b</i>` (no space in source) | `**a** *b*` — one space inserted (E8) | `**a****b**` parses ambiguously |
| `<a>` without `href`, or `javascript:` | plain text, link dropped (E6) | dead links are worse than text |
| `<a href="..."></a>` (empty text) | `[url](url)` (E7) | keeps the reference visible |
| `<a id="1a" name="1a"></a>` inside a heading | marker hoisted to its own line before the heading (D6; TESTS 27) | raw HTML inline in an ATX heading is the least renderer-portable spot |
| `<a id="rm"></a>` wrapping text in a paragraph | inline marker immediately before the anchor text (D6; TESTS 32) | keeps the anchor target adjacent to its label |
| `<a name="top"></a>` as a top-level block | marker on its own line, then block children (D6; TESTS 31) | block-level anchor keeps its children intact |
| `<a id="x" name="y"></a>` (id and name differ) | both attrs emitted, each namespaced (D6; TESTS 35) | preserve whatever the source declares |
| `<a id="x" href="https://…"></a>` (usable link) | link rendered, `id` dropped (D6; TESTS 33) | a live link wins over a named anchor (documented limitation) |
| `href="#"` (null link) | left as `#` (D6; TESTS 34) | bare null link, no fragment to rewrite |
| Label cell with non-heading content beside the heading | heading, then the sibling rendered in block context (D6; TESTS 36) | D5 used to drop anchor siblings silently |
| Inline-only `<div>` wrapping a run | one paragraph, container flattened (D7; TESTS 37) | real-HTML inline content stays inline (B4) |
| Emphasized run with no container at all | one paragraph (D7; TESTS 38) | the run model is container-independent |
| `<span>` inside `<div>` around a run | one paragraph, spans flattened (D7; TESTS 39) | decorative spans disappear (4.1 step 4) |
| `***independent medical opinion***` before `(IMO)` | `***` hugs the parenthesis (D7; TESTS 40) | `_wrap` strips its inner text (D1/D2) |
| `<i>Note</i>:` + link inside a `<div>` | one paragraph (D7; TESTS 41) | label and link coalesce into the run |
| `<div>` containing a real `<p>` | run flushed, then the paragraph as its own block (D7; TESTS 42) | containers holding block elements still split |
| `<a id="ref">` wrapping text inside a `<div>` | inline marker immediately before its text (D7; TESTS 43) | inline anchor joins the run (D6 inline mode) |
| Table with a single row | that row is the header; no body | GFM requires a header row |
| Ragged table row | padded with empty cells to the widest row (E12) | GFM rows must be uniform |
| Pipe in cell text | escaped `\|` (E13) | unescaped pipes break the table |
| Table whose every row's first cell leads with a heading | layout frame: dissolved into real headings (native level) + block-rendered content (D5; TESTS 13, 26–30) | eGain's `label \| spacer \| content` grid; user goals 2/3 |
| Nested table in a real table's cell | escaped rows joined by `<br>` (2.6 `render_table_inline`) | GFM has no cell tables |
| Heading elsewhere in a table cell | plain inline text, level lost (documented) | GFM cells cannot hold headings |
| List inside a cell | items joined `"; "` | compact, unambiguous |
| `<hr>` in a cell | ` — ` | visible separator, no block break |
| `<pre>` whose code contains ` ``` ` | fence of four backticks | fence must exceed content |
| Unknown element anywhere | unwrap (render children) | totality — never crashes on new CMS markup |
| 50 levels of `<div>` nesting | converts fine (TESTS case 24) | depth policy (2.5) |

### 5.3 Invariants and how to test them

| Invariant | How a test observes a violation |
|---|---|
| Determinism (contract 1) | call `convert` twice on the same input; assert byte equality (P1) |
| Exactly one trailing newline, or empty output | assert `out == "" or (out.endswith("\n") and not out.endswith("\n\n"))` on every case |
| No empty emphasis markers | scan output for `**` adjacent to `**`, `****`, `` ` ` ``; every TESTS output is asserted byte-exactly anyway |
| Every `\|` inside a table cell is escaped | assert no unescaped pipe splits a cell: re-split the GFM table and compare cell counts to the input (case 12) |
| No words lost (contract 2) | for a no-markup input, assert the output (minus newlines) contains every input word (case 1) |
| Canonical article URLs | assert no output link contains a `?` for `/system/ws/vNN/ss/article/` ids (case 4) |

### 5.4 Pitfalls and known traps

- **`&nbsp;` is U+00A0, not ASCII space.** Some regexes/treatments skip it;
  `normalize_text` replaces it *before* collapsing. Forgetting this leaves
  visible gaps and fails byte-exact tests (case 11).
- **BeautifulSoup + lxml lowercases tag names and drops some attributes**;
  that is *good* (canonical tree), but code must read `el.name` (a `str` or
  `None`), never rely on original case, and must treat `el.attrs` as a plain
  dict (multi-valued attrs become strings — fine here).
- **`el.children` includes `NavigableString`s.** Every loop over children must
  branch on `isinstance(child, NavigableString)` first (the pseudocode does).
- **`find_all("li")` is recursive.** For lists use *direct* children for items
  (else nested items double-render); for cells use *direct* `td`/`th`.
- **Do not add spaces around emphasis "for readability"** (e.g. `** a **`) —
  GFM requires the markers to hug their content, and byte-exact tests pin it.
- **`<br>` inside generated GFM table cells** is a literal `<br>` in the
  output string — that is intentional (GitHub renders it); do not "clean" it.
- **Regex discipline:** the only conversion regexes are
  `[ \t\r\n\f\v]+` (linear) and the article-URL matcher (fixed shape). Do not
  introduce nested-quantifier patterns (catastrophic backtracking, 2.5).
- **Do not sort or dedupe anything** in this module — ordering is inherited
  from the tree walk and the tree crawl (sibling document).

### 5.5 Language notes

```python
from bs4 import BeautifulSoup, NavigableString, Tag


def convert(html, *, base_url, article_id=""):
    ...
    soup = BeautifulSoup(html, "lxml")
    root = soup.find("body") or soup  # lxml wraps fragments in <html><body>
    blocks = render_block_list(root.contents, base_url)
    ...
```

- **`BeautifulSoup(fragment, "lxml")` wraps fragments in
  `<html><body>...</body></html>`** (unlike the raw lxml fragment API).
  `convert` therefore renders the innermost `<body>`'s children — the
  fragment's top level — in block context (deviation D4). lxml remains the
  parser of record because its lenient repair keeps the fragment's tree
  predictable.
- `Tag.name` is the lowercased name; `Tag.attrs` is a dict; `Tag.children` is
  a generator — materialize if iterated twice.
- Keep `render_block_list` / `render_inline_*` as plain recursive functions
  over the tree (depth is server-bounded, 2.5); no class needed.
- If a standard-library shortcut exists (`html.parser`), it is rejected: it is
  stricter (raises on malformed HTML) and adds `<html><body>` wrappers — both
  violate the contract.

<!-- SECTION:TESTS -->
## 6. Test cases and sample data

All inputs are **synthetic** fragments (G11) in the shape of live CMS output;
`base_url = "https://www.knowva.ebenefits.va.gov"` for every case. Expected
outputs are **byte-exact** (they include the single trailing `"\n"` unless
shown as `""`).

| # | Name | Input (sample data) | Expected output | Why it matters |
|---|---|---|---|---|
| 1 | minimal paragraph | `<p>Hello world</p>` | `Hello world\n` | contract 2 fidelity baseline |
| 2 | heading with emphasis | `<h2>Part <strong>1</strong>: Title</h2>` | `## Part **1**: Title\n` | heading + inline mix |
| 3 | plain external link | `<p><a href="https://example.com/x">go</a></p>` | `[go](https://example.com/x)\n` | E5 basic link |
| 4 | eGain article link (absolute, with query) | `<a class="eGainArticleLink" articleid="123" href="https://www.knowva.ebenefits.va.gov/system/ws/v11/ss/article/123?portalId=999&usertype=customer">Section B</a>` | `[Section B](https://www.knowva.ebenefits.va.gov/system/ws/v11/ss/article/123)\n` | canonical URL rewrite (query dropped) |
| 5 | relative article link | `<a href="/system/ws/v11/ss/article/456?lang=en-US">X</a>` | `[X](https://www.knowva.ebenefits.va.gov/system/ws/v11/ss/article/456)\n` | base_url joining |
| 6 | 2×2 table | `<table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr></tbody></table>` | `| A | B |\n| --- | --- |\n| 1 | 2 |\n` | GFM table core |
| 7 | ragged row padding | `<table><tr><th>A</th><th>B</th><th>C</th></tr><tr><td>1</td></tr></table>` | `| A | B | C |\n| --- | --- | --- |\n| 1 |  |  |\n` | E12 padding |
| 8 | pipe escape | `<table><tr><th>K</th></tr><tr><td>a\|b</td></tr></table>` | `| K |\n| --- |\n| a\|b |\n` | E13 escaping |
| 9 | nested unordered list | `<ul><li>one<ul><li>sub</li></ul></li></ul>` | `- one\n    - sub\n` | E15 indentation |
| 10 | ordered list | `<ol><li>first</li><li>second</li></ol>` | `1. first\n2. second\n` | E14 numbering |
| 11 | span-style stripping + `&nbsp;` | `<p><span style="color: red">red</span>&nbsp;text</p>` | `red text\n` | decoration removal + NBSP |
| 12 | adjacent emphasis disambiguation | `<p><strong>a</strong><em>b</em></p>` | `**a** *b*\n` | E8 space insertion |
| 13 | layout frame with nested data table | `<table><tbody><tr><td><h3>In This Section</h3></td><td><div>This section contains the following topics:</div><table><tr><th>Topic</th><th>Name</th></tr><tr><td>1</td><td>Alpha</td></tr></table></td></tr></tbody></table>` | `### In This Section\n\nThis section contains the following topics:\n\n\| Topic \| Name \|\n\| --- \| --- \|\n\| 1 \| Alpha \|\n` | live-portal pattern (worked example 4.2); D5 dissolution + un-nested data table |
| 14 | javascript: link dropped | `<a href="javascript:void(0)">click</a>` | `click\n` | E6 |
| 15 | image with alt | `<p><img src="/img/x.png" alt="Figure 1"></p>` | `![Figure 1](https://www.knowva.ebenefits.va.gov/img/x.png)\n` | E5/E4 image rule |
| 16 | br becomes space | `<p>line one<br>line two</p>` | `line one line two\n` | E9 |
| 17 | horizontal rule | `<hr>` | `---\n` | hr block |
| 18 | blockquote | `<blockquote><p>note</p></blockquote>` | `> note\n` | quote prefix |
| 19 | list inside a cell | `<table><tr><th>K</th></tr><tr><td><ul><li>a</li><li>b</li></ul></td></tr></table>` | `| K |\n| --- |\n| a; b |\n` | list-in-inline rule |
| 20 | inline code | `<p><code>x = 1</code></p>` | `` `x = 1`\n `` | code wrap |
| 21 | pre block with fence | `<pre><code>def f():\n    return 1</code></pre>` | ` ```\ndef f():\n    return 1\n``` \n` (i.e. fence, code, fence, trailing newline) | pre rule |
| 22 | heading clamp | `<h4>Deep</h4>` | `#### Deep\n` | level mapping |
| 23 | empty/whitespace input | `""`, `"   \n  "` | `""` | contract 4 |
| 24 | nesting depth probe | 50 nested `<div>` around `<p>deep</p>` | `deep\n` | 2.5 depth policy |
| 25 | empty emphasis dropped | `<p>a<strong></strong>b</p>` | `ab\n` | E10 |
| 26 | layout frame, spacer column | `<table><tr><td><h2>Overview</h2></td><td></td><td><p>Body text</p></td></tr></table>` | `## Overview\n\nBody text\n` | D5 dissolution; the empty spacer cell contributes nothing |
| 27 | section-mark label with named anchor | `<table><tr><td><h3>I.i.1.A.1.a<a id="1a" name="1a">.</a>&nbsp;Description of PL 106-475</h3></td><td></td><td><p>Body text</p></td></tr></table>` | `<a id="1a" name="1a"></a>\n\n### I.i.1.A.1.a. Description of PL 106-475\n\nBody text\n` | D6: the anchor marker is hoisted to its own line before the heading; the anchor's `.` text + `&nbsp;` still yield the canonical `mark. Title` spacing |
| 28 | heading in a non-leading cell → GFM table | `<table><tr><th>K</th><th>Head</th></tr><tr><td><h3>Deep</h3></td><td>x</td></tr></table>` | `\| K \| Head \|\n\| --- \| --- \|\n\| Deep \| x \|\n` | the frame rule needs EVERY row to lead with a heading; otherwise GFM (level lost in cell) |
| 29 | one non-layout row → GFM fallback | `<table><tr><td><h2>Head</h2></td><td>x</td></tr><tr><td>plain</td><td>y</td></tr></table>` | `\| Head \| x \|\n\| --- \| --- \|\n\| plain \| y \|\n` | all-rows condition; a single text-led row kills the frame |
| 30 | nested layout frame dissolves recursively | `<table><tr><td><h2>Outer</h2></td><td></td><td><table><tr><td><h3>Inner</h3></td><td></td><td><p>Deep</p></td></tr></table></td></tr></table>` | `## Outer\n\n### Inner\n\nDeep\n` | block-context content cells recurse through `render_table` (D5) |
| 31 | top-level named anchor, standalone | `<p>Before</p><a name="top"></a><p>After</p>` | `Before\n\n<a name="top"></a>\n\nAfter\n` | D6 block-level anchor: marker on its own line |
| 32 | anchor wrapping text in a paragraph | `<p><a id="rm">the RM</a></p>` | `<a id="rm"></a>the RM\n` | D6 inline marker sits immediately before the anchor's own text (no space) |
| 33 | anchor with a usable link | `<p><a id="x" href="https://example.com/y">go</a></p>` | `[go](https://example.com/y)\n` | D6: a live link wins; `id` dropped (documented limitation) |
| 34 | null link `href="#"` | `<p><a href="#">top</a></p>` | `[top](#)\n` | D6: bare `#` is left untouched (not namespaced) |
| 35 | id and name differ | `<p><a id="x" name="y">label</a></p>` | `<a id="x" name="y"></a>label\n` | D6: both attrs are emitted |
| 36 | label cell anchor sibling of heading | `<table><tr><td><h3>Section</h3><a name="top"></a></td><td></td><td><p>Body</p></td></tr></table>` | `### Section\n\n<a name="top"></a>\n\nBody\n` | D6: the label cell's non-heading anchor sibling is preserved (D5 dropped it) |
| 37 | div wraps an emphasized run | `<div>An <em>initial claim</em> is a request for benefits.</div>` | `An *initial claim* is a request for benefits.\n` | D7: an inline-only container flattens into one paragraph (B4) |
| 38 | top-level emphasized run | `An <em>initial claim</em> is a request for benefits.` | `An *initial claim* is a request for benefits.\n` | D7: the run model needs no container at all |
| 39 | nested spans inside a div | `<div><span>An</span> <em>initial claim</em> <span>is a request.</span></div>` | `An *initial claim* is a request.\n` | D7: decorative spans flatten into the run |
| 40 | bold-emphasis hugging a parenthesis | `An <strong><em>independent medical opinion </em></strong>(IMO), as discussed in <a href="http://www.ecfr.gov/current/title-38/section-3.328">38 CFR 3.328</a>, is an independent assessment.` | `An ***independent medical opinion***(IMO), as discussed in [38 CFR 3.328](http://www.ecfr.gov/current/title-38/section-3.328), is an independent assessment.\n` | D7: `_wrap` strips its inner, so `***` hugs `(IMO)` |
| 41 | italic label + link inside a div | `<div><i>Note</i>: As discussed in <a href="https://example.com/x">the guidance</a>, VA Central Office reviews the claim.</div>` | `*Note*: As discussed in [the guidance](https://example.com/x), VA Central Office reviews the claim.\n` | D7: label and link coalesce into the run |
| 42 | div holding a real paragraph | `<div>An <em>initial claim</em> is a request.<p>Next block.</p></div>` | `An *initial claim* is a request.\n\nNext block.\n` | D7: a container with a block element still splits |
| 43 | named anchor inside a div run | `<div>See <a id="ref">the reference</a> for details.</div>` | `See <a id="ref"></a>the reference for details.\n` | D7: inline anchor joins the run (D6 inline mode) |

**Namespaced (article_id) group.** The cases above use `article_id=""` (unit
tests), so markers carry bare ids. A separate group calls
`convert(html, base_url=BASE_URL, article_id="123")` and asserts the
`art_123_` prefix appears both on emitted markers (`<a id="art_123_1a" ...>`)
and on rewritten fragment links (`](#art_123_1a)`), while `href="#"` stays
`#`. This is what makes the ~13,134 dead `#fragment` links resolvable in the
assembled manual (B2 acceptance: 0 dead intra-article fragments).

### 6.1 Property tests (preferred)

Seeded (fixed seed, e.g. `random.Random(20261002)`) random-structure generator
building fragments from the vocabulary above:

- **P1 (determinism):** `convert(x) == convert(x)` for every generated `x`.
- **P2 (shape):** output is `""` or ends with exactly one `"\n"`.
- **P3 (no empty markers):** output contains no substring `**` with nothing
  between a matching pair produced by the converter — operationalized: no
  `****`, no `* *`-style empties, no backtick-only `` ` ` ``. (The generator
  avoids same-type nested emphasis — alternating `strong`/`em` — because
  `**<em>` nesting legitimately yields `****` in valid GFM; the check is
  about *empty* markers, not marker adjacency in general.)
- **P4 (word preservation):** with emphasis/link markup stripped from both
  sides, the multiset of words in the output equals the multiset of words in
  the input (for generated inputs without tables — tables are covered by the
  byte-exact cases).

### 6.2 Performance acceptance

Live worst case observed: ~80 KB article. `convert` must complete in < 500 ms
per article on a laptop-class CPU (claimed, unverified; O(C) per 2.4). A
full crawl of 785 articles is network-bound, not conversion-bound.

<!-- SECTION:REFERENCES -->
## 7. References

- GitHub Flavored Markdown spec, tables and strikethrough
  (<https://github.github.com/gfm/>): header-row requirement, `\|` escaping,
  `<br>` inside cells.
- lxml HTML parser documentation (lenient tree building; canonical lowercase
  tags) — <https://lxml.de/parsing.html>.
- BeautifulSoup 4 documentation, `NavigableString` / `Tag.children`
  semantics — <https://www.crummy.com/software/BeautifulSoup/bs4/doc/>.
- Sibling document: [manual-tree-crawl](manual-tree-crawl.md) (the pre-order topic
  traversal that fixes the article order feeding this converter).
- Live CMS samples (verified 2026-10-02): element census and the "In This
  Section" layout-table pattern used in TESTS case 13.
- algorithm-records-keeper skill, `references/use-cases/parsers-and-construction.md`
  checklist (applied in 2.5).
