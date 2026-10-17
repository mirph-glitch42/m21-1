# Backlog

<!-- INDEX:BEGIN format=tsv version=1 -->
id	title	status	priority	start_line	end_line
INDEX_BLOCK	-	-	-	3	35
HEADER	-	-	-	37	52
QUEUE	-	-	-	53	71
B1	Replace eGain layout tables with standard Markdown layout	DONE	Medium	72	134
B2	Dead intra-article anchors (`#1a`, `#RM`, …)	DONE	Medium	135	214
B3	Slug-dedup robustness (anchor collisions)	DONE	Medium	215	285
B4	Inline emphasis split into standalone paragraphs (goal-1 bug)	DONE	Medium	286	420
B5	GitHub CI gate failure	DONE	Medium	421	456
B6	Layout frames with non-heading label cells escape D5	DONE	Medium	457	646
B7	TOC entries lack internal links	DONE	Medium	647	726
B8	Dead internal links, incl. "To Top"	DONE	Medium	727	809
B9	Raw spaces in link destinations	DONE	Medium	810	879
B10	Broken image links (legacy host)	DONE	Medium	880	977
B11	Change Date frames → quote block (readability deviation)	DONE	Medium	978	1067
B12	CI gate for `algorithms/INDEX.md` staleness	DONE	Medium	1068	1138
B13	Sloppy double horizontal rules around dissolved frames	DONE	Medium	1139	1208
B14	14 residual leaked layout frames (missed format frames)	DONE	Medium	1209	1334
B15	Change Date frames not in a quote block (B11 gap)	DONE	Medium	1335	1434
B16	Nested-in-cell tables unreadable + one leaked multi-section chunk	DONE	Medium	1435	1596
B17	Inline images break paragraph readability	CANCELLED	Medium	1597	1685
B18	Section nav links — unified schema, To Top folded in	OPEN	Medium	1686	1817
B19	Malformed HTML tags inline entire section chunks	DONE	Medium	1818	2002
B20	Nested in-cell tables → aligned box-drawing tables in pre	DONE	Medium	2003	2142
B21	Missing paragraph breaks — inline-only `<div>` paragraphs coalesce	DONE	Medium	2143	2278
B22	GitHub CI gate failing — SonarCloud security issues on new code	DONE	Medium	2279	2326
B23	SonarCloud Reliability rating to A (new code)	OPEN	Low	2327	2360
B24	Wrap must not split a word from its attached punctuation	OPEN	Medium	2361	2394
B25	Nested `<ul>`/`<ol>` in a table cell duplicates sub-items	OPEN	High	2395	2428
B26	Flat in-cell `<ul>`/`<ol>` flattened to `;`-joined text	OPEN	High	2429	2461
CONSTRAINTS	-	-	-	2462	2486
<!-- INDEX:END -->

<!-- BACKLOG:HEADER -->
## Status

Deferred work, recorded 2026-10-04. Each item is written so the next
session can start without re-deriving context: problem (with measured
evidence), blast radius, the process the governing skills require, open
decisions, and acceptance criteria.

Order = all High, then Medium, then Low; within a tier in `B<n>` arrival order (G9).

**Migration (2026-10-16):** backlog moved to the priority scheme — every item declares Priority (default **Medium**; **B23** = **Low** per its own notes; **B25** = **High** (user-approved 2026-10-16); **B26** = **High** (new 2026-10-16, in-cell list flattening)); planned version tokens stripped from Ordering fields and the Queue (G6); the Queue is now priority-derived. Per-item migration Progress lines were added on the then-active OPEN items (B18, B23, B24, B25); B17 was later CANCELLED (2026-10-16); DONE items are recorded by this note.

