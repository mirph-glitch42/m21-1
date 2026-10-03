# Rich HTML → Markdown Block Converter (eGain Article Content Extraction)

<!-- INDEX:BEGIN format=tsv version=1 -->
id	start_line	end_line
INDEX_BLOCK	3	13
METADATA	15	36
THEORY	37	188
PSEUDOCODE	189	372
WALKTHROUGH	373	446
IMPLEMENTATION	447	548
TESTS	549	608
REFERENCES	609	624
<!-- INDEX:END -->

<!-- SECTION:METADATA -->
## 1. Metadata

| Field | Value |
|---|---|
| Name | Rich HTML → Markdown block converter for eGain article content |
| Slug | html-to-markdown-section-extraction |
| Version | 0.2.0 |
| Status | implemented |
| Author | Bionic agent (on behalf of murphyjj) |
| Created | 2026-10-02 |
| Last modified | 2026-10-03 |
| Status history | 0.1.0 (2026-10-02): initial draft; 0.2.0 (2026-10-03): implemented in src/m21_crawl/mdconv.py |
| Languages | Python 3.12 (implementation); pseudocode is language-agnostic |
| Implementation location | src/m21_crawl/mdconv.py — HtmlConversionError L53–60; _parse L62–65; convert L67–93; block context L98–161; inline context L167–241; tables L245–327; lists L329–356; normalization and URLs L359–397 (v0.2.0, 2026-10-03) |
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
  covers everything else, so no input can reach an undefined case.
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
  per element. The only context-sensitivity is *block vs inline position*,
  which is structurally determined by the parent (a cell/list-item renders
  inline; a document top level renders block) — no runtime choice.
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
BLOCKISH := {h1..h6, p, ul, ol, table, blockquote, pre, hr, div}
UNWRAP_BLOCK := {div, span, font, center}

function convert(html, base_url, article_id="") -> str:
    # Pre: html is a str (or None), base_url is an absolute http(s) URL.
    # Post: a GFM string per contract 2.1, or "" per rule 4.
    if html is None or trim(html) == "":
        return ""
    try:
        soup <- parse_html(html)            # lenient tree parse (lxml)
    except Exception as cause:
        raise HtmlConversionError(article_id, cause)
    blocks <- render_block_list(soup.contents, base_url)
    blocks <- [b for b in blocks if b != ""]
    if blocks is empty:
        return ""
    return join(blocks, "\n\n") + "\n"

# --- block context ---------------------------------------------------------
function render_block_list(children, base_url) -> list[str]:
    blocks <- []
    for child in children:
        if child is text:
            t <- normalize_text(child)
            if t != "": blocks.append(t)                # rule E11
        else if child.name in {h1..h6}:
            level <- int(child.name[1])                 # 1..6; clamp to 1..6
            blocks.append(("#" * level) + " " + render_inline_children(child, base_url))
        else if child.name == "p":
            t <- render_inline_children(child, base_url)
            if t != "": blocks.append(t)
        else if child.name in {ul, ol}:
            blocks.append(render_list(child, base_url))
        else if child.name == "table":
            blocks.append(render_table(child, base_url))
        else if child.name == "hr":
            blocks.append("---")
        else if child.name == "blockquote":
            inner <- render_block_list(child.children, base_url)
            if inner is non-empty:
                body <- join(inner, "\n\n")
                blocks.append(prefix_every_line(body, "> "))
        else if child.name == "pre":
            code <- text_content(child)                 # newlines preserved
            fence <- "```" if code does not contain "```" else "````"
            blocks.append(fence + "\n" + code + "\n" + fence)
        else if child.name in {a}:
            if has_blockish_descendant(child) or render_inline_children(child, base_url) == "":
                blocks.extend(render_block_list(child.children, base_url))  # link dropped
            else:
                url <- rewrite_url(attr(child,"href"), base_url)
                if url is not None:
                    blocks.append("[" + render_inline_children(child, base_url) + "](" + url + ")")
                else:
                    blocks.append(render_inline_children(child, base_url))
        else if child.name in UNWRAP_BLOCK:
            blocks.extend(render_block_list(child.children, base_url))      # container
        else if child is a tag (unknown or inline tag in block position):
            t <- render_inline_children(child, base_url)
            if t != "": blocks.append(t)
    return blocks

