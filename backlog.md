# Backlog

Deferred work, recorded 2026-10-04. Each item is written so the next
session can start without re-deriving context: problem (with measured
evidence), blast radius, the process the governing skills require, open
decisions, and acceptance criteria.

Order = user priority. Status: **B1 done** this session; **B2, B3 open**.

## B1. Replace eGain layout tables with standard Markdown layout — **DONE (2026-10-04)**

**User goals (verbatim, 2026-10-04):**

1. Readable, nicely formatted output that does not change the TEXT or
   ORGANIZATION of the manual.
2. Remove layout tables in favor of standard markdown layout.
3. Un-wrap nested tables and reformat if they are not going to be
   renderable.

**Chosen approach (user-approved direction, Option A — headings):** a
table is a *layout frame* iff it has ≥1 row and **every** row's first
cell's first significant child (whitespace-only text skipped; any other
first child — text, `th`, list — disqualifies; no container
unwrapping) is `h1`–`h6`. Each row then emits its label as a **real
heading at its native level** (text verbatim), and renders the
remaining cells' children in **block context** — so a nested *real*
data table becomes a real, well-formed GFM table (goal 3) instead of
inline `<br>`-escaped text. Detection is deliberately conservative: any
doubt falls back to the previous GFM rendering, so **text is never
dropped**.

**Implementation:** `src/m21_crawl/mdconv.py` — `_layout_heading`
(~L269), `_is_layout_frame` (~L288), `_render_layout_frame` (~L305),
branch at top of `_render_table` (~L248). Algorithm doc
`algorithms/html-to-markdown-section-extraction.md` bumped to **v0.3.0**
(D5 deviation, pseudocode, 4.1 step 8, worked example = case 13
dissolution trace, TESTS case 13 rewritten + cases 26–30). Tests
`tests/test_mdconv.py` → 30 cases + P1–P4 (seed 20261002). RED
confirmed before GREEN (cases 13/26/27/30 failed on old code; 28/29
passed because the GFM fallback is pre-existing).

**Verification (regenerated manual, 13,204,066 bytes, 0 failed articles):**

- Piped table lines: **26,393 → 18,320** (8,073 layout rows dissolved;
  the remainder are genuine data tables).
- `<br>` artifacts: **1,946 → 270**; all 270 sampled are *nested data
  tables inside real data-table cells* (the documented GFM fallback,
  goal-3 residue), **zero** frame-derived artifacts.
- **0 stolen article slugs:** all 442 article names unique; for every
  article, the first heading in document order with its base slug is the
  article's own `## {name}` H2. All 425 referenced article anchors
  resolve.
- **Month links are an improvement, not a regression:** all 93
  month-name headings are B1-promoted frame labels (each immediately
  followed by a data table), so pre-B1 there were *zero* month headings
  and `#january`/`#march`/`#april`/`#may` were 100% dead. Post-B1 those
  4 lowercase targets resolve (first heading wins). Capitalized
  fragments (`#January`, `#July`, …) remain dangling because GitHub
  slugs are lowercase — that is B2, pre-existing.

**Note for the record:** B1 detection/render *details* (all-rows rule,
native-level promotion, conservative fallback) were this session's
design on top of the user-approved Option-A direction; the direction
itself was user-approved.

**Acceptance status:** goals 1–3 met per the measurements above;
`make gate` green; algorithm doc + tests + `mdconv` land in one atomic
commit. **Remaining B1-adjacent residue = the 270 nested-in-cell data
tables**, which is the same surface B2/B3 touch.

## B2. Dead intra-article anchors (`#1a`, `#RM`, …) — **open, re-measured post-B1**

**Problem (measured 2026-10-04 on the B1-regenerated manual):** eGain's
HTML carries named anchor positions (`<a name="1a">`, `id="RM"`, …)
*mid-paragraph*; `mdconv` drops the markers but keeps the links that
point at them. Link profile now: **23,091** internal `#` links over
**705** unique targets → **425 targets / 9,957 links RESOLVED** (421
article anchors + 4 month slugs) and **280 targets / 13,134 links
dangling**. The dangling set is the true dead-anchor backlog: ~248
code-like targets (e.g. `#1b`×543, `#1a`×488, `#1c`×480, `#1`×450,
`#RM`) + ~32 word-like targets (capitalized month names, `Top`/`top`,
Roman numerals `I`–`XIV`, `Introduction`, `Overview`).

**Why the count moved from 14,533/14,538 (original B1 write-up):** that
figure pre-dated the hyperlink task (`88fb2c5`, cross-article → article
anchors) and B1 (months now live). Both converted a slice of formerly
dead links into resolved ones, so the *remaining* dead set is now 13,134
links / 280 targets. Keep B2 open.

**Why deferred:** fixing it needs a **new algorithm on the converter
side**: record each named anchor's position during the block-tree walk,
then rewrite intra-article `#` links to those recorded positions (they
may land mid-paragraph, so the target is a text offset, not a heading).
That is a full doc → tests → implementation cycle under the algorithm
records keeper — not a tweak — and it is out of scope for the hyperlink
task.

**Acceptance criteria (when done):** every `](#frag)` whose fragment is
not an article-heading slug resolves to a recorded anchor position (or
is rewritten to a live target); 0 dead intra-article fragments in the
regenerated manual; text and organization unchanged.

## B3. Slug-dedup robustness (anchor collisions) — **open, article slugs verified clean post-B1**

**Status today (verified 2026-10-04 against the npm `github-slugger`
reference over all live headings, and re-verified post-B1):**
`heading_anchor` matches the renderer's anchor for **all 442 article
headings — 0 mismatches**, and **0 article slugs are stolen** — for
every article name the first heading in document order with its base
slug is the article's own `## {name}` H2. B1 adds many body headings
(e.g. `### January` ×6, `### December` ×…), which is exactly where future
collision risk lives, but the *article* anchors (the ones the TOC and
cross-article links depend on) are confirmed intact.

**Why this is not structurally safe:** our anchors are computed from the
heading *text alone*. GitHub assigns slugs in document order — the first
heading to claim a slug keeps it, later duplicates get `-N`. If any body
heading with a colliding slug ever precedes an article heading, the
article heading silently gets a suffix and every link resolved to the
unsuffixed slug becomes a dead link. B1 has now added ~10k body
headings, so the invariant is *currently* held but no longer trivially
so — it must be enforced, not assumed.

**Options:**

- **(a) renderer-equivalent walk (recommended):** compute anchors by
  scanning the final document in order with dedup, exactly like
  `github-slugger` — correct by construction for any heading set.
- **(b) invariant pin:** prove (test) that no article-heading slug
  collides with any earlier heading slug, and fail the gate if it ever
  does.

**Either way:** promote the reference-slugger check from a manual
scratchpad run to a repeatable verification (test or script) that asserts
0 anchor mismatches on the regenerated manual. Note the case-sensitivity
split observed in B2 (lowercase month targets resolve, capitalized ones
don't) is evidence the eGain anchor scheme is its own thing, independent
of heading slugs — B2 and B3 are related but distinct work.

## Standing constraints (apply to all items)

- The manual's TEXT and ORGANIZATION must not change — formatting only
  (user goal 1).
- Historical/Rescinded exclusion stays as committed in
  `algorithms/historical-rescinded-exclusion.md`.
- `output/` (the assembled manual) must **not** be committed while the
  user's "do not commit the assembled manual at this time" hold stands.
- `make gate` green before every commit; Conventional Commits; algorithm
  doc and code change atomically.