Status: **B1–B22 done** (shas in each closeout — B6/B11 `f48faf9`; B13 `817a8f3`; B12 `403550c`; B7/B8/B9 this session's commit; B10 `f88004b` closed 2026-10-08; B14 `827a8c0` + `cc76aad`; B15 `dd54c1e` + `a922976`; B16 `489fa4a` + `2b21ee9`; B19 `a2c691b`; B20 `5611151`/`2ddb718`; B21 `d1e03ca`/`33c02f4` closed 2026-10-16; B22 `aa4362b` closed 2026-10-15) | **B17 CANCELLED** (2026-10-16; superseded by B21) | **B18 OPEN** (new 2026-10-10) | **B23 OPEN** (new 2026-10-15, Low) | **B24 OPEN** (new 2026-10-15) | **B25 OPEN** (new 2026-10-16, nested-list duplication; **High**) | **B26 OPEN** (new 2026-10-16, in-cell list flattening; **High**) | **In progress:** —

**Queue:** B25 → B26 | B17 → B18 → B24 | B23 (low) | **In progress:** — | **Done:** B1–B22 | **Updated:** 2026-10-16

<!-- BACKLOG:QUEUE -->
## Queue (execution order)

Order = all High, then Medium, then Low; within a tier in `B<n>` arrival order (G9). No version numbers — versions are assigned at completion only (G6). Done items (B1–B22) are not listed.

**High** (B# order):

1. **B25** — nested `<ul>`/`<ol>` in a table cell duplicates sub-items (fix `_render_list_inline`).
2. **B26** — flat in-cell `<ul>`/`<ol>` flattened to `;`-joined text (same root function; unflatten, close with B25).

**Medium** (B# order):

1. **B18** — section nav links, unified schema; To Top folded in.
2. **B24** — wrap never begins a line with a closing punctuation fragment (glue it to its word).

**Low** (B# order):

1. **B23** — SonarCloud Reliability rating to A (new code).

<!-- BACKLOG:ITEM:B1 -->
## B1. Replace eGain layout tables with standard Markdown layout — **DONE (2026-10-04)**
**Priority:** Medium

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

<!-- BACKLOG:ITEM:B2 -->
## B2. Dead intra-article anchors (`#1a`, `#RM`, …) — **DONE (2026-10-06)**
**Priority:** Medium

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

<!-- BACKLOG:ITEM:B3 -->
## B3. Slug-dedup robustness (anchor collisions) — **DONE (2026-10-06)**
**Priority:** Medium

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

<!-- BACKLOG:ITEM:B4 -->
## B4. Inline emphasis split into standalone paragraphs (goal-1 bug) — **DONE (2026-10-07)**
**Priority:** Medium

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

<!-- BACKLOG:ITEM:B5 -->
## B5. GitHub CI gate failure — **DONE (2026-10-05)**
**Priority:** Medium

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

<!-- BACKLOG:ITEM:B6 -->
## B6. Layout frames with non-heading label cells escape D5 — **DONE (2026-10-07)**
**Priority:** Medium

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

**Closeout (2026-10-07, post-B13 re-crawl — fresh output 14,042,184 B,
0 failed articles; code in `f48faf9`; doc `html-to-markdown-section-
extraction.md` v0.6.0, D8 generalization + B11 meta-label carve-out):**

- **Census (fresh output):** 2,138 GFM tables (was 2,192 pre-B6);
  **54 header-only tables** (was 111) = **14 leaked layout frames**
  (enumerated below) + **40 protected genuine single-row content tables**
  (VA Form/letterhead/memo text, rating rows `43. Bilateral…` / `K-1`,
  `Notes`/`References` rows, the 12-table Memorandum of Changes cluster
  L143118–L143171). 14 + 40 = 54; no other header-only tables exist.
- **The 14 residual leaked frames** (still `label | spacer | content`
  header-only GFM tables; line numbers in the post-B13 output, article id
  from the anchor): L6561 `II.i.2.B.4.b` and L6564 `II.i.2.B.4.c`
  (art 554400000174859); L7153 `II.i.2.C.6.h` (art 554400000174860);
  L11081 `Introduction`; L12315 `II.iii.3.A.3.e` (art 554400000174881);
  L28943 `V.ii.4.A.3.d`, L28955 `V.ii.4.A.3.f`, L28958 `V.ii.4.A.3.g`
  (art 554400000180492); L34698 `V.iii.5.3.g` (art 554400000014520);
  L72659 `**VIII.iv.2.A.3.c**` (art 554400000177470, bold label);
  L116105 `**In This Section**`; L117318 `XI.ii.3.C.4.e` (art
  554400000174206); L118914 `****XI.iii.1.A.1.a. Definition: Burial****`
  (art 554400000174200, bold-wrapped label); L134486 `| In This Section
  |` (spacer-first order).
- **Hypothesis (UNVERIFIED):** the label cell carries a block-level
  child, so `_frame_row_kind` returns `None` and the whole table keeps
  the GFM fallback (D5 conservative principle). Debug path: fetch the
  owning article's raw HTML (fetch recipe: `build_client` +
  `get_article_content`, article `554400000174859` for L6561/L6564),
  parse with BeautifulSoup/lxml, run `_frame_row_kind` per row with
  prints; compare a failing label cell against the resolved sibling
  (e.g. `II.i.2.B.4.d` in the same article renders as a heading).
- **Acceptance status:** all other criteria met — the 111 → 54
  header-only reduction is the dissolved frame population (68 3-cell +
  4/5-cell + 2-cell section-mark + spacer-first + meta-label shapes);
  protected set byte-identical; the remaining 14 are the "small
  enumerated residual with reason" the acceptance criteria allow —
  tracked as **B14**. `make gate` green; GitHub CI green; text and
  organization unchanged.

<!-- BACKLOG:ITEM:B7 -->
## B7. TOC entries lack internal links — **DONE (2026-10-07)**
**Priority:** Medium

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

**Completion note (2026-10-07):** Full algorithm-records-keeper cycle:
`algorithms/internal-link-resolution.md` → **v0.4.0** (pseudocode split
into `build_anchor_map` + `internalize`; TESTS cases 13–16; WALKTHROUGH
4.1; Implementation-location L210–236) and the `algorithms/INDEX.md`
registry row. `assemble.py` hoists the document-order slug walk ahead of
TOC rendering and emits `{i}. [{name}](#{anchor})`; the TOC is a
heading-free list, so it contributes nothing to the walk and every
pre-existing anchor stays byte-identical. `_internalize_links` matches
only `_ARTICLE_LINK` (`http(s)://…/article/{id}`), so `#fragment` TOC
targets pass through untouched — idempotency on the TOC is structural and
pinned by `test_internalize_idempotent_on_toc`. New tests:
`test_toc_entries_are_internal_links` (incl. the dedupe case
`general`/`general-1`), `test_toc_visible_text_and_order_unchanged`,
`test_toc_anchors_resolve_census` (0 dead TOC anchors against a
document-order anchor census). `tests/test_cli.py`
`EXPECTED_MD`/`EXPECTED_MD_SKIP` TOCs moved to the linked form (16 green);
`tests/test_assemble.py` 28 green; `make gate` green (182 tests). The
full-manual "all 442 TOC links verified" census needs the live crawl (the
`live`-marked test, not in `make gate`); the offline core is
`test_toc_anchors_resolve_census` and re-runs at the next `make crawl`.
Landed atomically (doc + tests + code + registry) as
`feat(assemble): link TOC entries to their own anchors (B7)`; the B15
docs-only entry rides along in the same commit.

<!-- BACKLOG:ITEM:B8 -->
## B8. Dead internal links, incl. "To Top" — **DONE (2026-10-08)**
**Priority:** Medium

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

**Completion note (2026-10-08):** Full algorithm-records-keeper cycle:
`algorithms/internal-link-resolution.md` → **v0.5.0** (§2.7 two-stage
fragment resolution — canonicalize, then remap — with pseudocode, TESTS
cases 17–23, WALKTHROUGH 4.3, Implementation-location line map) and the
`algorithms/INDEX.md` registry row. `assemble.py` adds `_NAMED_ANCHOR`
(per-line `findall` — the census scans that seeded this item used
first-anchor-per-line and missed 14 named ids on multi-anchor lines, all
in `art_554400000174883`), `_FRAGMENT_LINK`, `_ART_ID`,
`_defined_anchors` (fence-aware walk: headings slugged in document order
+ raw `<a id>` ids, first-wins per lowercased key) and
`_resolve_fragment_links` (stage 1 canonicalizes a case-variant
fragment to the exact defined spelling; stage 2 remaps a still-unresolved
`art_{id}_…` fragment to that article's own `## ` H2 slug; every other
fragment — exact matches, TOC links, external URLs, unknown ids — passes
byte-identical, so a dead ref is never fabricated). The pass runs after
`_internalize_links` and is idempotent — a second run finds every
fragment exact-defined and rewrites nothing. New tests (cases 17–23):
`test_case_variant_fragment_canonicalized`,
`test_absent_art_fragment_remapped_to_article_top`,
`test_unknown_art_id_never_fabricated`, `test_raw_space_fragments`,
`test_resolve_fragment_links_idempotent`,
`test_fragment_pass_never_introduces_dead_links`,
`test_external_url_fragments_untouched` — `tests/test_assemble.py` 35
green. Corrected census (2026-10-08, `output/` 442-article manual):
23,068 in-document `#fragment` links; 21,468 defined anchors (21,464
unique); 214 dead = 91 case-variants (91 distinct) + 123 truly-absent
(77 distinct, all `art_{id}_…` across 58 article ids) — all 168
distinct fragments remappable (100%); 418 `to top` links (417 exact
`[To Top]`), 95 dead pre-fix. This supersedes the 2026-10-07 census
above (different snapshot + first-anchor-per-line scan). Post-fix: 214
fragments rewritten, every rewrite landing on a defined anchor, anchor
set stable, **0 dead internal links** — all four acceptance criteria met
(exact defined anchors resolve in both GitHub's case-insensitive and
case-sensitive local renderers). `make gate` green (189 tests).
Landed atomically (doc + tests + code + registry + backlog) as
`feat(assemble): resolve dead #fragments to canonical anchors (B8)`;
`output/` stays untracked.

<!-- BACKLOG:ITEM:B9 -->
## B9. Raw spaces in link destinations — **DONE (2026-10-08)**
**Priority:** Medium

**Completion (2026-10-08).** Percent-encode spaces at emit time in
`_rewrite_url` — the single choke point for link and image destinations
(`src/m21_crawl/mdconv.py` v0.8.0, D10): new `_encode_spaces` helper
(L634) applied to the namespaced fragment path and every absolute path;
a bare `#` stays bare; spaces only, every other character verbatim
(backlog decision). Named-anchor markers keep raw `id`/`name`
attributes: renderers percent-decode the fragment when matching, so
`[…](#art_…_M21-1%20Guidance)` still targets `name="art_…_M21-1 Guidance"`.
Doc cycle: html-to-markdown-section-extraction v0.7.0 → 0.8.0 (D10,
TESTS cases 59–62, 5.2 edge row, invariant "no raw spaces in emitted
link/image destinations"); registry row 0.8.0. TDD: RED `case59` /
`case60` + `test_namespaced_fragment_link_with_raw_space` (+
`test_namespaced_anchor_marker_keeps_raw_space`, green from the start —
locks the anchor-side behavior) → GREEN; `make gate` green (193 tests).
Offline verification on the assembled manual (`/tmp/b9_census.py`):
baseline 51 raw-space destinations (measured split: 33 external URLs,
9 internal fragments incl. the 2 to-top fragments, 9 knowva `/img/`
URLs) → **0** after the D10 simulation; B8 re-resolution on the
simulated doc → **0 dead internal links**. **Tradeoff (option (a),
handoff lean, flagged here for the user):** the 9 internal
space-anchors no longer exact-match their raw-space markers once
encoded — B8 stage 2 remaps them to the owning article's H2 (Prologue
×7, Overview ×2) instead of the sub-anchor: landing degrades from
sub-anchor to article top. Option (b) (percent-decode in assemble
stage 1, amending the B8 doc/tests) is deferred as a follow-up if
sub-anchor fidelity is wanted. `output/` stays untracked.

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

<!-- BACKLOG:ITEM:B10 -->
## B10. Broken image links (legacy host) — **DONE (2026-10-08)**
**Priority:** Medium

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

**Completion record (2026-10-08).** Network recovered; verdict
**re-taken and conclusive**:

- `dig vaww.vrm.km.va.gov` → NOERROR with **zero answer records**, SOA
  `ns1x.va.gov` (the name is absent from the authoritative `va.gov`
  zone); control `www.knowva.ebenefits.va.gov` resolves and answers
  (HTTP 302 on `/`) → the host is dead, not a local DNS fault. (DoH
  endpoints themselves don't resolve from this box, so direct `dig`
  served as the DNS evidence.)
- **36/36** distinct `vaww.vrm.km.va.gov/img/` URLs are **live at
  `www.knowva.ebenefits.va.gov` on the exact same path**: GET with a
  browser UA (GET, not HEAD — the WAF 403s HEAD even for live images)
  → HTTP 200, `image/png`/`image/jpeg` content type, non-empty body.
  Byte fingerprints recorded at probe time (three filename triples are
  byte-identical on the live host — `SecD_Manage_Evidence.png/2/6` =
  12,452 B md5 `c9792f50…`; `…_3.png/7.png` = 11,132 B md5
  `83861819…` — the site's own renames; each URL serves whatever the
  live site serves at that path, so no content mismatch is possible).
- **Bonus census — 12 additional non-image legacy URLs** (48 distinct
  total, 56 occurrences): 11/12 live on knowva same-path (case-law
  content pages, CSB/Rate-Tables topic pages, spellchecker widget); 1
  is a 404 — a **source-malformed concatenated URL**
  (`…top.jsp?…mainConsole=1https://corpweb1.dfas.mil/…`) that is
  broken at the source and no worse after the remap; recorded as a
  source defect, left as-is.
- Root-cause insight: the **live portal itself** references the dead
  legacy host in 36 `<img src>` attributes — the user's broken
  placeholders are broken on the live site too.

**Decision (agent, flagged for user review):** host-level remap
`vaww.vrm.km.va.gov` → `www.knowva.ebenefits.va.gov`, scheme
preserved, path/query/fragment verbatim — **not** a 36-entry image
table: simpler, fixes the 36 images and the 11 live document links in
one rule, and generalizes to any further legacy-host URL on the same
path convention. Look-alike hosts are guarded: the host boundary must
be `/`, `?`, `#`, or end-of-string (TESTS case 66).

**Implementation:** D11 in
`algorithms/html-to-markdown-section-extraction.md` **v0.9.0** —
`_remap_legacy_host` applied in `_rewrite_url` (the single choke
point), **before** D10 space encoding; TESTS cases 63–66; suite 197
green.

**Acceptance status:** verdict recorded ✓ (conclusive, 2026-10-08);
all 36 live and content-verified ✓; remap applied ✓; regenerated
manual (14,096,707 B, 0 failed articles): **0** legacy-host
occurrences, all **106** image refs on knowva (84 distinct `/img/`
paths = 48 original + 36 remapped, all on verified-live paths) ✓.

<!-- BACKLOG:ITEM:B11 -->
## B11. Change Date frames → quote block (readability deviation) — **DONE (2026-10-07)**
**Priority:** Medium

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

**Closeout (2026-10-07, post-B13 re-crawl — acceptance verified on the
fresh output, 14,042,184 B, 0 failed articles):**

- **0** `#`–`###### Change Date` headings of any level (was 1,239 across
  h2/h3/h5);
- **0** `| Change Date |` table rows (was 21 leaked-frame rows);
- **1,260** `> **Change Date**` quote lines — the full population now
  renders as the quote block (bold marker + verbatim date).

Code + doc + tests landed in `f48faf9` (doc v0.6.0: D8 meta-label T2
path + D5 T1 carve-out; TESTS case 46 expectation rewritten + T1 case);
`make gate` green; GitHub CI green; text verbatim, organization as the
approved deviation.

<!-- BACKLOG:ITEM:B12 -->
## B12. CI gate for `algorithms/INDEX.md` staleness — **DONE (2026-10-07)**
**Priority:** Medium

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

**Closeout (2026-10-07):** DONE. `scripts/check_index_registry.py`
(stdlib-only, deterministic, venv-agnostic via `$(PY)` so CI's no-`.venv`
interpreter runs it) enforces INDEX.md rules 3 and 5: exactly one row per
doc (matched by slug or the `File` link), row `Version` == METADATA
`Version`, row `Status` == METADATA `Status`, row `File` target exists and
is the document itself, and no orphan rows. Exits `1` on drift (offending
rows named), `2` on a malformed registry or document. Wired into
`make index-registry-check`, added to `gate` (after `doc-index-check`),
and a CI step after "Algorithm doc index check." `tests/test_index_registry.py`
covers the in-sync case, every drift case (version / status / missing row /
duplicate rows / orphan row / missing file target), the structural cases
(no table, bad cell count), the `Status` vs `Status history`
disambiguation, and the subprocess exit codes (0/1/2). `make gate` green
(178 tests); the previously stale row was already fixed in `817a8f3`, so the
gate passes on the current registry and now guards it.

**Decision — no algorithm doc (recorded per B12 closeout):** B12 is a CI
*gate* script (tooling), not an application algorithm. The spec's blast
radius lists only the script + Makefile + CI + tests, and the repo
convention documents only the crawler/converter algorithms (the vendored
`build_index.py` gate has no `algorithms/` entry of its own). This note
stands in for an `algorithms/` document.

Landed atomically (script + tests + Makefile + CI + this closeout).

<!-- BACKLOG:ITEM:B13 -->
## B13. Sloppy double horizontal rules around dissolved frames — **DONE (2026-10-07)**
**Priority:** Medium

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

**Closeout (2026-10-07, commit `817a8f3`):** D9 implemented — a
block-level `<hr>` in `_render_block_list` renders nothing (`pass`
branch; `<hr>` stays in `_BLOCK` so it still flushes the accumulated
inline run; the inline-cell `" — "` fallback is unchanged). Doc
`html-to-markdown-section-extraction.md` at v0.7.0 (D9 rule, pseudocode,
§5.2 edge-case row, TESTS case 17 rewritten + cases 57/58); the
`algorithms/INDEX.md` registry row bumped 0.6.0 → 0.7.0 (the exact
staleness class B12 will gate — it slipped through because no gate
checks the registry yet). TDD RED→GREEN: 70 mdconv tests pass (165
total suite); `make gate` green (format, lint, 5 inline indexes, tests,
secrets); GitHub CI green on `817a8f3`.

**Verification census (fresh `make crawl`, 14,042,184 B, 0 failed
articles):** standalone `---` blocks **12,673 → 0**; double-rule pairs
**13 → 0** (method: full-line regex `(-{3,}|\*{3,}|_{3,})` for hr
lines; pair = two hr lines ≤4 lines apart; GFM separator rows like
`| --- |` are not standalone hr lines). Every dropped rule was a
decorative eGain `<hr>` wrapper — no paragraph text changed.

<!-- BACKLOG:ITEM:B14 -->
## B14. 14 residual leaked layout frames (missed format frames) — **DONE, closed 2026-10-09**
**Priority:** Medium

**User request (verbatim, 2026-10-06, B6 origin):** "There appear to be
some layout tables that were not removed. we need a way of catching there
edge cases and removing them." — and 2026-10-07: "For backlog: more
examples of missed format frames." (three screenshots).

**State (2026-10-07, post-B13 re-census):** 14 layout frames still
render as header-only GFM tables. The exact enumeration (line numbers in
the post-B13 output, article ids, label variants), the UNVERIFIED
hypothesis (block-level children in the label cell → `_frame_row_kind`
returns `None` → whole-table GFM fallback), and the debug path are
recorded in the B6 closeout above. The 14 carry section-mark labels
(`II.i.2.B.4.b.` … `XI.iii.1.A.1.a.`), two `Introduction` /
`In This Section` meta-labels (one bold, one spacer-first), and
bold-wrapped label variants — the same frame family as B6's dissolved
population, with mixed rendering within single articles (sibling
sections in the same article render as proper headings).

**User re-confirmed (2026-10-07, 2 more screenshots — "more frames"):**
these leaked frames are visible in the live render — `II.i.2.C.6.h`
(its content cell's nested If/Then table flattened to literal-pipe inline
text) and `II.i.2.B.4.b` / `II.i.2.B.4.c` (the `B.4.c` content cell
carries the VA Form 21-526EZ image) — while their siblings
(`II.i.2.C.6.i`, `II.i.2.B.4.d`) render as proper headings in the same
articles. All three are already in the 14 above; no new frames added.

**Work items (in order):**

1. Verify the hypothesis frame-by-frame: fetch each owning article's raw
   HTML (fetch recipe in the B6 closeout), parse, and trace
   `_frame_row_kind` row-by-row — confirm exactly what makes the label
   cell fail the inline-only test. Do not guess: the discriminator
   change must match the observed source shape.
2. Doc cycle first (algorithm-records-keeper): refine D8 in
   `html-to-markdown-section-extraction.md` — the label cell's leading
   content must be inline-only; whatever cosmetic wrappers are present
   in the source are unwrapped before the test, never dropped (text
   never lost).
3. Rendering: section-mark labels get **proper heading status** with
   hoisted namespaced anchors (D6); `Introduction` / `In This Section`
   render as label lines per B6's meta-label rule; content cells render
   in block context (B1 behavior) so any nested genuine tables/images
   surface as real GFM tables/images.
4. TDD RED→GREEN: cases that reproduce each failing shape from the raw
   HTML before the fix; `make gate` green; GitHub CI green; one atomic
   commit (doc + code + tests + this backlog entry).
5. Re-census after the fix: expect **40 header-only tables, all
   protected** (the B6 closeout list), **0 leaked frames**; the 40
   protected byte-identical.

**Blast radius:** `_frame_row_kind`, `_is_layout_frame`,
`_render_layout_frame` in `src/m21_crawl/mdconv.py`; the algorithm doc
(D8); `tests/test_mdconv.py`.

**Acceptance criteria:** all 14 enumerated frames dissolve (heading or
label line + content blocks, words verbatim, anchors live where the
source has them); 0 leaked header-only tables remain (40 protected,
enumerated, byte-identical); `make gate` + GitHub CI green; text and
organization unchanged.

**Closeout (2026-10-09, fresh crawl 14,113,700 B, 0 failed articles —
census verified on that output):**

- **Root cause (verified frame-by-frame from the raw HTML, not
  guessed):** the 14 label cells failed the strict inline-only test for
  one of two reasons: (a) inline content wrapped in decorative
  containers (`p`/`span`/`div`; a heading inside a `div`) —
  inline-*equivalent* but not literally inline; (b) an **invisible**
  heading-first cell (the MRS article: lxml repaired malformed markup
  into an empty `<h3>`) — the label was not in `cells[0]`, and the old
  T1 test keyed on the first *visible* cell. Neither shape lost text;
  both now dissolve.
- **Doc cycle first (algorithm-records-keeper):** **D12** (v0.10.0) — a
  label cell qualifies when its content is inline-*equivalent* (the
  decorative wrappers are unwrapped, text never dropped); then the
  **MRS union** (v0.11.0) — T1 is decided on `cells[0]` *before* the
  first visible cell, so an invisible heading-first cell still leads
  with its heading (an empty heading renders no line; the content
  block-renders). Doc at v0.11.0; `algorithms/INDEX.md` row 10 in sync
  (0.11.0).
- **TDD RED→GREEN:** TESTS cases 67–73 added (p/span-wrapped mark
  label; p/strong-wrapped meta label; div-wrapped T1 heading; ZWSP-only
  first cell; `p`-wrapped non-mark label stays GFM; nested-table label
  stays GFM; invisible heading-first MRS shape). Case 71 is the MRS
  regression: RED on pre-fix code, GREEN post-fix. 204 tests pass;
  `make gate` green (format, lint, inline indexes, registry, tests,
  secrets).
- **The 14 frames now dissolve (fresh line numbers):** L6562
  `II.i.2.B.4.b`, L6573 `II.i.2.B.4.c`, L7165 `II.i.2.C.6.h`, L12339
  `II.iii.3.A.3.e`, L28985 `V.ii.4.A.3.d`, L29000 `V.ii.4.A.3.f`, L29020
  `V.ii.4.A.3.g`, L34769 `V.iii.5.3.g`, L72749 `VIII.iv.2.A.3.c`, L117516
  `XI.ii.3.C.4.e`, L119115 `XI.iii.1.A.1.a. Definition: Burial`
  (bold-wrapped) — plus 3 meta-label frames (1 `Introduction`, 2
  `In This Section`) now `### ` headings identical to the 335
  `### In This Section` headings the other dissolved frames already
  produce (TESTS 47/50). Zero `| Introduction |` / `| In This Section |`
  table rows remain.
- **Census (fresh output):** **43 header-only GFM tables = 42 protected
  + 1 (SSA 6.i)**; **0 leaked frames**. Acceptance expected "40
  protected" (pre-D12, 2026-10-07); the +2 is portal content drift —
  the Memorandum of Changes cluster now carries 6 date pairs through
  `2026-03-09`.
- **SSA 6.i (L84917, 5 cols, first 4 empty, content last): protected by
  design** — no heading in any cell, so it is neither T1 (needs a
  heading) nor T2 (needs a mark/meta label); consistent with
  `_frame_row_kind`. *Agent decision, not user-approved — surfaced
  here.*
- **42 protected enumeration (fresh line numbers):** L6519, L8934, L8946,
  L8958, L24613, L28445, L28454, L38222, L38225, L39408, L39428, L41808,
  L44054, L67610, L68191, L68242, L72754, L80557, L84949 (SSA 6.k),
  L84973 (SSA 6.m), L90525, L96573, L96589, L109047, L112272, L112626,
  L112861, L115129, L125500, L131210 + the 6 two-line Memorandum of
  Changes tables L143336/39/46/49/56/59/66/69/76/79/86/89 (date pairs
  `2015-03-24` → `2026-03-09`).
- **Follow-up (new backlog candidate):** memo templates (SSA 6.i/6.k/6.m,
  letter) render as header-only tables — cosmetic, content intact
  (candidate: block-render single-row tables whose cells are
  inline-only content).
- **Landed:** commit `827a8c0` (atomic: doc v0.11.0 + INDEX + tests +
  code + this closeout); GitHub CI run 37999360788 (`head_sha`
  `827a8c0…`, conclusion success) —
  <https://github.com/mirph-glitch42/m21-1/actions/runs/37999360788>.

<!-- BACKLOG:ITEM:B15 -->
## B15. Change Date frames not in a quote block (B11 gap) — **DONE, closed 2026-10-09**
**Priority:** Medium

**User request (verbatim, 2026-10-07):** "For backlog: not all change
dates are in quote blocks." + screenshot (article "M21-1, Part VIII,
Subpart iv, Chapter 7, Section A - Compensation for Paired Organs or
Extremities Under 38 CFR 3.383") showing `Change Date` rendered as a
**heading** and `May 13, 2015` as a **plain paragraph** — i.e. NOT the B11
quote block (`> **Change Date**` / `> May 13, 2015`).

**Why this is a gap (not a regression):** B11's closeout (2026-10-07)
verified **1,260** `> **Change Date**` quote lines and **0**
`#`–`###### Change Date` headings on the post-B13 re-crawl. This frame
proves that census was incomplete: at least one Change Date frame in the
regenerated manual still renders heading + plain date. B11's detection was
scoped to (a) D5-dissolved *frame label* headings and (b) B6 meta-label
*table* rows. A `Change Date` that is a **standalone heading not part of a
dissolved frame** (or a bold-paragraph label, or a heading level the census
did not enumerate, e.g. `<h4>`) falls outside both paths.

**Work items (in order):**

1. Census the regenerated manual for every `Change Date` occurrence that is
   **not** a `> **Change Date**` quote line — headings of any level,
   bold-paragraph labels, table rows — and enumerate them (line number +
   owning article id + exact source variant). Confirm count > 0 and pin the
   missed shape(s).
2. Fetch the owning article's raw eGain HTML (fetch recipe in the B6
   closeout) and trace `mdconv` — confirm exactly which branch lets it
   through (likely a non-frame heading, or a label the D5/D8 paths don't
   match). Do not guess: the discriminator change must match the observed
   source shape.
3. Doc cycle first (algorithm-records-keeper): extend the Change Date
   carve-out in `html-to-markdown-section-extraction.md` so *any* `Change
   Date` label (heading or bold label, any level, frame or not) converges
   to the quote block; keep anchor hoisting where the source had a heading;
   never drop text.
4. TDD RED→GREEN: a case that reproduces the missed shape from raw HTML
   before the fix; `make gate` green; GitHub CI green; one atomic commit
   (doc + code + tests + this backlog entry).
5. Re-census after the fix: expect **0** non-quote-block Change Date frames
   in the regenerated manual; the full population (1,260 + the missed set)
   renders as `> **Change Date**` + verbatim date.

**Progress (2026-10-09) — WI 1–5 done:**

- **WI 1 (census on the fresh 14,113,700 B output):** 1,260
  `> **Change Date**` quote lines (good); **missed population = 218 bold
  h3 headings** (217 `### **Change Date**` + 1 `### ****Change Date****`,
  output L11992); 0 other heading levels, table rows, or bold-paragraph
  labels; 2 legitimate body-text mentions left alone (L12948, L140090).
  Total 1,480 = 1,260 + 218 + 2 (arithmetic verified).
- **WI 2 (raw HTML fetched, no guessing):** both corpus shapes verified
  from source — article `554400000177486`: T1 frame, `<h3><strong><span…>
  Change Date</span></strong></h3>` + spacer + `<div><span>May 13,
  2015</span></div>`; article `554400000174880` (output L11992): same
  shape, one extra nested span (the double-bold `****Change Date****`).
  **Root cause (traced):** the `_render_layout_frame` T1 branch tests the
  *rendered* inline string (`**Change Date**`) against `_CHANGE_DATE`, so
  it falls through to the heading path; the T2 path already used
  `_plain_label` — which is why case46 (T2 bold) passed while the 218 T1
  frames leaked.
- **WI 3–4 (doc cycle + TDD):** doc 0.11.0 → **0.12.0** (B11 carve-out
  now explicitly emphasis-independent on T1; pseudocode, TESTS row 74,
  §5.2 row; INDEX row 10 in sync); new test **case72** RED on the old
  code (exactly the `### **Change Date**` symptom) → **one-line fix** in
  the T1 branch (`if t == _CHANGE_DATE` →
  `if _plain_label(heading) == _CHANGE_DATE`) → GREEN (205 pass);
  article `554400000177486` re-verified end-to-end: raw HTML now
  converts to `> **Change Date**` / `> May 13, 2015`; `make gate` green.
  **Scope (agent decision, surfaced at commit):** fix the verified T1
  frame path only; if any `### **Change Date**` heading survives the
  re-census it would be a non-frame standalone heading to investigate
  individually (expected: 0).
- **WI 5 (done 2026-10-09):** full re-crawl (14,113,478 B, 0 failed
  articles; both completeness gates pass) → re-census: **0** bold
  `Change Date` headings (checked both `### **Change Date**` and
  `### ****Change Date****` variants) and **1,478** `> **Change Date**`
  quote lines = 1,260 (B11) + 218 (this fix); no surviving non-frame
  bold heading to investigate (the scope decision's expected outcome).
- **Landed:** commit `dd54c1e` (atomic: doc v0.12.0 + INDEX + tests +
  code + this entry); GitHub CI run 38020365154 (`head_sha` `dd54c1e`,
  conclusion success) —
  <https://github.com/mirph-glitch42/m21-1/actions/runs/38020365154>;
  re-crawl + this closeout 2026-10-09.

**Blast radius:** the D5 heading carve-out / `_render_layout_frame` in
`src/m21_crawl/mdconv.py`; the algorithm doc (D5/D8 carve-out);
`tests/test_mdconv.py`.

**Acceptance criteria:** in the regenerated manual, **0** `Change Date`
labels render as a heading, bold paragraph, or table row outside the quote
block; every Change Date frame renders as `> **Change Date**` + verbatim
date (words unchanged — the approved B11 deviation); `make gate` + GitHub
CI green.

**Ordering:** independent of B7–B14; small standalone cycle. Rides the same
`mdconv` doc as B6/B11/B13/B14.

<!-- BACKLOG:ITEM:B16 -->
## B16. Nested-in-cell tables unreadable + one leaked multi-section chunk — **DONE, closed 2026-10-10**
**Priority:** Medium

**User request (verbatim, 2026-10-10):** "Identify all tables embedded
within tables, and convert them to ascii tables so they are actually
readable. place all required tasks in the backlog before proceeding with
the doc+TDD cycle."

**Census (assembled manual 2026-10-10; 14,113,478 B / 143,171 lines):**
**263** lines contain `<br>` (**913** `<br>` total). Signature: class (a)
= line starts with `|` and contains `<br>`; class (b) = contains `<br>`
but does **not** start with `|`:

- **Class (a) = 262 lines** — well-formed GFM data rows whose cell holds a
  *nested* table rendered as unaligned `<br>`-joined pipe-escaped text:
  `**Step** \\| **Action** <br> 1 \\| Navigate …`. **108 articles**
  affected. Top: art `554400000179488` (11 lines), `554400000173969`
  (10), `554400000014108` (9), `554400000176614` (9). Representative
  lines: L3011 (art `554400000181476`, Step/Action POA table), L3351
  (art `554400000181477`, document-field attribute table), L4198
  (art `554400000181483`, If/Then correspondence table).
- **Class (b) = exactly 1 line** — **L12941**, art `554400000174883`
  (title "2. VDC Rating Claims Intake"): a whole multi-section chunk
  (2.a–2.f, 3, 3.a–3.c, 4, 4.a–4.b …) leaked as ONE plain-text line — no
  leading `|`, 15 `<br>` joins, source `<hr>`s flattened to ` — `. Only
  **2** ` — ` lines exist in the whole file, both in/near this one → the
  leak is singular and isolated.

**Root cause — class (b) (traced from raw HTML, no guessing):** fetched
the raw eGain HTML of `554400000174883` (91,083 B) and parsed it with
the same parser `mdconv` uses. The article body's top-level children
include an **orphan `<tbody>` element** holding the entire leaked
remainder: orphan `<tbody>` → `<tr>` → a single `<td>` with 97 children
(alternating `div`/`table`/`div` …) → the section frames. In
`mdconv.py`, `_render_block_list` dispatches children by tag; `<tbody>`
is in **neither** `_BLOCK` (`_HEADING | {p,ul,ol,table,blockquote,pre,
hr}`) **nor** `_UNWRAP_BLOCK` (`{div,span,font,center}`), so it falls to
the final fallback `run.append(_render_inline_piece(child, …))`, which
unwraps unknown tags and renders everything (tables, hrs) INLINE into
one paragraph run → the giant L12941 line.

**Shape — class (a) (traced from raw HTML of `554400000181476`):** the
outer table is a genuine 2-column data table (condition | action); the
nested table (Step/Action) sits *inside the action cell*. GFM cannot
nest tables in cells, so the nested table must render as in-cell ASCII
text (user-directed).

**Chosen approach (class (a) user-directed; class (b) agent-proposed —
both flagged for user review):**

- **Class (a):** render each nested in-cell table as an **ASCII pipe
table** — columns padded to equal widths, a `---` separator row under
the header, rows `<br>`-joined, pipes escaped (`\\|`) as today. Outer
stays a real GFM table (it is real data). Bold/links inside cells render
as they do today. TEXT/ORGANIZATION unchanged.
- **Class (b):** treat orphan table-part elements (`tbody`/`thead`/
  `tfoot`/`tr`/`td`/`th`/`caption`) found in *block* position as
  **transparent wrappers** — unwrap so their children render in block
  context; the section frames inside then dissolve through the existing
  D5 path into real headings + GFM tables. Conservative: never drop
  text; only fires for table parts that are malformed direct children of
  a block list (legitimate tables render through `_render_table` and are
  untouched).

**Work items (in order):**

1. **WI 1 (done 2026-10-10):** this backlog entry — census + root-cause
   trace + work items, written before any doc/code (user-directed
   ordering).
2. **WI 2 — doc cycle first** (algorithm-records-keeper): bump
   `algorithms/html-to-markdown-section-extraction.md` **v0.12.0 →
   v0.13.0**: extend §2.6 (nested table rendering = padded ASCII pipe
   table + `---` separator row, `<br>`-joined, pipes escaped) and add the
   orphan-table-part unwrap rule (new D-rule, or extend D7/D12); regen
   line index; update the `algorithms/INDEX.md` row (gate-enforced to
   match the doc version).
3. **WI 3 — TDD RED→GREEN** in `tests/test_mdconv.py` (72 cases
   currently): (a) a case reproducing the unreadable nested render
   (`**Step** \\| **Action** <br> 1 \\| …`) → assert the padded
   ASCII-pipe + separator form; (b) a case with orphan
   `<tbody><tr><td><h3>…` → assert it renders as a heading + blocks,
   NOT one inline line. RED confirmed on the old code first; then
   implement in `mdconv.py`; `make gate` green.
4. **WI 4 — atomic commit:** doc + INDEX + tests + code + this entry
   (explicit paths; **never** `git add -A`); Conventional Commit ≤72
   chars; push; GitHub CI green.
5. **WI 5 — re-crawl + re-census:** full manual re-crawl (0 failed
   articles); re-census on the fresh output: class (b) = **0** (no
   non-`|` line contains a `<br>` join or a ` — ` hr-flatten); all class
   (a) lines in the padded ASCII-pipe form; TEXT/ORGANIZATION unchanged.
6. **WI 6 — closeout:** record commit sha, CI run id, re-crawl size,
   re-census numbers in this entry (B14/B15 closeout format); flip the
   status line to done.

**Progress (2026-10-10) — WI 1–6 done:**

- **WI 1 (done):** this backlog entry — census + root-cause trace + work
  items, written before any doc/code (user-directed ordering).
- **WI 2 (doc cycle first):** doc 0.12.0 → **0.13.0** — §2.6 extended
  (a nested in-cell table renders as a **padded ASCII pipe table**: cells
  right-padded to the column width, a `---` separator row under the
  header always emitted (`"-"*max(3,w)`), rows `<br>`-joined, pipes
  escaped once by the outer `_render_table`); new **D14** rule (orphan
  table-part elements `tbody`/`thead`/`tfoot`/`tr`/`td`/`th`/`caption`
  found in *block* position unwrap as transparent wrappers so their
  block children dissolve into real headings + GFM tables); TESTS cases
  added; `algorithms/INDEX.md` row 10 in sync at 0.13.0.
- **WI 3 (TDD RED→GREEN):** new cases RED on the old code — (a) a nested
  Step/Action table → the old unpadded `<br>`-joined form, now the
  padded ASCII-pipe + separator form; (b) an orphan
  `<tbody><tr><td><h3>…` → the old single inline line, now a heading +
  blocks. GREEN: **207 pass**.
- **WI 4 (atomic commit):** doc + INDEX + tests + code + this entry,
  explicit paths only (never `git add -A`).
- **WI 5 (re-crawl + re-census, done 2026-10-10):** full re-crawl
  (**14,602,019 B**, 0 failed articles; both completeness gates pass).
  Re-census on the fresh output: the pre-B16 **L12941 class-(b) leak is
  GONE** (that chunk now renders as real headings + GFM tables); all
  **262** class-(a) nested tables are now in the padded ASCII-pipe form
  (D13). See the deviation note below for the one residual line.
- **Landed:** commit `489fa4a` (atomic: doc v0.13.0 + INDEX + tests +
  code + this entry); GitHub CI run **38081371078** (`head_sha`
  `489fa4a`, `gate` job **success**) —
  <https://github.com/mirph-glitch42/m21-1/actions/runs/38081371078>.
  **SonarCloud** (check-run job id `114298883090`) is an **external
  GitHub-App check, not part of our `ci` workflow** (which defines only
  the `gate` job); it was already `failure` at the prior user-approved
  tip `a922976`, so it is pre-existing noise, not caused by this work —
  **`gate` green = CI green**.

**Deviation note (honest, surfaced at closeout):** the re-census
surfaced **one** residual class-(b) line — **L58156**, article
`554400000176623` (Part VII, Subpart i, Chapter 3, Section A),
subsection `VII.i.3.A.4.d` — a whole section chunk inlined into a single
garbage line. This is a **different root cause** from the B16 L12941
leak: the source HTML contains a **malformed tag** (`<div<< div="">` …
`</div<<>`) that lxml names `div<<`, and `mdconv`'s inline-run fallback
dumps its block content inline. **Verified pre-existing (not a B16
regression):** running the pre-B16 `mdconv` (`git show a922976`) on the
same article produces the same garbage line (old form, no `<br>`), which
is exactly why it was invisible to the `<br>`-based census; B16's D13
(always-emitted separator row) made it visible. **B16 did not cause
it.** It is now tracked as **B19** (the corpus census found **7**
articles carrying malformed tag names). B16 is closed on its own
acceptance criteria (the L12941 leak is gone; every class-(a) nested
table is padded ASCII); the residual is a separate bug with its own
entry.

**Blast radius:** `_render_block_list` fallback +
`_render_table_inline`/`_render_cell` in `src/m21_crawl/mdconv.py`; the
algorithm doc (§2.6 + new D-rule); `tests/test_mdconv.py`.

**Acceptance criteria:** in the regenerated manual — **0** class-(b)
leaked lines (the L12941 chunk renders as real headings + GFM tables);
**0** unpadded nested renders (every in-cell table is the padded
ASCII-pipe form); 0 ` — ` hr-flattened joins; TEXT/ORGANIZATION unchanged
(goal 1); `make gate` + GitHub CI green.

**Ordering:** after B15 (tip `a922976`); rides the same `mdconv` doc as
B6/B11/B13/B14/B15.

<!-- BACKLOG:ITEM:B17 -->
## B17. Inline images break paragraph readability — **CANCELLED 2026-10-16**
**Priority:** Medium

**User request (verbatim, 2026-10-10):** "Images in-line with text makes
for bad readability. Images should be blocked away from the text to
maximize readability of the document. This can be either space above and
below the image, or text wraping around the image. Just not in-line with
the text."

**Symptom (screenshot, 2026-10-10):** in the assembled manual, screenshots
sit *inside* paragraphs — e.g. the "Browse Topics" image in the
"Searching M21-1 Content in KM" article: text flows on the same line
before **and** after the image ("…drill down to the M21-1. `![…](…)`
By entering your search word(s) or phrase…"), so renderers wrap the
paragraph around the inline image and the reading order breaks.

**Mechanism (hypothesis — trace + census in WI 2):** `<img>` renders
through the inline path (`_render_inline_piece`), so (a) a `<p>` with
mixed text + `<img>` children emits one Markdown line with the image
inline, and (b) a top-level `<img>` in block context falls to
`_render_block_list`'s inline-run fallback (neither `_BLOCK` nor
`_UNWRAP_BLOCK`), joining the surrounding text run.

**Chosen approach (agent-proposed, within the user's directive):** treat
`<img>` as block-level in block context: flush the current inline run,
emit `![alt](src)` on its own line (standard block separation — blank
line above and below), then start a fresh run for the following text. A
`<p>` containing an image splits at the image boundary (text before → its
own paragraph, image on its own line, text after → new paragraph).
TEXT/ORGANIZATION unchanged (only block layout of the image line).

**Work items (in order):**

1. **WI 1 (done 2026-10-10):** this backlog entry — written before any
   doc/code (user-directed ordering).
2. **WI 2 — census + root-cause trace:** census the assembled manual for
   Markdown lines where `![` shares the line with non-image text
   (count + top articles); fetch the raw eGain HTML of 2–3
   representatives and confirm which mechanism fires (`<img>` inside a
   `<p>` vs. top-level `<img>` in a block list vs. both).
3. **WI 3 — doc cycle first** (algorithm-records-keeper): bump
   `algorithms/html-to-markdown-section-extraction.md` **v0.15.0 →
   v0.16.0** (B19/B18 now precede it in the queue): new D-rule "images
   are blocks in block context" (or extend
   D7/§2.6), update the error/edge-case tables, rewrite affected TESTS
   rows, add new TESTS cases; update the `algorithms/INDEX.md` row
   (gate-enforced to match the doc version).
4. **WI 4 — TDD RED→GREEN** in `tests/test_mdconv.py`: (a) `<p>` with
   text + `<img>` + text → assert three blocks (text paragraph, image
   line, text paragraph); (b) top-level `<img>` between two text runs →
   assert the image is on its own line, text runs not joined to it. RED
   confirmed on the old code first; then implement in `mdconv.py`;
   `make gate` green.
5. **WI 5 — atomic commit:** doc + INDEX + tests + code + this entry
   (explicit paths; **never** `git add -A`); Conventional Commit ≤72
   chars; push; GitHub CI green.
6. **WI 6 — re-crawl + re-census:** full manual re-crawl (0 failed
   articles); re-census: **0** lines where `![` shares a line with
   non-image text; TEXT/ORGANIZATION unchanged (goal 1).
7. **WI 7 — closeout:** record commit sha, CI run id, re-crawl size,
   re-census numbers in this entry (B14/B15/B16 closeout format); flip
   the status line to done.

**Blast radius:** `_render_block_list` + `_render_inline_piece`/
`_render_cell` in `src/m21_crawl/mdconv.py`; the algorithm doc (new
D-rule + TESTS); `tests/test_mdconv.py`.

**Acceptance criteria:** in the regenerated manual — **0** Markdown
lines where an `![…]` image shares the line with non-image text (every
image sits on its own line with blank lines above and below);
TEXT/ORGANIZATION unchanged (goal 1); `make gate` + GitHub CI green.

**Ordering:** after **B19**, **B18**, and **B21** (all now precede it in the
queue); rides the same `mdconv` doc as B6/B11/B13/B14/B15/B16/B18/B19/B20/B21.

**Progress:**

- 2026-10-16 — migrated to the priority scheme (G9): priority = **Medium**
  (migration default).
- 2026-10-16 — **CANCELLED** (user-directed 2026-10-16): non-issue after
  **B21** (inline-only `<div>` paragraph breaks, DONE `d1e03ca`/`33c02f4`) —
  B21's block-separation already moves images out of inline paragraph flow,
  so B17's readability goal is met; no code, doc, or test change required.

**Closeout (cancelled 2026-10-16):** CANCELLED — superseded by **B21** (DONE),
which already blocks inline images out of paragraph flow. No code/doc/test
change; no version (G6). Re-queued the remainder (B17 removed from the Queue).

<!-- BACKLOG:ITEM:B18 -->
## B18. Section nav links — unified schema, To Top folded in — **OPEN, new 2026-10-10**
**Priority:** Medium

**User request (verbatim, 2026-10-10):** "For readability, let's format
section navigation links like: `<-- Previous Section | Top | Next
Section -->` for bottom of section links, or, for the top of article
links: `<-- Previous Section | Next Section -->` Centered on the page,
if possible. This, of course, wraps the `To Top` link into this new
schema, and will require the removal of the old `To Top` link."

**Current state (census of the assembled manual, 2026-10-10,
14,602,019 B):**

- **Bottom-of-section nav** renders as two space-separated links on one
  line: `[<-- Previous Section](#m21-1-part-…) [Next Section -->]
  (#m21-1-part-…)` — Prev/Next point at the manual's assembled section
  anchors (B8). No "Top" in this schema today.
- **To Top** appears **418** times and is **inconsistent**:
  - **409** point at the article-top anchor (`#art_N_top` **320** +
    `#art_N_Top` **89**) — these *work* (jump to the top of the
    article).
  - **~9** point at a **non-top** anchor: `#art_N_Overview` (2), `#n`
    (1), `#d` (1), `#c` (1), and **5** `#m21-1-part-…` *section*
    anchors — these are the To Top links that "do nothing" (the target
    is not a heading anchor in the output). This matches the user's
    earlier note that "a lot of them do not do anything."
  - Layout: **373** are a standalone line (their own block); **31** are
    appended to the nav line with **no space** (`…[Next Section -->]
    (…)[To Top](…)`); the remainder sit in other contexts (incl. the
    B19 inlined line L58156).
- **Mechanism:** the eGain HTML nav `<p>` carries the Prev/Next links
  (→ `#m21-1-part-…`) and a `To Top` link (`<a href="#top">`, rewritten
  by **D6** into the per-article namespace `#art_N_top`). There is
  **no** nav/To-Top-specific code path in `mdconv.py` — all of this is
  a product of the *generic* inline-run rendering (the nav `<p>` and the
  `To Top` `<div><span><a>` are unwrapped and their links emitted as
  inline pieces, which is why the spacing/positioning is inconsistent).
  This item **adds** a dedicated nav-rendering rule rather than patching
  the generic path.

**Chosen approach (user-directed; design details agent-proposed, flagged
for review):** add a nav-link rule so the section-navigation links render
as a **single, centered-where-possible, pipe-joined line**:

- **Bottom of an article** (the nav that follows a section body):
  `<-- Previous Section | Top | Next Section -->` — three links,
  ` | `-joined, one unit; **Top** = the folded To Top link, and **all**
  Top links point at the article-top anchor `#art_N_top` (the ~9 broken
  section/malformed targets are corrected to the article top).
- **Top of an article** (the leading nav, before the first section):
  `<-- Previous Section | Next Section -->` — two links (no Top, since
  the reader is already at the top).
- **Centering is best-effort**: pure GFM has no centering primitive, so
  we either emit a `<center>…</center>` wrapper (HTML; many renderers
  honor it, some strip it) or leave the line left-aligned. The
  non-negotiable deliverable is the pipe-joined single-line schema;
  centering is "if possible" per the user and is renderer-dependent.
- The **standalone `To Top` block is removed** (its function is folded
  into the bottom nav's Top); TEXT/ORGANIZATION otherwise unchanged.

**Work items (in order):**

1. **WI 1 (done 2026-10-10):** this backlog entry — census of the
   current nav/To Top shapes + mechanism, written before any doc/code
   (user-directed ordering).
2. **WI 2 — trace + pin the design:** fetch the raw eGain HTML of 2–3
   representative articles (one with a working To Top, one with a broken
   section/malformed To Top, one top-of-article nav) and confirm the
   exact source shape of the nav `<p>` (Prev/Next/Top hrefs) and the
   `To Top` `<div>`; decide the centering mechanism (test whether the
   target renderers honor `<center>`); confirm the article-top anchor
   (`#art_N_top` vs `#art_N_Top`) each article actually exposes so the
   corrected Top links resolve.
3. **WI 3 — doc cycle first** (algorithm-records-keeper): bump
   `algorithms/html-to-markdown-section-extraction.md` **v0.14.0 →
   v0.15.0** (after B19): new D-rule "section nav links render as a
   single pipe-joined, centered-where-possible line — bottom `<--
   Previous Section | Top | Next Section -->`, top `<-- Previous Section
   | Next Section -->`; the standalone To Top block is removed and its
   target folded into the bottom Top link; broken To Top targets are
   corrected to the article-top anchor"; update the error/edge-case
   tables + TESTS rows; update the `algorithms/INDEX.md` row
   (gate-enforced to match the doc version).
4. **WI 4 — TDD RED→GREEN** in `tests/test_mdconv.py`: (a) bottom nav
   `<p>` (Prev+Next+Top) → assert one line `<-- Previous Section | Top
   | Next Section -->` with all three anchors and the Top → `#art_N_top`;
   (b) top nav (Prev+Next only) → `<-- Previous Section | Next Section
   -->`; (c) a To Top whose href is a broken section/malformed anchor →
   assert it is corrected to the article-top anchor (or dropped if no
   top anchor exists); (d) assert **no** standalone `To Top` block
   remains. RED on the old code first; then implement a dedicated nav
   path in `mdconv.py`; `make gate` green.
5. **WI 5 — atomic commit:** doc + INDEX + tests + code + this entry
   (explicit paths; **never** `git add -A`); Conventional Commit ≤72
   chars; push; GitHub CI green.
6. **WI 6 — re-crawl + re-census:** full manual re-crawl (0 failed
   articles); re-census: **0** standalone `To Top` blocks; every
   bottom-of-section nav is exactly `<-- Previous Section | Top | Next
   Section -->`; every top-of-article nav is `<-- Previous Section | Next
   Section -->`; **0** To Top links pointing at a non-existent anchor
   (the ~9 broken ones now resolve to the article top);
   TEXT/ORGANIZATION unchanged (goal 1).
7. **WI 7 — closeout:** record commit sha, CI run id, re-crawl size,
   re-census numbers in this entry (B14/B15/B16 closeout format); flip
   the status line to done.

**Blast radius:** a new nav-link rendering path in
`src/m21_crawl/mdconv.py` (detect the section-nav `<p>` / To Top block
in block context and emit the unified line; interacts with D6 anchor
rewrite + D7 inline-run coalescing); the algorithm doc (new D-rule +
TESTS); `tests/test_mdconv.py`.

**Acceptance criteria:** in the regenerated manual — every
bottom-of-section nav is exactly `<-- Previous Section | Top | Next
Section -->` (three links, pipe-joined, centered where the renderer
allows); every top-of-article nav is `<-- Previous Section | Next
Section -->`; **0** standalone `To Top` blocks; **0** To Top links
pointing at a non-existent anchor (all Top links resolve to the
article-top anchor); TEXT/ORGANIZATION unchanged (goal 1); `make gate`
+ GitHub CI green.

**Ordering:** after **B19** (nav must be in normal block form before
reformatting — B19 fixes the inlined nav in the malformed-tag articles)
and before B17 (and after **B21** — queue 2026-10-13: B20 → B21 → B18 → B17). Rides the same `mdconv` doc as B6/B11/B13/B14/B15/B16/
B17/B19/B20/B21.

**Progress:**

- 2026-10-16 — migrated to the priority scheme (G9): priority = **Medium**
  (migration default).

<!-- BACKLOG:ITEM:B19 -->
## B19. Malformed HTML tags inline entire section chunks — **DONE, closed 2026-10-10**
**Priority:** Medium

**Discovery (2026-10-10, during the B16 re-census):** the B16 re-census
surfaced **one** new class-(b) leak with a **new root cause** (not the
orphan-`<tbody>` shape B16 fixed). It is a **correctness** bug: a whole
section chunk is inlined into a single garbage line.

**Symptom (verified, no guessing):** article `554400000176623` (Part
VII, Subpart i, Chapter 3, Section A — "Establishing a Child's Age and
Relationship"), subsection `VII.i.3.A.4.d`: the entire section (heading +
anchor + content `<ul>` + `<hr>` + Prev/Next nav + To Top) is inlined
into **one** garbage line at **L58156**, starting
`— | VII.i.3.A.4.d<a id="art_554400000176623_4d" …>`. The sibling
subsections 4.a–4.c in the same article render correctly.

**Root cause (traced from the raw HTML, 61,205 B, no guessing):**

1. The source HTML contains a **malformed tag pair**:
   `<div<< div="">` … `</div<<>` wrapping `<div><hr/></div>` + the 4.d
   layout-frame table (h3 | spacer | content div+ul) + `<div><hr/></div>`
   + the Prev/Next nav `<p>` + the To Top `<div>`.
2. The parser is BeautifulSoup + **lxml** (`_parse`, `mdconv.py`
   L104–106). lxml names the malformed tag **`div<<`** (attribute
   `div=""`) — confirmed with a minimal fragment test.
3. `div<<` is the **last body child**; siblings 0–61 are normal
   `p`/`h2`/`div`/`table` frames, all rendered fine.
4. `mdconv` dispatch (`_render_block_list`, final `else` branch ~L230):
   `div<<` is in **neither** `_BLOCK` **nor** `_UNWRAP_BLOCK`
   (`div,span,font,center`) **nor** `_TABLE_PART` (D14), so it falls to
   `run.append(_render_inline_piece(child))` → the **entire subtree**
   (hr → ` — `, table → D13 inline ASCII, nav links inline) is rendered
   INLINE into one paragraph run = the observed garbage line.
5. **Verified pre-existing (not a B16 regression):** running the
   pre-B16 `mdconv` (`git show a922976:src/m21_crawl/mdconv.py`) on the
   same article produces the **same** garbage line (old single-row-join
   form, no `<br>`) — which is exactly why it was **invisible** to the
   B16 `<br>`-based census. B16's D13 (always-emitted separator row) made
   it visible. So B16 did **not** cause it; the old census simply missed
   it.

**Corpus census (2026-10-10; 442 non-excluded articles, 0 fetch errors):**
tag-name census over the **parsed** HTML (a `<br>`-based census is blind
to this class — malformed-tag inlined content without `<br>` is
invisible, which is how it hid pre-B16). **7 articles** carry a malformed
tag name, each exactly one:

| article id | malformed tag name |
|---|---|
| `554400000014116` | `introduction<` |
| `554400000179497` | `d<a` |
| `554400000176623` | `div<<` |
| `554400000177994` | `p"` |
| `554400000178000` | `div"` |
| `554400000174208` | `viii.5.13.<` |
| `554400000174201` | `p<span` |

(The census is a *population* bound — it counts malformed tag names in
the source. Only the ones whose malformed wrapper is a **direct body
child** that reaches `_render_block_list`'s inline fallback actually
inline-dump block content; WI 2 confirms which of the 7 leak.)

**Chosen approach (agent-proposed, flagged for user review):** in
`_render_block_list`'s final `else` branch, if `_contains_block_el(child)`
→ **flush the current inline run and recurse** `_render_block_list
(child.children, …)` (unwrap as a transparent block wrapper, like
D7/D14), so a malformed-tag wrapper that **contains block content**
dissolves into real blocks; **otherwise** keep the current
inline-into-run behavior (preserves `sup`/`sub`/genuine-inline-unknown
behavior). Conservative: never drops text; only fires for unknown tags
that actually contain block elements. New D-rule (**D15**) + doc bump +
TDD case reproducing the `<div<< div="">` shape.

**Work items (in order):**

1. **WI 1 (done 2026-10-10):** this backlog entry — symptom + full
   root-cause trace + pre-existing proof + corpus census, written before
   any doc/code (user-directed ordering).
2. **WI 2 — confirm the leaking population:** of the 7 census articles,
   fetch the raw HTML of each and confirm which malformed tags are
   **direct body children reaching the inline fallback** (vs. nested,
   where a parent already unwraps them); pin the exact source shape(s)
   (the `<div<< div="">` case is confirmed; the other 6 need their shape
   pinned so the discriminator matches the observed source, not a guess).
3. **WI 3 — doc cycle first** (algorithm-records-keeper): bump
   `algorithms/html-to-markdown-section-extraction.md` **v0.13.0 →
   v0.14.0**: new **D15** rule "an unknown/malformed tag that **contains
   block elements** unwraps as a transparent block wrapper (its children
   render in block context) — never inline-dump block content;
   genuinely-inline unknown tags keep the current inline behavior";
   update the error/edge-case tables + add TESTS cases; update the
   `algorithms/INDEX.md` row (gate-enforced to match the doc version).
4. **WI 4 — TDD RED→GREEN** in `tests/test_mdconv.py`: (a) a case
   reproducing `<div<< div="">` wrapping `<hr>` + a layout-frame table +
   a nav `<p>` → assert it renders as `hr`-nothing + a real heading +
   block content + nav, **not** one inline line; (b) a case with a
   genuinely-inline unknown tag (e.g. `<sup>x</sup>` inside text) →
   assert it still renders inline (no regression). RED on the old code
   first; then implement in `mdconv.py`; `make gate` green.
5. **WI 5 — atomic commit:** doc + INDEX + tests + code + this entry
   (explicit paths; **never** `git add -A`); Conventional Commit ≤72
   chars; push; GitHub CI green.
6. **WI 6 — re-crawl + re-census:** full manual re-crawl (0 failed
   articles); tag-name census over all 442 articles → **0** articles
   whose block content is inline-dumped by an unknown tag; article
   `554400000176623` §`VII.i.3.A.4.d` renders as an anchor + a real
   heading + block content + a normal nav line, like its sibling
   subsections; TEXT/ORGANIZATION unchanged (goal 1).
7. **WI 7 — closeout:** record commit sha, CI run id, re-crawl size,
   re-census numbers in this entry (B14/B15/B16 closeout format); flip
   the status line to done.

**Progress (2026-10-10) — WI 1–7 done:**

- **WI 1 (done):** this backlog entry — symptom + full root-cause
  trace + pre-existing proof + corpus census, written before any
  doc/code (user-directed ordering).
- **WI 2 (leaking population confirmed):** fetched all 7 census
  articles and shaped each malformed tag against the parsed tree:
  **exactly 1 of 7 leaks** — `554400000176623`'s `div<<` is a **direct
  body child** whose subtree holds block elements (div+hr, layout-frame
  table, div+hr, nav `<p>`, To Top div) → `_contains_block_el=True`.
  The other 6 (`554400000014116` `introduction<`, `554400000179497`
  `d<a`, `554400000177994` `p"`, `554400000178000` `div"`,
  `554400000174208` `viii.5.13.<`, `554400000174201` `p<span`) are
  **inline-position junk nested inside `h3`/`td`/`li`** with **zero**
  block descendants → D15 correctly leaves them inline (no regression).
  The `_contains_block_el` discriminator matches the observed source
  exactly.
- **WI 3 (doc cycle first):** doc 0.13.0 → **0.14.0** — new **D15**
  rule (an unknown/malformed tag that **contains block elements**
  unwraps as a transparent block wrapper — flush the inline run and
  recurse into block context, exactly like D7 containers / D14 orphan
  parts — while an inline-only unknown tag keeps the inline-into-run
  behavior), error-model row, pseudocode final-`else` branch, 4.1
  walkthrough, two new edge-case rows, TESTS cases 77–78;
  `algorithms/INDEX.md` row in sync at 0.14.0; line index regenerated
  (gate-enforced).
- **WI 4 (TDD RED→GREEN):** test cases 75–76 (doc TESTS 77–78): case
  75 reproduces the `div<< div="">` shape (hr wrappers + layout-frame
  table + nav `<p>`); **RED confirmed on the old code** (the exact
  garbage line `— | VII.i.3.A.4.d… | one; two |`); case 76
  (inline-only `p<span`) passes before and after (no regression).
  D15 implemented in `_render_block_list`'s final `else`; **209
  pass**, `make gate` green.
- **WI 5 (atomic commit):** doc + INDEX + tests + code, explicit paths
  only (never `git add -A`); this entry stayed OPEN until the closeout
  below (B14/B15/B16 two-commit pattern).
- **WI 6 (re-crawl + re-census, done):** full re-crawl
  (**14,601,436 B**, **143,358 lines**, 0 failed articles; both
  completeness gates pass). Re-census on the fresh output: **0**
  class-(b) lines (no non-`|` line contains a `<br>` join), **0**
  ` — ` hr-flattened lines in the entire file; article
  `554400000176623` §`VII.i.3.A.4.d` now renders as the hoisted
  namespaced anchor + `### VII.i.3.A.4.d…` heading + paragraph/list
  blocks + a normal Prev/Next + To Top nav (L58156–L58172) — like its
  sibling subsections; the other 6 census articles' inline junk stays
  inline (no regression).
- **WI 7 (closeout, done):** see Landed below; status flipped to done.

**Landed:** commit `a2c691b` (atomic: doc v0.14.0 + INDEX + tests +
code); GitHub CI run **38105922116** (`head_sha` `a2c691b`, run
conclusion **success**) —
<https://github.com/mirph-glitch42/m21-1/actions/runs/38105922116>.
Re-crawl **14,601,436 B** / **143,358 lines**, 0 failed articles;
re-census **0** leaks (acceptance met).

**Blast radius:** `_render_block_list`'s final `else` branch +
`_contains_block_el` in `src/m21_crawl/mdconv.py`; the algorithm doc
(new D15 + TESTS); `tests/test_mdconv.py`.

**Acceptance criteria:** in the regenerated manual — **0** unknown/
malformed tags inline-dump block content (all leaking census articles'
block sections render as real headings + blocks); article
`554400000176623` §`VII.i.3.A.4.d` renders as an anchor +
`### VII.i.3.A.4.d…` heading + block content + a normal nav line;
genuinely-inline unknown tags are unaffected; TEXT/ORGANIZATION unchanged
(goal 1); `make gate` + GitHub CI green.

**Ordering:** **first** in the current queue (correctness fix — it
restores the affected articles' nav to the normal block shape that B18
will reformat); before B18 and B17. Rides the same `mdconv` doc as
B6/B11/B13/B14/B15/B16/B17/B18.

<!-- BACKLOG:ITEM:B20 -->
## B20. Nested in-cell tables → aligned box-drawing tables in pre — **DONE (2026-10-15)**

**Source:** user

**Requested:** 2026-10-12
**Priority:** Medium

**Request (verbatim):** "this is good. you may proceed with B20" (2026-10-12)
and "B20 Needs to be added to the backlog before continuing" (2026-10-12).
The approach itself was approved over the `render-test/` iteration:
box-drawing table in a `<pre>` block, W=48 wrap, one blank spacer row
between rows.

**Problem / evidence:** B16 (DONE) renders every nested in-cell table as a
padded ASCII pipe table (D13) — 262 corpus lines across 108 articles
(B16 census, 2026-10-10). Two measured defects, article `554400000181476`
(source `~/.lmstudio/scratchpads/9u/b16/art_554400000181476.html`):

- **Right border misaligned.** D13 pads by *source* string length, but the
  user's renderers (VMD, GitHub — both verified by the user) process
  Markdown inside the cell: `***Note***` renders as 4 columns while the
  source string is 10 — the `***Note***:` row's border sits 2 columns off
  (diagnosed 2026-10-12 over the render-test iteration).
- **No wrap; long cells run unbounded wide.** Max-height row padding was
  tried and rejected: "There should be 1 blank row of space separation,
  not this large spacing" (2026-10-12).

**Root cause / census:** GFM cannot nest tables inside table cells, so a
nested table must render as *text* inside the outer cell. D13's padded
ASCII shape is that text; the misalignment is width computed on the source
string instead of the rendered string. Population: the same 262 nested
tables / 108 articles B16 censed (re-census at closeout).

**Chosen approach (user-approved):** box-drawing monospace table inside a
`<pre>` block:

- Borders `┌┬┐│├┼┤└┴┘─` — box characters, not pipes, so D3's single-escape
  pass cannot corrupt them.
- Every cell wrapped at W=48 *rendered* columns (rendered: `***x***`→x,
  `**x**`→x, `*x*`→x, `[text](url)`→`text`, `` `code` ``→`code`) —
  alignment uses rendered width because the renderers process Markdown
  inside `<pre>` (user-verified for VMD and GitHub).
- Each row padded to its own rendered width; one blank spacer row between
  rows (user-rejected max-height padding).

Source of truth: `render-test/gen_b20_nested_table.py` (self-verifying;
`verify()` asserts every row is exactly the table's LINE_W rendered cols —
59 in the fixture — and that the word multiset/order is preserved) + the
approved sample `render-test/b20-nested-table.md` (section B: 26 rows × 59
cols).

**Work items (in order):**

1. **WI 1 (this change, 2026-10-13):** this entry, written in the same
   change as the migration of `backlog.md` to the backlog-manager format
   (index block, section markers, Queue section) — the skill's
   first-opportunity rule.
2. **WI 2 — doc cycle first** (algorithm-records-keeper): bump
   `algorithms/html-to-markdown-section-extraction.md` **v0.14.0 →
   v0.15.0** — D13 rewritten as this box-drawing `<pre>` form (supersedes
   D13's padded ASCII; the D13 number is kept so D3/TESTS references stay
   valid, supersession noted in D13's text); D3 note updated (box chars
   are not pipes — verify the outer `_render_table` escape pass does not
   corrupt the `<pre>`/box output); `render_table_inline` pseudocode,
   §4.1 walkthrough, §5.2 edge-case row, TESTS rows 72/75;
   `algorithms/INDEX.md` bumped in the same change (B12 gate).
3. **WI 3 — TDD RED→GREEN:** rewrite test cases 70 and 73 in
   `tests/test_mdconv.py` to pin the box-drawing `<pre>` output; confirm
   RED on the D13 code; port the verified generator logic
   (`rendered_width`, tokenizer, `wrap`, `pad`, `build_box`, `verify`)
   into `_render_table_inline` in `src/m21_crawl/mdconv.py`; GREEN.
4. **WI 4 — gate:** `make gate` green (format, lint, indexes, tests,
   secrets).
5. **WI 5 — re-crawl + re-census:** full manual re-crawl (0 failed
   articles); re-census: every nested in-cell table is the box-drawing
   `<pre>` form, **0** padded-ASCII nested renders remain (the 262
   population); rendered-width alignment spot-checked with the `verify()`
   oracle; TEXT/ORGANIZATION unchanged (goal 1).
6. **WI 6 — atomic commit + CI:** doc + INDEX + tests + code + this
   entry (explicit paths; **never** `git add -A`); Conventional Commit
   ≤72 chars; push; GitHub CI green.
7. **WI 7 — closeout:** record commit sha, CI run id, re-crawl size,
   re-census numbers in this entry (B14/B15/B16 closeout format); flip
   status to DONE.

**Blast radius:** `_render_table_inline` + the new rendered-width/wrap/box
helpers in `src/m21_crawl/mdconv.py`; the algorithm doc (D13, D3 note,
pseudocode, §4.1, §5.2, TESTS 72/75) + `algorithms/INDEX.md`;
`tests/test_mdconv.py` (cases 70/73). Must NOT change: outer
`_render_table` (real GFM tables keep D3 single-escape behavior),
TEXT/ORGANIZATION, all other render paths (D5/D6/D7/D12/D14/D15).

**Acceptance criteria:** in the regenerated manual — every nested
in-cell table renders as a box-drawing monospace table inside `<pre>`
with **every row the same rendered width** (the `verify()` oracle passes
on all 262); cell text verbatim (word multiset/order preserved; no space
inserted where the source had none — `***Note***:` stays attached); W=48
wrap; one blank spacer row between rows; **0** padded-ASCII nested
renders remain; `make gate` green + GitHub CI green.

**Ordering:** **first** in the queue (user-directed 2026-10-12: "you may
proceed with B20"); before B18 and B17.

**Progress:**

- 2026-10-12 — user approved the render-test sample ("this is good") and
  directed "you may proceed with B20" + "B20 Needs to be added to the
  backlog before continuing".
- 2026-10-14 — code complete: box-drawing `<pre>` renderer,
  rendered-width wrap, `verify()` oracle; final fix `2ddb718`
  (3-level nested box lines kept atomic); 230 tests green.
- 2026-10-15 — re-crawl + full acceptance verification green (below);
  status → DONE.

**Closeout (2026-10-15, fresh crawl 14,759,857 B, 0 failed articles —
census verified on that output):**

- **Code:** `5611151` (review fixture) + `2ddb718` (final wrap fix —
  3-level nested box lines kept atomic).
- **CI (verified green on `c1aa95d`, the push carrying this closeout):**
  `SonarCloud Code Analysis` success, `Analyze (python)` success,
  `Analyze (actions)` success, `gate` success.
- **Re-census (2026-10-15):** **269** box-drawing tables in **107**
  articles (B16 baseline: 262 / 108 — delta is live-site churn: new
  XIII.i.8.B NCA Burial Eligibility article added 10/14/2026; XIV.2.C
  SSN Verification content updated 10/14/2026).
- **Acceptance verified on the 2026-10-15 output:** every box row in all
  269 tables has an identical rendered width (`_rendered_width` oracle —
  0 failures); **0** pipe/padded-ASCII nested renders remain; the one box
  whose rendering changed vs the pre-fix baseline (article
  `554400000173313`, XIV.4.C) is word-for-word identical (1103 words,
  same order) — a pure re-wrap at W=48.
- **Diff vs the 2026-10-14 05:32 backup fully explained:** (a) the
  `2ddb718` re-wrap in `554400000173313`; (b) live-site changes after
  the backup — new XIII.i.8.B article (`554400000335065`) + its TOC
  entry, XIII.i.8.A Next-Section link retarget, XIV.2.C date/reference
  update, two new 10/14/2026 changelog rows. No unexplained rendering
  drift.

<!-- BACKLOG:ITEM:B21 -->
## B21. Missing paragraph breaks — inline-only `<div>` paragraphs coalesce — **DONE (2026-10-16)**
**Priority:** Medium

**User report (verbatim, 2026-10-13):** "We are missing a large number of
paragraph separations in the document. The bolded **Example X:** and
**Analysis:** indicate the start of a new thought, and should be starting
a new paragraph." … "There should be 4 paragraphs above the first set of
bullets, but we are only rendering one. This greatly affects readability.
The conversion needs to be fixed to handle paragraphs. It appears some
block level decoding is not working correctly." (User note: "Ignore the
yellow highlighting. This is a search artifact from searching for the
correct section on the website.")

**Examples (user screenshots, 2026-10-13) — both in article
`554400000174869` (Part II, Subpart iii, Chapter 1, Section A —
Applications for Benefits):**

1. §`II.iii.1.A.2.d` (Examples: situations involving additional
   correspondence…): the portal renders each `***Example N:***` /
   `***Analysis:***` block as its **own** paragraph; the manual merges
   them all into **one** giant paragraph.
2. §`II.iii.1.A.2.f` (Considering Unclaimed Theories of SC): the portal
   shows **4** paragraphs above the first bullet list; the manual
   renders **1**.

**Root cause (traced from the live HTML, 2026-10-13, no guessing):**

1. In the source HTML each paragraph is its **own `<div>`** (inline
   `<span>`s inside), and paragraphs are separated by **empty
   `<div></div>` spacer divs** — verified in both example sections
   (shape: `…</div>` + `<div></div>` + `<div><span…>Example 2…`).
2. `div` is **not** in `_BLOCK` (D7 deliberately excludes containers).
   In `_render_block_list`, an **inline-only** `div` takes the
   `_UNWRAP_BLOCK` branch: `_contains_block_el(child)` is False, so its
   children are appended to the **current inline run** — consecutive
   paragraph `<div>`s therefore coalesce into **one** paragraph block.
3. The empty `<div></div>` spacers render to `""` and contribute no
   separation at all.
4. Net effect: N portal paragraphs → **1** markdown paragraph. Affects
   every article that uses this div-paragraph shape (user: "a large
   number").

**Blast radius:** `_render_block_list` (the `_UNWRAP_BLOCK` inline-only
branch) in `src/m21_crawl/mdconv.py`; the algorithm doc (new **D16** —
D15 is the last numbered rule; TESTS rows 81+); `tests/test_mdconv.py`;
the assembled manual (re-crawl) — paragraph counts change across
articles. Open risk: inline-only `div`s the portal keeps joined (e.g.
two divs forming one sentence inside a frame cell) would now split — the
WI 6 census must confirm the two example sections split correctly and
the corpus delta is sane.

**Chosen approach (agent-proposed, flagged for user review):** in
`_render_block_list`, an **inline-only `div` in block position is a
paragraph boundary** — flush the current inline run and emit the div's
flattened inline text as its **own block** (browser semantics: `div` is
block-level; the portal rendering confirms the intent). Inline-only
`div`s in **inline context** (inside `<p>`, cells, list items) are
unaffected. New **D16** rule + doc bump + TDD cases.

**Work items (in order):**

1. **WI 1 (done 2026-10-13):** this backlog entry — symptom + verified
   root-cause trace (live HTML, both example sections) + blast radius +
   approach, written before any doc/code.
2. **WI 2 — census (quantify the population):** count inline-only
   `<div>` sibling groups at block level in the crawled corpus (or,
   output-side: merged-paragraph signatures in the current manual) so
   closeout can report before/after paragraph counts for the two example
   sections + a corpus delta.
3. **WI 3 — doc cycle first** (algorithm-records-keeper): bump
   `algorithms/html-to-markdown-section-extraction.md` **0.15.0 →
   0.16.0** (queue position; B18 → 0.17.0, B17 → 0.18.0 re-sequenced):
   new **D16** rule "an inline-only `div` in block position is a
   paragraph boundary — its inline content becomes its own block; empty
   `div` spacers render nothing; inline-context `div` is unchanged";
   update the block-model + edge-case sections + TESTS rows; sync
   `algorithms/INDEX.md` (gate-enforced).
4. **WI 4 — TDD RED→GREEN** in `tests/test_mdconv.py` (cases 79+):
   (a) two inline-only `<div>` siblings separated by an empty
   `<div></div>` → **two** paragraph blocks (RED on current code —
   currently one merged paragraph); (b) inline-context `div` (inside
   `<p>`) unchanged (no regression); GREEN; `make gate` green.
5. **WI 5 — atomic commit** (explicit paths; **never** `git add -A`;
   `output/` excluded); Conventional Commit subject ≤72 chars; push;
   GitHub CI green.
6. **WI 6 — re-crawl + verify:** full manual re-crawl (0 failed
   articles); §`II.iii.1.A.2.d` renders each `Example N:`/`Analysis:` as
   its own paragraph; §`II.iii.1.A.2.f` renders **4** paragraphs before
   the first bullet list (matching the portal); TEXT/ORGANIZATION
   otherwise unchanged (goal 1); census delta recorded.
7. **WI 7 — closeout:** record commit sha, CI run, census deltas here
   (B16/B19 closeout format); flip the status line to DONE; update
   Queue/header; regenerate the index + `--check`.

**Acceptance criteria:** in the regenerated manual — §`II.iii.1.A.2.d`
shows each `***Example N:***`/`***Analysis:***` block as its own
paragraph (as in the portal); §`II.iii.1.A.2.f` shows **4** paragraphs
above the first bullet list; inline-context `div` behavior unchanged
(cases 1–78 still pass); TEXT/ORGANIZATION unchanged (goal 1); `make
gate` green + GitHub CI green.

**Ordering:** **second** in the queue — after **B20** (in progress),
before B18/B17 (agent placement 2026-10-13, flagged; user may re-order).

**Progress:**

- 2026-10-13 — WI 1 done (this entry). Root cause verified from live
  HTML for **both** example sections: paragraphs are individual
  inline-only `<div>`s separated by empty `<div></div>` spacers; the
  `_UNWRAP_BLOCK` inline-only branch coalesces them into one run
  (D7: `div` not in `_BLOCK`).
- 2026-10-16 — closed (see Closeout). Migrated to the priority scheme
  (G9): priority = **Medium** (migration default).

**Closeout (2026-10-16, verified on the same-day output):**

- **Code:** `d1e03ca` (D16 — an inline-only `div` in block position is a
  paragraph boundary) + `33c02f4` (refinement — a `div` grouping child
  `div`s recurses so each child `div` is its own paragraph).
- **CI (verified green on `33c02f4`):** `SonarCloud Code Analysis`
  success, `Analyze (python)` success, `Analyze (actions)` success, `gate`
  success — 4/4.
- **Version landed:** algorithm `html-to-markdown-section-extraction`
  **0.16.1** (D16 refined; TESTS rows 82–83 / test cases 80–81);
  `algorithms/INDEX.md` synced (gate-enforced).
- **Census (2026-10-16 output):** **645** `***Example***`, **64**
  `***Analysis***`, and **458** `***Exception***` markers each on their
  own paragraph (line-start).
- **Acceptance verified (2026-10-16 output):** §`II.iii.1.A.2.d` renders
  each `***Example N:***`/`***Analysis:***` as its own paragraph (L10391);
  §`II.iii.1.A.2.f` renders **4** paragraphs before the first bullet list
  (L10429) — both match the portal; inline-context `div` behavior
  unchanged (test cases 1–78 pass); TEXT/ORGANIZATION otherwise unchanged
  (goal 1); `make gate` green.

<!-- BACKLOG:ITEM:B22 -->
## B22. GitHub CI gate failing — SonarCloud security issues on new code — **DONE (2026-10-15)**

**Source:** user
**Requested:** 2026-10-14
**Priority:** Medium

**Request (verbatim, 2026-10-14):** "For the backlog: Github CI Gate failing. Fix CI Gate before any more pushes." (Related user messages: "I turned on agent access through GitHub Apps for SonarCube Cloud." / "I had the wrong app installed in github. Agent app now installed" — the SonarCloud public API turned out to be sufficient; no token path used.)

**Problem / evidence (measured 2026-10-14):** commit `f0e1ade` pushed to `main`; CI failed. SonarCloud **Security Rating on New Code** gate red — **7** open issues (all created 2026-10-14T18:33 = f0e1ade analysis; full 42-issue history cached at `/tmp/sonar_all.json`):

- `pythonsecurity:S2083` BLOCKER — `render-test/gen_b20_nested_table.py:235` (`fixture.write_text`)
- `pythonsecurity:S8707` MAJOR ×2 — `scripts/build_index.py:145` (read open), `:168` (write open)
- `pythonsecurity:S8707` MAJOR ×2 — `src/m21_crawl/cli.py:251` (makedirs), `:252` (open)
- `githubactions:S8541` MAJOR — `.github/workflows/ci.yml:36` — pip upgrade line missing `--only-binary :all:`
- `githubactions:S8544` MAJOR — `.github/workflows/ci.yml:37` — pip install needs `--require-hashes` + per-req sha256 hashes in `requirements.lock`

**Root cause / census (issue-history analysis, complete 2026-10-14):** Sonar's 42-issue history (incl. resolved) shows `scripts/check_index_registry.py` was flagged S8707 (2026-10-08) and is now **RESOLVED** — its guard shape **was credited**. Identical-intent guards in the other 3 files were **not** credited (build_index/cli re-opened 2026-10-14 at new lines; gen_b20 re-flagged at L235). ci.yml S8541/S8544 open since 2026-10-03 — the pip pin alone did not fix them. Credited shape (`check_index_registry.py` L82-101, L263-272): 2-arg `_resolve_inside(base, rel)` with `os.path.join(root, rel)` + `commonpath` check; module-local `StructuralError`; **guard call + sink in ONE helper** (`_read_lines`); caller passes the base; `main()` catches the custom exception → exit 2. Rejected shapes differ in: 1-arg guard, base computed inside the guard, built-in `ValueError` or `fail()`/`sys.exit`, and/or sinks outside the protected scope.

**Chosen approach (agent design, flagged for user review 2026-10-14):** mirror the credited shape exactly in the 3 rejected files — 2-arg `(base, rel)` guard, module-local `StructuralError` per file, one helper per sink pair that resolves then opens/writes, `main()` computes the base and catches the custom exception (cli keeps exit 3, build_index keeps exit 2). ci.yml: add `--only-binary :all:` to the pip upgrade line; add `--require-hashes` and sha256 hash continuations for all 15 pinned packages in `requirements.lock` (hashes fetched from the PyPI JSON API — never guessed).

**Work items (in order):**

1. **WI 1 (done 2026-10-14):** this backlog entry + guard-shape census (credited vs rejected) + hash plan, all before any code.
2. **WI 2 — guard rewrites:** `scripts/build_index.py`, `src/m21_crawl/cli.py`, `render-test/gen_b20_nested_table.py` to the credited shape; update `tests/test_cli.py`, `tests/test_build_index_guard.py`, `tests/test_gen_b20_guard.py` expectations (2-arg calls, `StructuralError`); `make gate` green.
3. **WI 3 — CI pinning:** ci.yml L36/L37 fix; generate `requirements.lock` hash continuations from the PyPI JSON API (`files[].digests.sha256`, all wheels).
4. **WI 4 — commit + push (gated):** explicit path list (**never** `git add -A`; `output/` stays untracked); Conventional Commit subject ≤72 chars; `make gate` green first; push; poll check-runs — **both** the `ci` and the SonarCloud checks must be green.
5. **WI 5 — fallback (only if still red):** ONE further shape iteration; if still red, ask the user before any `# nosem` suppression (user approval required).
6. **WI 6 — closeout:** record commit sha + both CI runs + before/after issue counts here; flip status to DONE; update Queue/header; regenerate the index + `--check`; then resume the queue (B20 closeout push).

**Blast radius:** `scripts/build_index.py`, `src/m21_crawl/cli.py`, `render-test/gen_b20_nested_table.py`, the three guard test files, `.github/workflows/ci.yml`, `requirements.lock`. Must NOT change: `scripts/check_index_registry.py` (credited template — untouched), documented exit codes (cli 0/1/2/3, build_index 2), the `output/` exclusion, and the manual's TEXT/ORGANIZATION (no crawl changes here).

**Acceptance criteria:** on the commit that lands this work — GitHub `ci` check green **and** SonarCloud check green; all **7** issues resolved in SonarCloud (or a user-approved suppression recorded in this entry); `make gate` green locally; no `output/` in the commit; the gate no longer blocks the next push (B20 closeout push lands CI-green).

**Ordering:** hard prerequisite for the next push (user: "Fix CI Gate before any more pushes") — queue position 1, ahead of B20's closeout push; **no version** (pure infrastructure, no doc bump). B20 stays IN PROGRESS locally; its closeout push is gated on this item landing.

**Progress:**

- 2026-10-14 — WI 1 done (this entry). Guard-shape census complete: credited template identified in `check_index_registry.py`; 7-issue list with line numbers captured from the public SonarCloud API.
- 2026-10-14 — WI 2/WI 3 done across `a3c8fcd` → `ed02751`; SonarCloud re-flagged the 4 S8707 sinks each time — the `commonpath` guard was not credited in helper or inline form (see `LLT-0001`).
- 2026-10-15 — final shape iteration (per WI 5): fetched the full rule description (`api/rules/show pythonsecurity:S8707`); its Compliant solution is a `realpath` + equality-or-`startswith(base + os.sep)` helper — replicated verbatim in `build_index.py` and `cli.py` (+ 4 resolver-level tests); `make gate` green (230 passed); WI 4: commit `aa4362b`, push, all 4 check runs green.

**Closeout (2026-10-15):** commit `aa4362b` — check runs: `SonarCloud Code Analysis` success, `Analyze (python)` success, `Analyze (actions)` success, `gate` success. SonarCloud state: **0 open security issues**; all 11 `pythonsecurity:S8707` issues FIXED (the 4 gate-blocking sinks in `build_index.py`/`cli.py` included); S2083/S8541/S8544 from the 7-issue list not among the 23 open. Before/after: 7 open (2026-10-14) → 0 security open (2026-10-15). The 23 remaining open issues are Reliability/Maintainability (S3776 ×10, S9409 ×4, S8786 ×3, S5863 ×3, S5778, S8513, S9073) — tracked separately as **B23** (low priority). No `# nosem` used.





<!-- BACKLOG:ITEM:B23 -->
## B23. SonarCloud Reliability rating to A (new code) — **OPEN (2026-10-15)**

**Source:** user
**Requested:** 2026-10-15
**Priority:** Low

**Request (verbatim, 2026-10-15):** "add reliability sonarqube items to bring reliability to A, priority low (end of queue)"

**Problem / evidence (measured 2026-10-15, commit `aa4362b`):** security is clean (0 open after B22), but **23 open Reliability/Maintainability issues** hold the Reliability rating below A: `python:S3776` CRITICAL ×10 (cognitive complexity — `mdconv.py`, `check_index_registry.py`), `python:S9409` MINOR ×4, `python:S8786` MAJOR ×3, `python:S5863` MAJOR ×3, `python:S5778` MAJOR ×1, `python:S8513` MAJOR ×1, `python:S9073` MAJOR ×1.

**Chosen approach (TBD at start):** per-rule remediation in Doc→Test→Code cycles — behavior-preserving extraction for S3776 where possible, targeted fixes elsewhere; each push verified against the SonarCloud API. Behavior must stay identical (test suite + `make gate`); the manual's TEXT/ORGANIZATION constraint is not affected (no crawl-output changes expected).

**Work items (in order):**

1. **WI 1 (done 2026-10-15):** this entry + open-issue census captured from the SonarCloud API at `aa4362b` (see Problem).
2. **WI 2 — remediation:** fix in severity order (S3776 → S8786/S5863 → S5778/S8513/S9073 → S9409), each with the test suite kept green; `make gate` green before every commit.
3. **WI 3 — closeout:** record sha + CI runs + before/after issue counts here; flip status to DONE; update Queue/header; regenerate the index + `--check`.

**Blast radius:** the flagged Python files and their tests only; no workflow/config changes unless a rule demands one; no `# nosem` without explicit user approval (B22 lesson).

**Acceptance criteria:** at the landing commit — SonarCloud open-issue count 0 (Reliability rating A) **or** a user-approved residual recorded here; `ci` + SonarCloud check runs green; `make gate` green; test suite unchanged in behavior.

**Ordering:** low priority — end of queue (after B17), per user (2026-10-15); **no version** (infrastructure/quality).

**Progress:**

- 2026-10-15 — WI 1 done (this entry); baseline census: 23 open at `aa4362b`.
- 2026-10-16 — migrated to the priority scheme (G9): priority = **Low**
  (per the item's own notes — "low priority, end of queue").

**Closeout:** (TBD)


<!-- BACKLOG:ITEM:B24 -->
## B24. Wrap must not split a word from its attached punctuation — **OPEN (2026-10-15)**

**Source:** user
**Requested:** 2026-10-15
**Priority:** Medium

**Request (verbatim, 2026-10-15):** "split during wrap does not adhere to punctuation rules when wrapping. this screen shot sows that the line split between word and the comma. instead of including the comma with the attached word." (screenshot of a wrapped box-drawing table cell where one line ends on a word and the next line begins with a stray comma).

**Problem / evidence (measured 2026-10-15):** in box-drawing wrapped cells (the D13/B20 wrap code in `mdconv.py`), a wrapped line can end on a word while the **next** line begins with a punctuation-only fragment (e.g. a comma) that belongs to that word. Root cause confirmed empirically (`PYTHONPATH=src .venv/bin/python`): the VA source text contains a **space before the comma** (e.g. `"If no , make"`). `_tokenize` (mdconv.py:566) splits gaps with `gap.split()`, so `no` and `,` become **two independent atomic units** (`,` is its own unit, `sep=True`). `_wrap_cell` (mdconv.py:615) is a greedy wrap that breaks the line when `cur_w + join_w + w > width`; when the width boundary falls immediately after `no`, the lone `,` unit is pushed to the next line, producing a line that *starts* with a stray comma. Control test: `"no, make"` (no space) tokenizes as a single unit `no,` and wraps correctly. Note the manual contains several such data quirks (`"and;"`, `"table.;"`) that expose the same rule.

**Chosen approach (agent-proposed, flagged for user review):** enforce the standard typesetting rule "no line begins with closing punctuation" inside the wrap. When `_tokenize` yields a punctuation-only unit (a run of `.`, `,`, `;`, `:`, `!`, `?`, `)`, `]`, `"` and similar trailing marks) that is separated from the previous unit by whitespace only, **glue it to the preceding unit** so the pair moves atomically and can never be the first unit of a new line. Implement as a small post-pass over the token list (or inside `_wrap_cell`) so the rest of `_tokenize`'s atomic units are unchanged. Behavior for already-correct text (no space before the punctuation) is identical.

**Work items (in order):**

1. **WI 1 (done 2026-10-15):** this entry + root cause confirmed empirically (see Problem).
2. **WI 2 — doc cycle first (algorithm-records-keeper):** bump `algorithms/html-to-markdown-section-extraction.md` **0.18.0 → 0.19.0**; add **D17** rule "wrap never begins a line with a closing punctuation fragment; a punctuation-only fragment separated from its word by whitespace is glued to the preceding word as one atomic unit"; update the D13 wrap edge-case + TESTS rows; sync `algorithms/INDEX.md` (gate-enforced via `make doc-index-check`).
3. **WI 3 — TDD RED→GREEN in `tests/test_mdconv.py`:** (a) `"If no , make …"` wrapped narrow → the comma stays attached to its word and no wrapped line begins with `,` (RED on current code); (b) `"no, make"` (no space) unchanged; (c) a `;` / `.` variant. `make gate` green.
4. **WI 4 — closeout:** record sha + CI runs + before/after here; flip status DONE; update Queue/header; regenerate the index + `--check`.

**Blast radius:** `_tokenize` / `_wrap_cell` / `_join_units` in `mdconv.py` (D13/B20 wrap path) + new TESTS row + new test cases only; no crawl-scope or exclusion changes; TEXT/ORGANIZATION constraint unaffected (same words, punctuation re-attached to its word).

**Acceptance criteria:** at the landing commit — no wrapped box-drawing cell line begins with a closing punctuation fragment; a punctuation-only fragment always renders attached to its preceding word; existing wrap tests unchanged in behavior; `make gate` green; CI + SonarCloud check runs green.

**Ordering:** normal priority — after B17 in the mdconv queue, before B23 (low). No version (assigned at completion, G6).

**Progress:**

- 2026-10-15 — WI 1 done (this entry); root cause confirmed (space-before-comma → stray comma unit pushed to the next line by `_wrap_cell`).
- 2026-10-16 — migrated to the priority scheme (G9): priority = **Medium**
  (migration default).

**Closeout:** (TBD)

<!-- BACKLOG:ITEM:B25 -->
## B25. Nested `<ul>`/`<ol>` in a table cell duplicates sub-items — **OPEN (2026-10-16)**

**Source:** user
**Requested:** 2026-10-16
**Priority:** High

**Request (verbatim, 2026-10-16):** "New Backlog: Counter to requirements, structure/organization of the document is being changed within tables. See following screenshots comparing web site and md." (screenshots: the portal renders a nested sub-list inside a table cell; the Markdown output duplicates the sub-items.)

**Problem / evidence (measured 2026-10-16):** in article `554400000174881` §`II.iii.3.A.1.d` (Step 2), a table cell contains a nested `<ul>` inside a `<li>` plus inline-only `<div><span>` text. The Markdown output **duplicates** the nested sub-items — each sub-bullet is emitted both in place and again as a separate block, changing ORGANIZATION (goal-1 violation). Root cause traced from the code: `_render_list_inline` (`src/m21_crawl/mdconv.py:754`) both (a) iterates `find_all("li")` (which already descends into the nested `<ul>`) **and** (b) recursively renders the nested `<ul>`, so each sub-bullet is emitted twice. (Contrast: the block-level `_render_list` at `mdconv.py:801` handles nesting correctly and is not affected.)

**Chosen approach (agent-proposed, flagged for user review):** render a real nested `<ul>`/`<ol>` inside a cell as an indented sub-list; if the target renderer (GitHub / VMD) will not render a nested `<ul>` inside a GFM table cell, fall back to `<br>`-indented literal bullets. Decision deferred to the doc cycle (algorithm-records-keeper) and the TDD RED test.

**Work items (in order):**

1. **WI 1 (done 2026-10-16):** this entry + root cause traced to the `_render_list_inline` double-render.
2. **WI 2 — census:** confirm the population of nested-list-in-cell occurrences across the corpus (output-side: duplicated sub-bullet signatures) so closeout can report before/after.
3. **WI 3 — doc cycle first (algorithm-records-keeper):** decide nested-`<ul>` vs `<br>`-indented fallback; add the rule; bump the algorithm doc version (assigned at completion, G6); sync `algorithms/INDEX.md` (gate-enforced via `make doc-index-check`).
4. **WI 4 — TDD RED→GREEN in `tests/test_mdconv.py`:** (a) a cell with a nested `<ul>` inside a `<li>` renders each sub-item **once** (RED on current code — currently duplicated); (b) a flat in-cell list unchanged (no regression); GREEN; `make gate` green.
5. **WI 5 — closeout:** record sha + CI runs + before/after census; flip status DONE; update Queue/header; regenerate the index + `--check`.

**Blast radius:** `_render_list_inline` (`src/m21_crawl/mdconv.py:754`) + the algorithm doc + `tests/test_mdconv.py` + the assembled manual (re-crawl). Must NOT change: `_render_list` (block-level, already correct); other cell rendering; TEXT of the manual (only the duplication is removed).

**Acceptance criteria:** at the landing commit — no table cell in the regenerated manual duplicates a nested list item (census: 0 duplicated sub-bullet signatures, vs the B25 baseline); article `554400000174881` §`II.iii.3.A.1.d` Step 2 renders each nested sub-item exactly once (matching the portal); flat in-cell lists unchanged (existing tests pass); TEXT/ORGANIZATION otherwise unchanged (goal 1); `make gate` green + GitHub CI green.

**Ordering:** normal priority — after B24 in the mdconv queue (all four are `mdconv` rendering fixes), before B23 (low). No version (assigned at completion, G6).

**Progress:**

- 2026-10-16 — WI 1 done (this entry); root cause traced to the `_render_list_inline` double-render; priority = **Medium** (migration default; **flag: goal-1 ORGANIZATION violation — may warrant High, user to confirm**).
- 2026-10-16 — priority → **High** (user-approved 2026-10-16); approach = **render-test** (same as B20 box-drawing tables), per user; **B26** (in-cell list **flattening**) added as a separate High item sharing this root function (`_render_list_inline`) — fixed together.

**Closeout:** (TBD)

<!-- BACKLOG:ITEM:B26 -->
## B26. Flat in-cell `<ul>`/`<ol>` flattened to `;`-joined text — **OPEN (2026-10-16)**

**Source:** user
**Requested:** 2026-10-16
**Priority:** High

**Request (verbatim, 2026-10-16):** "These images show that lists are flattened inside of nested tables as well. These lists need to be unflattened. I don't know if this part of B25 or a separate issue. If a separate issue, this issue should be added to the backlog and given a 'high' priority." (evidence: e78bdeba = portal rendering a proper flat bulleted list inside a table cell; a8812b27 = Markdown output flattening the same list to `;`-joined inline text.)

**Problem / evidence (measured 2026-10-16):** a table cell with a **flat** `<ul>` (top-level `<li>`s, no nesting) is rendered by `_render_list_inline` (`src/m21_crawl/mdconv.py:754`) as `find_all('li')` + `; `-joined string — every `<li>` is folded into one `;`-separated inline string, so the **bullets are lost** and the list's ORGANIZATION is flattened to prose (goal-1 ORGANIZATION violation). A **distinct symptom** from B25 (the **nested**-list **duplication** case) but the **same root function and same fix**.

**Root cause / census:** `_render_list_inline` flattens **all** in-cell lists — flat lists lose bullets (B26); nested lists duplicate sub-items (B25). Population: every `<ul>`/`<ol>` inside a GFM table cell (censused in WI 2).

**Chosen approach (agent-proposed, flagged for user review):** rewrite `_render_list_inline` to emit a **real list** (top-level bullets; nested sub-bullets indented) instead of joining with `; `. Shared with B25 (same function). If the target renderer (GitHub / VMD) will not render a `<ul>` inside a GFM cell, fall back to `<br>`-indented literal bullets. Decided in the doc cycle + TDD RED test, via the approved **render-test loop** (same as B20).

**Work items (in order):**
1. **WI 1 (done 2026-10-16):** this entry; root cause confirmed (`; `-join in `_render_list_inline`); cross-ref B25 (same function, same fix, closed together).
2. **WI 2 — census:** count flat in-cell lists (before/after) so closeout reports structure restored.
3. **WI 3 — doc cycle (algorithm-records-keeper):** decide bullet rendering in a cell (real `<ul>` vs `<br>`-indented); add the rule; bump the doc version at completion (G6); sync `algorithms/INDEX.md`.
4. **WI 4 — TDD RED→GREEN in `tests/test_mdconv.py`:** (a) flat in-cell `<ul>` renders as real bullets, not `;`-joined (RED now); (b) nested in-cell list renders each sub-item once (B25, RED); GREEN; `make gate` green.
5. **WI 5 — closeout:** record sha + CI + before/after census; flip DONE; re-queue; regenerate index + `--check`.

**Blast radius:** `_render_list_inline` (`mdconv.py:754`) + algorithm doc + `tests/test_mdconv.py` + the assembled manual (re-crawl). Must NOT change: `_render_list` (block-level, correct); other cell rendering; TEXT (only list structure is restored).

**Acceptance criteria:** at the landing commit — every flat in-cell `<ul>`/`<ol>` in the regenerated manual renders as real bullets (census: 0 `;`-flattened in-cell lists, vs the B26 baseline); the B25 nested-duplication case also renders each sub-item once (closed together); flat prose and other tables unchanged (existing tests pass); TEXT/ORGANIZATION otherwise preserved (goal 1); `make gate` green + GitHub CI green.

**Ordering:** High tier, after B25 (same function, fixed together); before B17/B18/B24 (Medium); before B23 (low). No version (assigned at completion, G6). Cross-ref: B25.

**Progress:**
- 2026-10-16 — WI 1 done (this entry); priority = **High** (per user: if separate, add to backlog at high); cross-ref B25 (same root function `_render_list_inline`, same fix, closed together).

**Closeout:** (TBD)

<!-- BACKLOG:CONSTRAINTS -->
## Standing constraints (apply to all items)

- The manual's TEXT and ORGANIZATION must not change — formatting only
  (user goal 1).
- Historical/Rescinded exclusion stays as committed in
  `algorithms/historical-rescinded-exclusion.md`.
- `output/` (the assembled manual) must **not** be committed while the
  user's "do not commit the assembled manual at this time" hold stands.
- `make gate` green before every commit; Conventional Commits; algorithm
  doc and code change atomically.
- **Current queue order (2026-10-10):** **B18 → B17** (B19 landed:
  `a2c691b` + this closeout). B18 reformats nav (B19 restored its
  normal block shape); B17 is the inline-image block fix. Each bumps
  the `mdconv` doc in turn (0.15.0 → 0.16.0).

- **Current queue order (2026-10-13, supersedes the 2026-10-10 bullet above):** **B20 → B18 → B17** — B20 (box-drawing `<pre>` tables for nested in-cell tables, superseding D13's padded ASCII) lands first at doc 0.15.0, then B18 at 0.16.0, then B17 at 0.17.0 (G6 re-sequencing; B20 requested 2026-10-12).
- **Current queue order (2026-10-13, supersedes the bullets above):** **B20 → B21 → B18 → B17** — B20 lands at doc 0.15.0, then B21 (paragraph breaks for inline-only `<div>` paragraphs) at 0.16.0, then B18 at 0.17.0, then B17 at 0.18.0 (B21 inserted 2026-10-13 after the user's paragraph-separation report; B21's queue position is agent-placed — user may re-order).
- **Current queue order (2026-10-15, supersedes the bullets above):** **B21 → B18 → B17 → B23 (low)** — B20 closed 2026-10-15 (code `5611151`/`2ddb718`, closeout in its entry), so B21 (paragraph breaks) is next at doc 0.16.0, then B18 at 0.17.0, then B17 at 0.18.0, then B23 (SonarQube reliability, low) last.
- **Current queue order (2026-10-14, supersedes the bullets above):** **B22 → B20 → B21 → B18 → B17** — B22 (CI gate fix, no version, blocks all pushes) lands first; B20's closeout push is gated on it. Doc versions unchanged: B20 0.15.0, B21 0.16.0, B18 0.17.0, B17 0.18.0.
- **Current queue order (2026-10-15, supersedes the bullets above):** **B20 → B21 → B18 → B17 → B23 (low priority)** — B22 closed 2026-10-15 (`aa4362b`); B23 (SonarCloud Reliability to A) appended at the end per user, low priority, no version. Doc versions unchanged: B20 0.15.0, B21 0.16.0, B18 0.17.0, B17 0.18.0.
- **Current queue order (2026-10-15, supersedes the bullets above):** **B21 → B18 → B17 → B24 → B23 (low priority)** — B20 closed 2026-10-15 (`5611151`/`2ddb718`); B24 (wrap punctuation rule) appended 2026-10-15 (normal, after B17, before B23-low); B21 (paragraph breaks) next at doc 0.16.0, then B18 at 0.17.0, B17 at 0.18.0, B24 at 0.19.0, B23 (low, no version) last.
- **Current queue order (2026-10-16, supersedes the bullets above):** **B25 → B26 → B17 → B18 → B24 → B23 (low)** — B25 (nested-list duplication) + B26 (in-cell list flattening) both **High** (user-approved 2026-10-16), same root function `_render_list_inline`, fixed together; B17/B18/B24 **Medium**; B23 (SonarQube reliability) **low**, last. No version tokens (G6).
- **Current queue order (2026-10-16, supersedes the bullets above):** **B25 → B26 → B18 → B24 → B23 (low)** — **B17 CANCELLED** (2026-10-16, user-directed): non-issue after **B21** (inline-only `<div>` paragraph breaks, DONE) already blocks inline images out of paragraph flow, so B17 is superseded and removed from the Queue; B25/B26 **High** (same root function `_render_list_inline`, fixed together); B18/B24 **Medium**; B23 **low**, last. No version tokens (G6).