# --- inline context --------------------------------------------------------
function render_inline_children(el, base_url) -> str:
    out <- ""
    for child in el.children:
        piece <- render_inline_piece(child, base_url)
        out <- join_inline(out, piece)      # rule E8
    return out

function join_inline(left, right) -> str:
    # E8: insert exactly one space when two emphasis/code markers would
    # touch, otherwise concatenate verbatim (document order preserved).
    if left ends with any of (*, _, `, ~) and right starts with any of (*, _, `, ~):
        return left + " " + right
    return left + right

function render_inline_piece(child, base_url) -> str:
    if child is text: return normalize_text(child)
    name <- child.name
    if name in {b, strong}:      return wrap(render_inline_children(child, base_url), "**")
    if name in {i, em}:          return wrap(render_inline_children(child, base_url), "*")
    if name in {s, strike, del}: return wrap(render_inline_children(child, base_url), "~~")
    if name == "code":           return "`" + text_content(child) + "`" if text_content(child) != "" else ""
    if name == "a":
        inner <- render_inline_children(child, base_url)
        url   <- rewrite_url(attr(child, "href"), base_url)
        if url is not None:
            if inner == "": inner <- url          # E7: link with no text uses its URL
            return "[" + inner + "](" + url + ")"
        return inner                              # no usable href: plain text
    if name == "br": return " "                   # E9
    if name == "img":
        src <- attr(child, "src"); if src is None: return ""
        return "![ " ... -> "!" + "[" + attr(child,"alt") + "](" + rewrite_url(src, base_url) + ")"
    if name in {ul, ol}:                                # list in inline position (cell)
        items <- [normalize_text(render_inline_piece(li, base_url))
                  for li in all li descendants in document order]
        return join([i for i in items if i != ""], "; ")
    if name == "table": return render_table_inline(child, base_url)
    if name in {h1..h6, p, div, span, font, u, center, small, big, sup, sub, blockquote}:
        return render_inline_children(child, base_url)   # unwrap; heading level lost in cells
    if name == "hr": return " — "                         # hr in inline position
    if name == "pre": return text_content(child)
    return render_inline_children(child, base_url)        # unknown: unwrap (totality)

function wrap(inner, marker) -> str:
    return "" if inner == "" else marker + inner + marker    # E10: never empty **

