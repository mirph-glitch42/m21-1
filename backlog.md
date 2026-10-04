# Backlog

Deferred work, recorded 2026-10-04. Each item is written so the next
session can start without re-deriving context: problem (with measured
evidence), blast radius, the process the governing skills require, open
decisions, and acceptance criteria.

Order = user priority.

## B1. Replace eGain layout tables with standard Markdown layout (rendering fix)

**User goals (verbatim, 2026-10-04):**

1. Readable, nicely formatted output that does not change the TEXT or
   ORGANIZATION of the manual.
2. Remove layout tables in favor of standard markdown layout.
3. Un-wrap nested tables and reformat if they are not going to be
   renderable.

**Problem (measured on the current `output/` manual):**

- 26,393 lines begin with `|`; of those, **10,748** are eGain *layout*
  rows — 3-column `label | <empty spacer> | content` tables separated by
  `---` rules. In any renderer this is a wall of table borders that
  obscures the manual's real structure (the "REALLY BAD" symptom).
- Layout cells may embed **real data tables**; GFM cannot nest tables, so
  they render inline as `<br>`-joined, `\|`-escaped text. Example
  (current line 2129):
  `**Topic** \| **Topic Name** <br> 1 \| [Description of *PL 106-475*…](#1)`.
- Block fragments inside cells sometimes split into isolated paragraphs
  (e.g. the emphasized phrase *will not move* standing alone), breaking
  reading flow — a goal-1 violation the same change must fix.

**Blast radius:**

- `src/m21_crawl/mdconv.py` — `_render_table` (~L245),
  `_render_table_inline` (~L264), `_escape_pipe` (~L292), `_render_cell`,
  and the block/inline dispatch that picks which rendering a table gets.
- The **25 byte-exact TESTS cases** in
  `algorithms/html-to-markdown-section-extraction.md` (incl. case 13,
  "layout table with nested table") and their pins in `tests/test_mdconv.py`
  — they codify today's (wrong) output and must be rewritten *first*.
- Deviations D1–D4 in that document's §2.6 reference the current table
  output and need revisiting.

**Process (governing skills):** doc-first TDD — bump the algorithm doc
(version, status history, new/updated TESTS rows) **before** touching
`mdconv`; land doc + tests + code in **one atomic commit** (algorithm
records keeper G1/G9, pragmatic-programmer guard 1). `make gate` green
before commit. The `assemble`-side anchor map is unaffected unless B1
adds headings (see B3).

**Open decision (needs user):** how layout *label* rows become structure:

- **Option A — headings.** Each label row becomes a `###`/`####` heading
  under its article's `## ` heading. Pros: real navigable structure,
  anchorable, shows in the TOC. Cons: adds ~10k headings and makes slug
  collisions (B3) far more likely.
- **Option B — bold labels.** Each label row becomes a bold paragraph
  (`**label**`) followed by the content as normal blocks. Pros: zero
  anchor impact, minimal semantic change. Cons: not navigable from the
  TOC.

Either way, nested data tables are **un-wrapped into real GFM tables**
immediately after their label (goal 3) instead of inline `<br>` text.

**Acceptance criteria:**

- 0 layout rows (`| label | | content |`) remain in the regenerated
  manual; 0 inline `<br>`-table artifacts.
- Every formerly nested data table renders as a real, well-formed GFM
  table (header row + separator + data rows).
- Text and organization unchanged (goal 1): a text-level diff (Markdown
  syntax stripped) before/after shows no added/removed/reordered words.
- `make gate` green; algorithm doc + tests + `mdconv` in one commit.

## B2. Dead intra-article anchors (`#1a`, `#RM`, …) — 14,533 dead links

**Problem (measured 2026-10-04 on the current manual):** eGain's HTML
carries named anchor positions (`<a name="1a">`, `id="RM"`, …)
*mid-paragraph*; `mdconv` drops the markers but keeps the links that
point at them. Result: **14,533 of 14,538** intra-article `#fragment`
links are dead (their fragment matches no heading and no anchor exists).
Examples (current lines 2129–2138): `[38 U.S.C. 5102](#1b)`,
`[Reorganization Matrix](#RM)`, `[Introduction](#Introduction)`.

**Why deferred:** fixing it needs a **new algorithm on the converter
side**: record each named anchor's position during the block-tree walk,
then rewrite intra-article `#` links to those recorded positions (they may
land mid-paragraph, so the target is a text offset, not a heading). That
is a full doc → tests → implementation cycle under the algorithm records
keeper — not a tweak — and it is out of scope for the hyperlink task.

**Acceptance criteria (when done):** every `](#frag)` whose fragment is
not an article-heading slug resolves to a recorded anchor position (or is
rewritten to a live target); 0 dead intra-article fragments in the
regenerated manual; text and organization unchanged.

## B3. Slug-dedup robustness (anchor collisions)

**Status today (verified 2026-10-04 against the npm `github-slugger`
reference over all 2,442 live headings):** `heading_anchor` matches the
renderer's anchor for **all 442 article headings — 0 mismatches**; 600 of
the 2,442 headings get GitHub's `-1`, `-2`, … dedup suffixes.

**Why this is not structurally safe:** our anchors are computed from the
heading *text alone*. GitHub assigns slugs in document order — the first
heading to claim a slug keeps it, later duplicates get `-N`. If any body
heading with a colliding slug ever precedes an article heading, the
article heading silently gets a suffix and every link resolved to the
unsuffixed slug becomes a dead link. B1 Option A adds ~10k headings and
would make such collisions likely.

**Options:**

- **(a) renderer-equivalent walk (recommended):** compute anchors by
  scanning the final document in order with dedup, exactly like
  `github-slugger` — correct by construction for any heading set.
- **(b) invariant pin:** prove (test) that no article-heading slug
  collides with any earlier heading slug, and fail the gate if it ever
  does.

**Either way:** promote the reference-slugger check from a manual
scratchpad run to a repeatable verification (test or script) that asserts
0 anchor mismatches on the regenerated manual.

## Standing constraints (apply to all items)

- The manual's TEXT and ORGANIZATION must not change — formatting only
  (user goal 1).
- Historical/Rescinded exclusion stays as committed in
  `algorithms/historical-rescinded-exclusion.md`.
- `output/` (the assembled manual) must **not** be committed while the
  user's "do not commit the assembled manual at this time" hold stands.
- `make gate` green before every commit; Conventional Commits; algorithm
  doc and code change atomically.
