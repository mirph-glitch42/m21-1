# B27 render test — lists inside a box-drawing (`<pre>`) cell

Source: the D13/B20 box-drawing nested-table renderer. B25/B26 make every
in-cell list emit real HTML `<ul>/<ol>/<li>`. Inside a top-level GFM cell that
is correct (it renders a real list on every renderer). But a list inside a
**box-drawing `<pre>` cell** breaks the monospace borders: `<li>` and the
`<ul>`/`<ol>` wrappers are not monospace, so the right `│` border on each line
drifts and the table is no longer aligned.

**Fix (B27, D17):** in box-drawing context a list emits **raw text symbols**
instead of HTML — `•` (U+2022) for level 1, `◦` (U+25E6) for level 2, deeper
levels indent two more columns and alternate the symbol. **No dashes, no HTML
list tags.** Every item's text is wrapped to the box width; continuation lines
**hang-indent** to the item-text column, and each level-2 item indents **two
columns deeper** than its level-1 parent — so the `•`/`◦` symbols and the box
borders all line up. Top-level GFM cells keep the HTML lists (B25/B26).

The "real bytes" blocks below are the **actual production output** (captured by
running the implementation, not hand-drawn). The "monospace" blocks show how a
`<pre>` block renders: every `│` lands on the same column.

## Case 1 — flat list in a nested cell

Input (HTML): an outer table whose cell holds a nested table whose cell holds
`<ul><li>alpha</li><li>beta</li></ul>`.

Real bytes (`<br>` = newline inside the rendered `<pre>`):

    | Outer |
    | --- |
    | <pre>┌─────────┐<br>│ Items   │<br>├─────────┤<br>│ • alpha │<br>│ • beta  │<br>└─────────┘</pre> |

Monospace (as rendered):

    ┌─────────┐
    │ Items   │
    ├─────────┤
    │ • alpha │
    │ • beta  │
    └─────────┘

## Case 2 — nested list (level 1 + level 2)

Input (HTML): a nested-table cell holding
`<ul><li>outer1<ul><li>inner1</li><li>inner2</li></ul></li><li>outer2</li></ul>`.

The level-2 items (`◦`) indent **two columns** deeper than their level-1
parent (`•`) — the box widens to 12 columns to make room.

Real bytes:

    | Outer |
    | --- |
    | <pre>┌────────────┐<br>│ Tree       │<br>├────────────┤<br>│ • outer1   │<br>│   ◦ inner1 │<br>│   ◦ inner2 │<br>│ • outer2   │<br>└────────────┘</pre> |

Monospace — note `◦` sits two columns to the right of `•`:

    ┌────────────┐
    │ Tree       │
    ├────────────┤
    │ • outer1   │
    │   ◦ inner1 │
    │   ◦ inner2 │
    │ • outer2   │
    └────────────┘

## Case 3 — long item with hanging indent

Input (HTML): a nested-table cell holding one long list item and one short
item.

The wrapped continuation lines (`address …`, `before submitting`) **hang-indent**
to the item-text column (two past the `•`), and every `│` border stays on the
same column.

Real bytes:

    | Outer |
    | --- |
    | <pre>┌────────────────────────────────────────────────┐<br>│ Action                                         │<br>├────────────────────────────────────────────────┤<br>│ • Enter the representative name and verify the │<br>│   address against the OGC accreditation list   │<br>│   before submitting                            │<br>│ • short                                        │<br>└────────────────────────────────────────────────┘</pre> |

Monospace — the wrapped lines hang under the item text, not under the `•`:

    ┌────────────────────────────────────────────────┐
    │ Action                                         │
    ├────────────────────────────────────────────────┤
    │ • Enter the representative name and verify the │
    │   address against the OGC accreditation list   │
    │   before submitting                            │
    │ • short                                        │
    └────────────────────────────────────────────────┘

---

**Implementation:** `pre_ctx` is threaded through `_render_inline_piece` →
`_render_cell`; the box renderer (`_render_table_inline`) calls `_render_cell`
with `pre_ctx=True`. `_render_list_inline` takes `pre_ctx` and, when true,
delegates to `_render_list_raw`, which emits `•`/`◦` by level parity, wraps
each item to the box width, and hanging-indents continuation lines to the
item-text column. The top-level GFM `_render_table` still uses the default
`pre_ctx=False`, so real GFM cells keep the HTML lists from B25/B26.

**Why the indent survives:** `_render_list_raw` pre-wraps each line to the box
width with the correct leading whitespace already in place. `_wrap_cell`
returns a line that already fits the box width **verbatim**, so when
`_cell_lines` splits the cell on `<br>` and re-wraps each piece, the leading
indent is preserved (a fit-width line is not re-tokenized and rejoined, which
is what used to strip it). That is the fix for the "flush with the left
border" bug — the level-2 indent and the hanging indent now render.