# --- tables ----------------------------------------------------------------
function render_table(el, base_url) -> str:
    rows <- []
    for tr in all tr descendants in document order:
        cells <- [render_inline_children(c, base_url) for c in tr's direct td/th]
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

function render_table_inline(el, base_url) -> str:
    # Nested table (inside a cell): one escaped-pipe row per <tr>,
    # rows joined by " <br> " (GitHub renders <br> inside cells).
    parts <- []
    for tr in all tr descendants in document order:
        cells <- [c.replace("|", "\\|") for c in (render_inline_children(td, base_url)
                  for td in tr's direct td/th)]
        parts.append(join(cells, " \\| "))
    return join(parts, " <br> ")

function render_list(el, base_url) -> str:
    ordered <- el.name == "ol"
    lines <- []
    i <- 1
    for li in el's direct li children:
        marker <- (str(i) + ". ") if ordered else "- "        # E14
        inline_parts <- []; sublists <- []
        for c in li.children:
            if c is a tag and c.name in {ul, ol}: sublists.append(c)
            else: inline_parts.append(render_inline_piece(c, base_url))
        text <- join_inline_sequence(inline_parts)
        if text != "": lines.append(marker + text)
        for sl in sublists:                                   # E15: 4-space indent
            for line in render_list(sl, base_url).split("\n"):
                lines.append("    " + line)
        i <- i + 1
    return join(lines, "\n")

# --- normalization and URLs ------------------------------------------------
function normalize_text(s) -> str:
    s <- s.replace(U+00A0, " ")        # &nbsp; -> space (before collapsing)
    s <- s.replace each of (U+200B, U+FEFF, U+200E, U+200F) with ""
    s <- regex_replace(s, "[ \t\r\n\f\v]+", " ")
    return s.strip()

function rewrite_url(href, base_url) -> str | None:
    h <- trim(href); if h == "": return None
    if h starts with "javascript:" (case-insensitive): return None    # E6
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
3. Walk the top level of the tree left to right. Each node is classified:
   heading, paragraph, list, table, rule, quote, code block, link, container,
   or something else. Each class has exactly one output recipe.
4. Containers (`div`, `span`, `font`) have no recipe of their own — walk into
   their children (that is how 500 decorative spans simply disappear).
5. Everything textual passes through the normalizer: `&nbsp;` becomes a space,
   zero-width junk is deleted, and runs of whitespace become a single space.
6. Emphasis (`b`/`i`/`s`) and `code` wrap their already-rendered children in
   Markdown markers; if the child was empty, the marker is dropped entirely so
   we never emit a bare `**`.
7. Links get a URL rewrite: relative paths become absolute; `javascript:` is
   dropped (plain text); VA article URLs lose their query string so the manual
   contains stable, canonical links.
8. Tables are built row by row: the first row is the header, ragged rows are
   padded, pipes in cell text are escaped. A table *inside* a cell is rendered
   as escaped rows joined by `<br>`.
9. Lists number or dash their items; nested lists indent by four spaces.
10. All finished blocks are joined with a blank line and one trailing newline.

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
2. One `<tr>`; two direct `<td>` cells → each cell is rendered *inline*.
   - Cell 1: child `<h3>` → heading in inline position → unwrap to its text:
     `In This Section`.
   - Cell 2: children in order:
     - `<div>` → inline unwrap → `<p>`-less text:
       `This section contains the following topics:` (normalized; the source's
       surrounding newlines collapse to the single space already present).
     - inner `<table>` → `render_table_inline`: row 1 = `Topic`, `Name`;
       row 2 = `1`, `Alpha` → `Topic \| Name <br> 1 \| Alpha`.
     - Joined: `This section contains the following topics: Topic \| Name <br> 1 \| Alpha`.
3. Rows: only one row → it is the header; width 2; no body rows.
4. Output block:

   ```
   | In This Section | This section contains the following topics: Topic \| Name <br> 1 \| Alpha |
   | --- | --- |
   ```

5. `convert` appends the trailing newline. Final string is exactly the block
   above + `"\n"` (TESTS case 13 asserts byte equality).

Note what *did not* happen: the `<h3>` inside the cell did not become `###`
(GFM cells cannot hold headings — documented), the decorative `<div>`/`<td>`
borders and `style` attributes vanished, and nothing was reordered.

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
| Table with a single row | that row is the header; no body | GFM requires a header row |
| Ragged table row | padded with empty cells to the widest row (E12) | GFM rows must be uniform |
| Pipe in cell text | escaped `\|` (E13) | unescaped pipes break the table |
| Nested table in a cell | escaped rows joined by `<br>` (2.6 `render_table_inline`) | GFM has no cell tables |
| Heading inside a cell | plain inline text, level lost (documented) | GFM cells cannot hold headings |
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
| 13 | layout table with nested table | `<table><tbody><tr><td><h3>In This Section</h3></td><td><div>This section contains the following topics:</div><table><tr><th>Topic</th><th>Name</th></tr><tr><td>1</td><td>Alpha</td></tr></table></td></tr></tbody></table>` | `| In This Section | This section contains the following topics: Topic \| Name <br> 1 \| Alpha |\n| --- | --- |\n` | live-portal pattern (worked example 4.2) |
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
- Sibling document: [manual-tree-crawl](manual-tree-crawl.md) (article order
  and leaf enumeration feeding this converter).
- Live CMS samples (verified 2026-10-02): element census and the "In This
  Section" layout-table pattern used in TESTS case 13.
- algorithm-records-keeper skill, `references/use-cases/parsers-and-construction.md`
  checklist (applied in 2.5).
