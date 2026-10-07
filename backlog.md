# Backlog

Deferred work, recorded 2026-10-04. Each item is written so the next
session can start without re-deriving context: problem (with measured
evidence), blast radius, the process the governing skills require, open
decisions, and acceptance criteria.

Order = user priority. Status: **B1, B2, B3, B4, B5 done**; **B6 open — new 2026-10-06, root cause verified in raw HTML; additional leak shapes recorded 2026-10-07 (2-cell frames, spacer-first order, image + nested-table bodies)**; **B7 open — new 2026-10-06, internal links in the generated TOC, design drafted**; **B8 open — new 2026-10-07, dead internal links incl. "To Top" (119 case-sensitive / 28 case-insensitive dead of 23,095)**; **B9 open — new 2026-10-07, raw spaces in link destinations (51 links + 9 images) break Markdown**; **B10 open — new 2026-10-07, broken image links (36 legacy-host `vaww.vrm.km.va.gov` URLs; live/dead census partial — local DNS outage, re-verify when network recovers)**; **B11 open — new 2026-10-07, Change Date frames → quote block (user-approved readability deviation; ~1,260 frames across 6 variants)**; **B12 open — new 2026-10-07, CI gate for `algorithms/INDEX.md` staleness**; **B13 open — new 2026-10-07, sloppy double horizontal rules (root cause verified 2026-10-07: eGain's decorative `<hr>` wrappers around every layout frame; fix = drop block-level `<hr>`) **.

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

## B2. Dead intra-article anchors (`#1a`, `#RM`, …) — **DONE (2026-10-06)**

**Completion note (2026-10-05):** Full algorithm-records-keeper cycle completed — doc bumped to v0.4.0 (D6 named-anchor preservation + per-article `art_{id}_` namespaces), 8 new/rewritten TESTS cases (case 27 + cases 31–36 + 4 namespaced-group tests), `mdconv.py` v0.4.0 (544 L, 136 tests green). `make gate` green. Committed atomically as `540581e`. **Remaining:** eGain network was down (connection refused) at completion time, so the manual could not be regenerated and the dead-fragment census (acceptance criterion: 0 dead intra-article fragments) is **pending network recovery**. Re-run `make crawl` + the census script (`scratchpads/9u/analyze_dead.py`, adapted for `art_{id}_frag` markers) once eGain is reachable.

**Census result (2026-10-06):** eGain was reachable again; `make crawl`
regenerated the manual (14,105,274 bytes, 0 failed articles, exit 0). Full
link census of the regenerated manual: **23,091** internal `#` links over
**9,897** unique fragments; **0 dead bare fragments** (all resolve to
document-order heading slugs). Namespaced `art_{id}_frag` links
cross-referenced against live eGain source HTML (106 articles fetched):
**110 dead fragments / 112 links — all Category D, i.e. the anchor does not
exist in the article's source HTML at all** (portal-context references:
`#top`×87, `#Top`×5, `#January`, `#Overview`, and 16 short numeric codes such
as `#3d`). **Zero anchors dropped by `mdconv` (Category B: 0)** and **zero
lost to the D6 live-link limitation (Category C: 0)** — the converter is
lossless on named anchors. These 112 links were already dangling pre-B2 (bare
`#top` etc. were dead then too); B2 only namespaced them.

**Census false-positive correction:** a first-pass check counting only
`<a id="…">` markers reported 168 dead `art_*` fragments / 214 links. That
overcounts: **GitHub officially supports `<a name="…">` as a `#` target**
(GitHub docs, "Basic writing and formatting syntax" → Custom anchors; see
also GitHub discussion #50962). Counting both `id` and `name` markers, **58
of those fragments are live on GitHub** (emitted name-only). True dead set =
the 110 fragments / 112 Category-D links above.

**Decision (resolved 2026-10-06):** the written acceptance — "0 dead
intra-article fragments" — is strictly unmet by the 112 source-dead links,
and no converter change can make a target exist that isn't in the source:
1. **Amend B2 acceptance** to "0 dead fragments *whose anchor exists in
   source*" (all such now live) and record the ~112 portal-anchor links as a
   known source-data limitation. *(Recommended.)*
2. **Re-target policy** (needs sign-off + full doc→tests→code cycle): rewrite
   unresolvable `#frag` links to a live target.
3. **Portability hardening** (optional, separate cycle): also emit `id=` when
   the source anchor is name-only, for renderers that honor only `id`
   (GitHub works either way).

**Closure (2026-10-06):** user approved **option 1** — the acceptance
 criterion is amended as below, and the ~112 portal-anchor links (dead in
 source, pre-existing pre-B2) are recorded as a known source-data
 limitation. B2 is **CLOSED**. Options 2/3 remain available as future work.

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

**Acceptance criteria (amended 2026-10-06, option 1):** every `](#frag)`
whose fragment is not an article-heading slug **and whose anchor exists in
the article's source** resolves to a recorded anchor position — measured:
**0 such dead fragments** (23,091 links / 9,897 fragments; converter is
lossless on named anchors per the A/B/C/D census above). The 112
portal-anchor links (`#top`/`#Top`×92, `#January`, `#Overview`, 16 numeric
codes) whose targets exist nowhere in the source are a **known source-data
limitation** (dead in the source pre-B2; no converter change can make a
target exist that isn't in the source). Text and organization unchanged.

## B3. Slug-dedup robustness (anchor collisions) — **DONE (2026-10-06)**

**Completion note (2026-10-06):** Direction = user-approved Option (a) — a
renderer-equivalent walk (github-slugger occurrence replica), not Option (b)
invariant pinning. Full algorithm-records-keeper cycle:
`algorithms/internal-link-resolution.md` → **v0.3.0** (506 L; C4 semantics
rewritten, Invariant B, §2.6 `Slugger`, pseudocode incl. the emitted-body
rule, test cases 6/9–12); registry row → 0.3.0 *implemented*. Implementation
`src/m21_crawl/assemble.py` (229 L): `Slugger` (L90–108; reuses the unchanged
`heading_anchor` base slug), `_body_heading_texts` (L111–135; fence-aware
body-heading extraction), `_emitted_body` (L165–177; error articles' bodies
are not emitted, so their headings are not counted), `assemble` final pass
(L218–229; H1 title → TOC H2 → each article's H2 + emitted body headings, in
portal order). Tests `tests/test_assemble.py` (393 L): 7 new test functions
(`test_duplicate_names_get_distinct_anchors`,
`test_slugger_dedup_sequence`,
`test_article_name_collides_with_earlier_body_heading`,
`test_fenced_code_heading_not_counted`, `test_article_named_table_of_contents`,
`test_error_article_body_headings_not_counted`,
`test_property_article_anchors_match_document_order`), 1 replaced
(`test_duplicate_names_share_first_anchor` — superseded by the C4 semantic),
1 rewritten slugger-aware (`test_all_resolved_anchors_exist_as_headings`);
full suite 136 → **142 passing**. `make gate` green; atomic commit
`201ccdc`; **CI on `201ccdce` green** (gate + SonarCloud).

**C4 semantic change (consequence of Option a, recorded in the doc):**
duplicate article names now map to their own heading's distinct `-N` slug
(2nd "General" → `general-1`), not both to the first. Test-covered.

**Acceptance status:** anchors are now assigned in document order with
occurrence-based dedup by construction, so any heading set (including the
~10k body headings B1 added) resolves correctly; the slugger-aware
anchor-existence test enforces it in the suite.

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

## B4. Inline emphasis split into standalone paragraphs (goal-1 bug) — **DONE (2026-10-07)**

**Symptom (user-reported 2026-10-04, with screenshots):** emphasized or
bold inline text inside a sentence renders as its *own paragraph* with a
blank line above and below, breaking the sentence into separate blocks.
Example, current output L2714–L2720 (`### I.i.1.A.4.i. Definition:
Initial Claim`):

    An

    *initial claim*

    is a substantially complete claim for a benefit, other than a
    supplemental claim, …

whereas the source is the single sentence
"An *initial claim* is a substantially complete claim …". This violates
goal 1 (do not change the ORGANIZATION of the manual): inline emphasis
has been promoted to block level.

**Scale (measured on the regenerated manual):** **8,779** standalone
emphasis blocks + **1,072** standalone bold blocks, each sandwiched
between non-empty text above and below — **≈9,851 fragmented inline
runs**. Other samples: `…an / *not* / intended…`, `…claims proc / *must*
/ take…`, `…for the / *Example* / : The example…`, `**References** / :
For more information…`.

**Additional evidence (verified 2026-10-06 in raw source HTML, article
554400000180507):** the `5. IMOs` section shows the same fragmentation
with a *link* mid-run. Source, verbatim (all inline inside `div > span >
span` in real HTML):

    An <strong><em>independent medical opinion </em></strong>(IMO), as
    discussed in <a href="http://www.ecfr.gov/…">38 CFR 3.328</a>, is

currently renders as **five** standalone blocks: `An` / `***independent
medical opinion***` / `(IMO), as discussed in` / `[38 CFR 3.328](…)` /
`, is`. Same shape: `*Note* / : / As discussed in / [link] / , VA Central
Office…` (source: `<div><i>Note</i>: As discussed in <a>…</a>, …</div>`).
User report 2026-10-06 (screenshot): "There are areas where new lines are
randomly inserted in the middle of words" — same root cause (inline
pieces promoted to blocks), folded into B4, not a new item.

**User rule (verbatim, 2026-10-06):** "Looking at the source, they stay
inline. Rule of thumb — if they would be in-line with real HTML, then they
will be inline here as well."

**Root cause (reproduced + confirmed 2026-10-04):** `_render_block_list`
treats **every child** of an unwrapped container (`_UNWRAP_BLOCK` =
`div`/`span`/`font`/`center`) — and every top-level fragment child — as
an independent block. A bare text node becomes one block; an inline tag
(`em`, `span`, …) becomes another. Reproduction:

- `<p>An <em>initial claim</em> is a …</p>` → **1 block** (correct).
- `<div>An <em>initial claim</em> is a …</div>` → **3 blocks** (bug).
- `<div><span>An</span> <em>initial claim</em> <span>is a …</span></div>`
  → **3 blocks** (bug).
- top-level `An <em>initial claim</em> is a …` → **3 blocks** (bug).

eGain mixes both structures (body text in `<p>` *and* in bare `<div>`),
so the damage is widespread. `<p>`-wrapped content is unaffected; content
sitting directly in a `div`/`span`/top-level is fragmented.

**Blast radius:** the block dispatcher `_render_block_list` (~L101) and
every block path that unwraps containers — including
`_render_layout_frame` (B1) and `blockquote` rendering (both call
`_render_block_list`). A fix therefore interacts with B1's output and
must re-verify it. **Test impact (verified 2026-10-06):** no existing
TESTS case encodes the fragmented output — all 36 doc cases + namespaced
group + P1–P4 were read; cases 31/36 traced through the finalized design
→ byte-identical output. No rewrites needed — additions only.

**Required process (governing skills):** full algorithm-records-keeper
cycle — doc-first (new rule, e.g. "inline-run coalescing in block
context" + a TESTS row), RED tests, then code, `make gate` green, one
atomic commit. Not a tweak.

**Fix direction — signed off 2026-10-06 (user rule of thumb above);
design finalized in-session as rule **D7 (inline-run coalescing in block
context)**:**

1. **Block delimiters:** `h1`–`h6`, `p`, `ul`, `ol`, `table`,
   `blockquote`, `pre`, `hr` only. Everything else in block context is
   inline-level and joins the current inline run.
2. **Containers** (`div`/`span`/`font`/`center`, i.e. `_UNWRAP_BLOCK`):
   if they contain **no block-level descendant** → flatten their children
   into the current inline run; if they contain a block-level tag → flush
   the run, then recurse (current behavior).
3. **Links:** a named anchor (id/name, no usable href) is **inline-level**
   — joins the run and renders `marker + inner`; a run that degenerates to
   an isolated anchor yields a marker-only line, which reproduces shipped
   case 31/36 output exactly. A plain link (usable href, no blockish
   descendant) joins the run as `[text](url)`. A link with blockish
   descendants → flush + unwrap (drop URL), current behavior.
4. **Flush:** join the run's pieces with `_join_inline` (E8 spacing),
   strip, append only if non-empty.

The original open sub-question — *resolved by the rule itself*: a lone
emphasis that is a complete label (e.g. standalone `**References**`) joins
its neighbours whenever the source keeps it inline; the user rule leaves
no exception for it.

**Acceptance criteria:** the L2714 example and the IMOs `An …
independent medical opinion … (IMO), as discussed in 38 CFR 3.328, is`
sentence each render as one line; the count of emphasis/bold blocks
sandwiched between non-empty text above and below drops from ≈9,851 to
~0 (or to a small, enumerated set of genuinely standalone labels); text
and organization unchanged; existing TESTS cases verified unaffected
(2026-10-06: none encode the fragmentation — additions only); `make
gate` green; doc + tests + code in one commit.

**Closeout (2026-10-07):** implemented as rule **D7** in
`algorithms/html-to-markdown-section-extraction.md` (v0.4.0 →
**v0.5.0**, registry row updated), tests 37–43 added, `make gate`
green, commit **`16e5795`** `feat(mdconv): coalesce inline runs in
block context (B4/D7)` — doc + tests + code + registry in one atomic
commit; pushed to `main` 2026-10-07; **CI run 37570984268 (run #10),
`head_sha` `16e579556f8ac53461001c9e53d2f2f20316ddde`, conclusion
success** (<https://github.com/mirph-glitch42/m21-1/actions/runs/37570984268>).
`make crawl` re-ran clean (0 failed articles; output 14,104,764 bytes).
Acceptance verified on the regenerated manual:
- fragmentation ≈9,851 → **24** standalone emphasis-only lines — all 24
  are legitimate whole-paragraph italics (letter templates), i.e. the
  "small, enumerated set of genuinely standalone labels" the acceptance
  allows; one is `*T* *his letter…*` where the **source** splits the
  word — faithful, do not "fix";
- IMOs sentence now renders as one clean paragraph: `An ***independent
  medical opinion***(IMO), as discussed in [38 CFR 3.328](http://www.
  ecfr.gov/…), is`, then the proper nested list — exactly the
  acceptance example;
- the 2026-10-06 "new lines randomly inserted in the middle of words"
  report (folded into B4 above) is the same population — resolved by D7.

## B5. GitHub CI gate failure — **DONE (2026-10-05)**

**Problem (user-reported 2026-10-05):** the `ci` workflow on `main`
fails even though the local gate is fully green (format ✓, lint ✓,
doc-index ✓, 126 tests ✓, gitleaks staged ✓) — i.e. a
CI-environment-specific failure. User directive: **fix the CI gate
before any more pushes.**

**Root cause (confirmed):** `.github/workflows/ci.yml` is the only
place the doc-index stage is invoked *through make* (`make
doc-index-check`); the Makefile hard-wired `PY ?= .venv/bin/python`.
CI does `pip install -r requirements.lock` into the system interpreter
(Python 3.12, `ubuntu-latest`) — there is no `.venv` on the runner, so
the recipe shelled out to a nonexistent binary. Every other CI stage
invokes `ruff`/`pytest`/`gitleaks` directly, which is why they were
unaffected.

**Fix:** Makefile — `PY` now falls back to the PATH `python3` when
`.venv/bin/python` is absent:
`PY ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)`.
Safe because `scripts/build_index.py` is stdlib-only (argparse, re,
sys). Local behavior unchanged (venv present → venv python); CI uses
the interpreter holding the locked deps. Note: `setup`, `format*`,
`lint` still use `$(VENV)` — deliberately: `setup` is local-only and
CI invokes `ruff` directly.

**Verification:** `make PY=python3 doc-index-check` green; CI
simulation (repo copy **without** `.venv`, plain `python3` on PATH)
green; full `make gate` green locally; **CI run 37375552531** on
`main` (commit `1fc4458`) — **success, all steps green**, including the
previously failing `Algorithm doc index check`.

**Acceptance:** met.

## B6. Layout frames with non-heading label cells escape D5 — **open, new 2026-10-06**

**User report (verbatim, 2026-10-06, with screenshot of the `5. IMOs`
section):** "There appear to be some layout tables that were not removed.
we need a way of catching there edge cases and removing them." Screenshot:
the IMOs `Introduction` and `Change Date` rows render as GFM tables
(`| Introduction |  | This topic contains… |`, `| Change Date |  |
August 22, 2024 |`).

**Root cause (verified in raw HTML, 2026-10-06):** D5
(`_is_layout_frame` + `_layout_heading`) dissolves only tables whose
**every** row's first cell *leads with a heading* (`h1`–`h6`). eGain
emits the same `label | spacer | content` frame with the label cell in
two variants — `<h3>Introduction</h3>` (D5 dissolves; e.g. the A&A
section of article 554400000180507 renders `### Introduction` at output
L36529) **or plain text** `<div><span style="font-size: 14px"><span
style="font-family: arial, helvetica, sans-serif">Change Date</span>
</span></div>` (no heading element → `_layout_heading` returns `None` →
GFM fallback). The plain-text-label frames are the leak; single-row
frames then render as **header-only GFM tables** (the one row becomes
the header row, zero body rows).

**Verified population (assembled manual, 2026-10-06; line-based census,
authoritative — an earlier table-based census had a Python scoping bug
and is void):** 2,202 GFM tables total; **111 header-only tables**
(header + separator, no body rows): **68** are 3-cell
`label | spacer | content` frames, **1** is a 4-cell variant
(`(empty) | In This Section | spacer | content`, L232582), **1** is
5-cell, **33** are single-cell letter/notice wrappers (incl. one empty
table, L241486), **8** are 2-cell (letterheads `Department of Veterans
Affairs | Memorandum of Changes` and memo rows — **genuine content,
protected**). **Zero** multi-row tables match the all-rows-empty-middle-
cell pattern (checked every multi-row 3+-col table) — no genuine data
table is at risk. Label-cell variants observed in the leak set:

- meta labels, plain or bold in source: `Introduction`, `Change Date`,
  `**Introduction**`, `**Change Date**` (L5225, L8071/8076, L37151/37156,
  L209690, L214884, L218390/218470);
- **section marks as plain text with named anchors**: `II.i.2.B.4.b<a
  id="art_554400000174859_4b" name=…>.</a> …` (L9922, L9927, L19431),
  `I.ii.1.C.2.a<a id="art_554400000181484_2a"…>` (L6642), `II.i.2.C.6.h…`
  (L10886) — per the user's 2026-10-05 direction these marks must get
  **proper heading status** on dissolution, anchors hoisted (D6);
- content cells of several of these hold **nested genuine data tables**
  currently flattened into `<br>`-joined inline text (goal-3 residue);
  dissolving the frame in block context would surface them as real GFM
  tables (goal 3);
- protected set (must keep GFM rendering): the 2-cell letterheads/memos
  (L243770–L243823 cluster), the 4 genuine 3-col×1-row tables (rating
  codes `7101/Hypertension/10`, dental Class/Eligibility/Level), the
  577-row citation crosswalk, and all other multi-row tables.

**Additional evidence (user-reported 2026-10-07, 3 screenshots — "more
examples of missed format frames"):** the 111-table census and the
proposed discriminator above (≥3 cells, second cell spacer) **miss two
more leak shapes**:

- **2-cell `label | content` frames with plain-text section-mark
  labels:** `II.i.2.B.4.b. Determining the Date a Form Becomes
  Outdated` and `II.i.2.B.4.c. Example of Outdated Form Determination`
  — the adjacent sibling `II.i.2.B.4.d.` in the same article renders as
  a proper heading, i.e. the same frame family with mixed rendering;
- **image body that must survive dissolution:** `B.4.c`'s content cell
  holds the VA Form 21-526EZ image;
- **nested genuine table in the content cell:** `II.i.2.C.6.h. Rating
  Review of Undeliverable Third-Party Development Mail – No EP
  Pending` — a 2-cell frame whose body carries a genuine If/Then table
  currently flattened to literal-pipe inline text (`If … | Then …`);
  the sibling `C.6.i` in the same article renders correctly (heading +
  real table) — again mixed within one section;
- **spacer-first column order:** the eFolders `Introduction` frame
  (`II.ii.2.A.1`) is `spacer | label | content`, vs IMOs' `label |
  spacer | content` — the discriminator must strip empty spacers
  position-independently;
- **census impact:** the discriminator must then require exactly one
  label cell (inline-only leading content) + one content cell per row;
  the 8 protected 2-cell letterheads/memos are disambiguated by the
  label-cell test, not by cell count; re-census the full population
  post-fix.

**Source shape (verbatim, article 554400000180507):**

    <table border="0" cellpadding="0" cellspacing="0">
      <tr>
        <td style="width: 115px; vertical-align: top">
          <div><span style="font-size: 14px"><span
          style="font-family: arial , helvetica , sans-serif">
          Change Date</span></span></div>
        </td>
        <td style="height: 8px; width: 15px"></td>
        <td style="width: 516px">
          <div><span …>August 22, 2024</span></div>
        </td>
      </tr>
    </table>

Fixed pixel widths (115px / 15px / 516px) and the empty spacer cell —
styles are cosmetic; the structural signature is `label | empty spacer |
content`.

**Proposed discriminator (candidates — finalize in the B6 doc cycle; it
must not misfire on genuine data tables):** a table is a frame iff
**every** row has ≥3 cells, the **second** cell carries no visible
content (spacer), and the first cell's leading content is inline-level
only (heading or plain text/link/anchor/span — no block-level
descendant). Render on dissolution: label → **heading** when it starts
with a section mark (`I.ii.1.C.2.a.` style — user direction 2026-10-05),
named anchors hoisted first (D6) — level `h3`, matching the h3-label
variant of the same frame family (plain-text labels carry no native
level; confirm in the doc cycle); otherwise a plain text line (bold kept
when the source is bold — never fabricated). Content cells render in
**block** context (B1 behavior). Any row failing the test → the whole
table keeps the GFM fallback (D5 conservative principle; text never
dropped). The 33 single-cell tables are a separate sub-rule (a single
cell cannot carry tabular meaning; dissolve to content blocks — decide
in the doc cycle; enumerate anything kept). The discriminator MUST be
verified against the full 111-table population post-fix (residual
enumeration).

**Blast radius:** `_layout_heading` (~L280), `_is_layout_frame` (~L300),
`_render_layout_frame` (~L320), `_render_table` branch (~L248) in
`src/m21_crawl/mdconv.py`; interacts with B4 (dissolved frame content
flows through `_render_block_list`). Full algorithm-records-keeper
cycle: doc-first (D5 refinement or a new D8 rule), RED tests, `make
gate` green, one atomic commit.

**Ordering:** after B4 — B4 changes `_render_block_list`, which B6's
dissolved content uses; user directive "Proceed in order on Backlog".

**Acceptance criteria:** the 68 3-cell + 4/5-cell frame leaks dissolve
to label + content blocks (0 leaked 3+-cell header-only tables remain, or
a small enumerated set with reason); IMOs `Introduction`/`Change Date`
and the A&A equivalents render as label line/heading + content, no GFM
table; section-mark labels become real headings with live namespaced
anchors (`#art_554400000174859_4b` etc. resolve); nested genuine tables
in dissolved frames surface as real GFM tables; the protected set
(letterheads, memos, rating/dental tables, 577-row crosswalk, all
multi-row tables) is byte-identical; the single-cell decision recorded
with any kept tables enumerated; `make gate` green; doc + tests + code in
one atomic commit; text and organization unchanged.

**Extended 2026-10-07 (additional evidence above):** the 2-cell
section-mark frames (`B.4.b`/`B.4.c`/`C.6.h`) dissolve to heading +
content; the `B.4.c` image survives; the `C.6.h` nested If/Then table
surfaces as a real GFM table; the spacer-first `Introduction` frame
(eFolders) resolves; post-fix re-census with the generalized
position-independent discriminator shows 0 leaked header-only tables in
the 2-cell / spacer-first shapes (or a small enumerated residual with
reason).

## B7. TOC entries lack internal links — **open, new 2026-10-06**

**User report (verbatim, 2026-10-06):** "Add internal links to the
generated TOC at the beginning of the document."

**Current state (verified at `58c939e`):** `assemble.py` L207 renders the
TOC as a plain numbered list — `f"{i}. {a.name}"` — so all 442 entries are
inert text in every renderer. The B3 anchor map already computes each
article's final GitHub slug in document order (H1 title → TOC H2 → each
article's H2 + emitted body headings, `Slugger` replica; `anchor_by_id` at
~L223–227), but it is built *after* the document string is assembled and is
used only by the `_internalize_links` pass — the TOC lines never see it.
All 442 article names are unique (B1 verification), so every TOC entry has
exactly one unambiguous target: its own `## {name}` H2.

**Proposed change (finalize in the doc cycle):** hoist the
`anchor_by_id` computation to *before* TOC rendering (it depends only on
the deduped article list and the emitted bodies — no circularity: the TOC
itself contributes no headings to the slug walk), and render TOC entries
as `{i}. [{a.name}](#{anchor_by_id[a.id]})`. Numbering, order, and entry
text stay byte-identical — only the link wrapping is added (goal 1: no
text or organization change).

**Interaction to verify in the implementation cycle:**
`_internalize_links` runs over the final document *including* the TOC.
Confirm idempotency on already-linked TOC entries (link text matches an
article name; target already that article's own slug) — it must not
double-rewrite, drop, or otherwise mutate them.

**Algorithm doc:** `internal-link-resolution.md` (v0.3.0 → **v0.4.0**) —
TOC links are in-document section links built from the same anchor map;
extend that doc rather than create a parallel source of truth. Full
algorithm-records-keeper cycle: doc first, RED tests (TOC cases in
`tests/test_assemble.py` — note L66 currently asserts the plain, unlinked
`toc == "1. Article 1\n2. Article 2"` and must move with the change),
`make gate` green, one atomic commit (doc + tests + code + registry row).

**Blast radius:** `src/m21_crawl/assemble.py` (TOC rendering ~L207–212 +
anchor pass ~L217–228); `tests/test_assemble.py`;
`algorithms/internal-link-resolution.md` + `algorithms/INDEX.md` registry
row.

**Ordering:** after B6 — B7 is independent of B4/B6 (it does not touch
`mdconv`), but stays last by arrival order (user directive "Proceed in
order on Backlog").

**Acceptance criteria:** every TOC entry is a Markdown link whose `#`
target resolves to that article's own `## ` H2 (B3 document-order slugger
dedup context included); TOC numbering/order/text unchanged;
`_internalize_links` idempotent on the TOC; `make gate` green; doc +
tests + code + registry in one atomic commit; on the regenerated manual
all 442 TOC links verified against a document-order anchor census (0 dead
TOC links).

## B8. Dead internal links, incl. "To Top" — **open, new 2026-10-07**

**User report (verbatim, 2026-10-07):** "Some of the 'To Top' links
work (goes to the top of the article that it follows), but a lot of
them do not do anything."

**Census (assembled manual, 2026-10-07):** 23,095 internal `#` links.

- **dead, case-sensitive: 119** — of which **91 are case-variant false
  positives** (`#…_Top` vs the defined `…_top` anchors): they work on
  GitHub (case-insensitive anchor resolution) but fail case-sensitive
  local renderers — the likely source of the user's "a lot do nothing";
- **dead, case-insensitive: 28** — genuinely absent targets (e.g.
  `art_554400000176625_top`, `art_554400000173815_1e`,
  `art_554400000181468_Overview`) — source-side broken refs;
- 418 `[To Top]` links; 323 distinct `art_…_top` anchors across 434
  articles; 2 malformed `#art_554400000175201_to top` / `…_175222_to
  top` fragments (also B9).

**Root cause:** source-side broken refs plus case/space variants. B3's
`anchor_by_id` map already knows every defined anchor's canonical
spelling, so a canonicalize pass can fix all 91 in every renderer.

**Proposed fix (decide in the doc cycle):** stage 1 **canonicalize**
every internal fragment to the defined anchor's canonical spelling via
the B3 `anchor_by_id` map; stage 2 **remap** the 28 unresolved to the
target article's first emitted anchor (its `## ` H2 slug or first named
anchor); anything still unresolvable stays as-is and is enumerated.
Doc: `algorithms/internal-link-resolution.md` — coordinate with B7 so
both fold into one v0.4.0 revision of the assembly algorithm.

**Blast radius:** `src/m21_crawl/assemble.py` (`_internalize_links`
~L138, `anchor_by_id` ~L223–227), `tests/test_assemble.py`.

**Ordering:** after B7 (shared doc revision; both touch
`_internalize_links`).

**Acceptance criteria:** 0 case-variant internal links; the 28
case-insensitive-dead links remapped to a live anchor or enumerated
with reason; all 418 `To Top` links land on a live anchor in both
GitHub and a case-sensitive local renderer; post-fix re-census: 0 dead
internal links.

## B9. Raw spaces in link destinations — **open, new 2026-10-07**

**User report (verbatim, 2026-10-07):** "There appear to be links that
are malformed? Not entirely sure what I am looking at, but the table
looks wrong." — the "Topic Name" table in that screenshot is itself a
B6 leaked frame; the links-in-destination problem below is the
distinct B9 defect.

**Census (assembled manual, 2026-10-07):** 51 link destinations with
raw spaces:

- 9 internal space-anchors whose targets **exist** (only the Markdown
  is broken), e.g. `#art_554400000095621_M21-1 Guidance`;
- 2 `#…_to top` malformed fragments (also B8 stage 2);
- ~40 external URLs (vbaw.vba.va.gov `.docx`/`.pdf`/`.xlsx`, sharepoint
  links);
- plus 9 knowva `/img/` image URLs with spaces (`M21-1 structure.png`,
  `IV.iii.3.F.2.g_Step 2.PNG`).

Raw spaces break Markdown link parsing in most renderers (the link ends
at the first space).

**Proposed fix (decide in the doc cycle):** percent-encode spaces at
emit time in `_rewrite_url` (`src/m21_crawl/mdconv.py` ~L546–576 — the
single choke point for both links and images). Internal anchors:
`#art_…_M21-1%20Guidance` still resolves to the
`name="art_…_M21-1 Guidance"` attribute (fragment percent-encoding is
decoded by the renderer). External URLs: encode spaces only (leave
other characters as-is).

**Ordering:** after B8 — canonicalize first, then encode, so the B9
pass operates on already-canonical fragments.

**Blast radius:** `_rewrite_url` in `mdconv.py`; `tests/test_mdconv.py`;
no text changes (URLs are not text).

**Acceptance criteria:** 0 raw-space link/image destinations in the
regenerated manual; the 9 space-anchors resolve in both GitHub and a
case-sensitive local renderer; a sample of external space-URLs opens
correctly.

## B10. Broken image links (legacy host) — **open, new 2026-10-07**

**User report (verbatim, 2026-10-07):** "large number of broken image
links. need to verify that the links are working in online manual, and
make sure they work in Markdown." Earlier (2026-10-07): "wrong image."

**Census (assembled manual, 2026-10-07; 106 images):**

- 48 knowva `/img/` URLs — **live** (GET 200, PNG content-type); 9 of
  them have spaces → B9;
- 22 knowva `/system/ws/v11/media/image/5544/<uuid>` URLs — **live**;
- **36 `vaww.vrm.km.va.gov/img/` URLs — legacy host; these are the
  broken placeholders** visible in the user's `II.i.2.A.5.d`
  mail-table screenshot.

**Live/dead verification status: INCONCLUSIVE.** Direct GET of the 36
legacy URLs failed at DNS resolution, and the DoH control
(`cloudflare-dns.com`) also failed → local DNS outage (known flaky
network), **not** evidence the host is dead. The verdict must be
re-taken once the network recovers.

**Required verification (when network recovers):**

1. DoH (HTTPS) DNS lookup for `vaww.vrm.km.va.gov`;
2. GET each of the 36 distinct URLs with a browser-like UA — **GET, not
   HEAD** (HEAD gets 403 from the WAF even for live images);
3. for any dead URL, find the knowva equivalent and **content-verify
   before remapping** — a remap to the wrong image is worse than a
   broken one (the "wrong image" report);
4. otherwise leave the dead URLs as-is and enumerate the dead set.

**Proposed fix (decide in the doc cycle):** remap table gated on
verification, applied in `_rewrite_url` or an assemble post-pass.

**Ordering:** after B9 (B9 fixes the encodable subset first; B10
operates on verified-dead URLs only).

**Blast radius:** `_rewrite_url` in `mdconv.py` (remap table) or an
`assemble.py` post-pass; `tests/`; the verification script + results
recorded in the doc cycle.

**Acceptance criteria:** the 36 legacy-host URLs have a verified
live/dead verdict recorded; live ones render (content-verified); dead
ones remapped to a content-verified knowva equivalent or left as-is
with the dead set enumerated; 0 images render as broken placeholders
on known-live hosts.

## B11. Change Date frames → quote block (readability deviation) — **open, new 2026-10-07**

**User request (verbatim, 2026-10-07):** "Deviation for readability:
Change Date markers and the date should be in a quote block."

This is an **explicitly user-approved deviation** from goal 1 (text and
organization unchanged): the *words* of the Change Date frame remain
verbatim, but the *layout* changes — the "Change Date" marker and the
date move into a GFM quote block. Side benefit: ~1,239 spurious
"Change Date" headings (h2/h3/h5) leave the heading hierarchy/TOC.

**Population (assembled manual, 2026-10-07; pre-B6 output, 14,104,764 B):**

| Variant | Count | Origin |
| --- | --- | --- |
| `### Change Date` + date paragraph | 1,230 | D5-dissolved frame (source label is `<h3>`) |
| `##### Change Date` + date paragraph | 8 | D5-dissolved frame (source label is `<h5>`) |
| `## Change Date` + date paragraph | 1 | D5-dissolved frame (source label is `<h2>`), L142293 |
| `| Change Date |  | date |` | 12 | B6 plain-label leak (e.g. L3846) |
| `| **Change Date** |  | date |` | 9 | B6 bold plain-label leak (e.g. L37661) |
| 1 pathological `Change Date****` line | 1 | nested-bold label (D8 sub-rule case) |

Total ≈ **1,260** frames. In every observed case the content cell is a
single plain-text date (`Month D, YYYY`); no nested tables/images
observed in Change Date frames (re-verify in the B6 census).

**Requested rendering (quote block; both variants converge):**

    > **Change Date**
    > March 13, 2024

Recommended: bold marker line (preserves the visual weight the
heading/bold variants carried and matches the bold source variant;
part of the readability deviation) + date as the second quote line.
Alternative (less recommended): unbolded `> Change Date`. Decide in
the doc cycle.

**Design (decide in the B6 doc cycle — this item rides the B6 cycle to
avoid rework):**

- Detection: the label cell's normalized plain text is exactly
  `Change Date` (case-sensitive).
- **D8 T2 path (new, B6):** a `Change Date` meta-label frame renders as
  the quote block above instead of `### Change Date` + content block.
  Named-anchor hoisting (D6) is kept — emitted before the quote block.
- **D5 T1 path (existing, 1,239 frames):** when the label heading's
  normalized text is exactly `Change Date`, emit the same quote block
  instead of a heading (anchor hoisting kept). Recorded in the doc
cycle as a D5 carve-out.
- Edge case: if the content cell is not a single plain-text paragraph
  (nested table/image/multiple blocks — none observed), the marker
  quote line stands alone (`> **Change Date**`) and the content
  renders in block context after it — never drop text.
- Other meta labels (`Introduction`, `In This Section`, `Overview`)
  are **not** quote-blocked — they introduce content sections, not
  metadata; the user request names only Change Date.

**Ordering:** implemented within the B6 cycle (B6 dissolves the leaked
plain-label frames; B11 dictates their Change Date rendering + the D5
carve-out for the already-dissolved heading variants). B11 closes
when B6's closeout verifies the quote-block population below.

**Blast radius:** `_render_layout_frame` (T1 branch + T2 meta-label
branch) in `src/m21_crawl/mdconv.py`; algorithm doc (D8 sub-rule + D5
carve-out); `tests/test_mdconv.py` (case 46 expectation becomes the
quote block; add a T1 `Change Date` case).

**Acceptance criteria:** in the regenerated manual, **0**
`##/###/##### Change Date` headings and **0** `| Change Date |` table
rows; all ~1,260 Change Date frames render as quote blocks (marker +
date, words verbatim); no other frame affected (Introduction /
In This Section / Overview remain headings); `make gate` green; doc +
tests + code in one atomic commit.

## B12. CI gate for `algorithms/INDEX.md` staleness — **open, new 2026-10-07**

**User request (verbatim, 2026-10-07):** "Add CI check for Index.md staleness."

**Why (the bug this closes):** `algorithms/INDEX.md` is a hand-maintained
aggregate registry, but both `doc-index` and `doc-index-check` in the
Makefile `continue` past `*/INDEX.md`, so **no gate enforces it** — neither
the local `gate` nor CI. It silently went stale: the html-to-markdown row
read `0.5.0` while the document METADATA said `0.6.0`, and nothing caught
it. The per-document *inline* indexes are checked; the aggregate registry
is not. INDEX.md's own rules 3 and 5 already state that CI should assert
this (Version == METADATA version; one row per doc, every row resolves);
the check was simply never written.

**Check to add (per INDEX.md rules 3 and 5):** for every `algorithms/*.md`
except `INDEX.md`, assert:
1. exactly one row exists in INDEX.md (matched by slug or file link);
2. the row's `Version` equals the document METADATA `Version`;
3. the row's `File` link target exists in the repo;
4. the row's `Status` equals the METADATA `Status`.
Plus the inverse: every INDEX.md row points at an existing file (no
orphans).

**Implementation:** a small deterministic, stdlib-only script
(e.g. `scripts/check_index_registry.py`) that exits non-zero with the
offending row named on any mismatch; wire it into a new
`index-registry-check` Makefile target and add that target to `gate` and
the CI workflow, mirroring how `doc-index-check` loops `algorithms/*.md`.

**Ordering:** independent of B6–B11; small standalone cycle. Should land
**before** the B6 closeout commit so the B6 version bump (0.5.0 → 0.6.0)
is what first exercises the new gate (and the currently stale row is fixed
as part of landing it).

**Blast radius:** new `scripts/check_index_registry.py`; `Makefile`
(new target + `gate` dependency); `.github/workflows` CI job; optional
fixture test under `tests/`.

**Acceptance criteria:** `index-registry-check` fails (non-zero, naming the
offending row) when a row's Version/Status/File disagrees with METADATA, or
a doc is missing its row, or a row is orphaned; passes on the current
(fixed) registry; wired into `make gate` and CI; the stale `0.5.0` row is
fixed as part of landing this.

## B13. Sloppy double horizontal rules around dissolved frames — **open, new 2026-10-07**

**User request (verbatim, 2026-10-07):** "For Backlog: Sloppy looking
double horizontal rules." + screenshot (a heading/label flanked by two
`---` rules, e.g. `## 2. PMC Reporting Requirements` / rule / Change Date
quote block / rule) + "identify why we are getting this behavior and fix
it."

**Root cause (verified 2026-10-07 in raw eGain HTML):** eGain wraps
*every* layout frame row in decorative `<hr>` elements — one rule before
and one after — each as a pure-hr wrapper div, e.g.
`<div style="margin-left: 85pt"><div><hr/></div></div>`. `mdconv` renders
every block-level `<hr>` as a `---` line, so each dissolved frame/heading
is flanked by two rules: the "double horizontal rule." Measured evidence:

- article `554400000181484`: **29 `<hr>`, all in pure-hr wrapper divs,
  0 inside tables** (19 inside one top-level div interleaved as
  hr-frame-hr-frame…, the rest as standalone wrapper divs);
- five more articles sampled (`554400000174866` 43, `554400000173823` 15,
  `554400000175208` 15, `554400000173307` 21, `554400000071171` 52 hrs):
  **100% pure-hr wrappers, 0 inside tables, 0 mixed wrappers**;
- the B6-regenerated manual contains **12,673 standalone `---` blocks** and
  **13 visible double-rule pairs** (rule / heading-or-label / rule).

These `<hr>` elements are pure layout decoration — the same class as the
layout tables B1/B6 dissolve — not text or organization. In the eGain UI
they are thin design rules around label rows; in GFM they render as heavy
`---` rules stacked around headings, which reads as sloppy.

**Fix (D9):** in `mdconv` block context, a block-level `<hr>` renders
*nothing* (dropped as layout decoration). `<hr>` stays in the `_BLOCK`
set so it still flushes the accumulated inline run — paragraph separation
around a rule is preserved, only the rule itself is dropped. The
inline-position fallback (`" — "`) is unchanged (no corpus evidence of
`<hr>` inside table cells). TEXT and ORGANIZATION unchanged: no text is
dropped, block order is preserved; headings (from frame dissolution)
carry the section structure.

**Process:** algorithm doc `html-to-markdown-section-extraction.md` gains
the D9 rule + TESTS case(s) (hr-flanked frame → no `---`; hr between two
paragraphs → both paragraphs kept, no rule), TDD RED→GREEN, `make gate`
green, atomic commit.

**Acceptance criteria:** after `make crawl`, the manual contains **0
standalone `---` blocks** and **0 double-rule pairs**; the 12,673 → 0
reduction is entirely decorative rules (spot-check that no paragraph text
changed); new tests RED on pre-fix code and GREEN post-fix; `make gate`
green.

## Standing constraints (apply to all items)

- The manual's TEXT and ORGANIZATION must not change — formatting only
  (user goal 1).
- Historical/Rescinded exclusion stays as committed in
  `algorithms/historical-rescinded-exclusion.md`.
- `output/` (the assembled manual) must **not** be committed while the
  user's "do not commit the assembled manual at this time" hold stands.
- `make gate` green before every commit; Conventional Commits; algorithm
  doc and code change atomically.
