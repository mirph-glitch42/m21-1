# Backlog

Deferred work, recorded 2026-10-04. Each item is written so the next
session can start without re-deriving context: problem (with measured
evidence), blast radius, the process the governing skills require, open
decisions, and acceptance criteria.

Order = user priority. Status: **B1, B2, B3, B5 done**; **B4 open — direction signed off 2026-10-06 (inline coalescing), implementation pending**.

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

## B4. Inline emphasis split into standalone paragraphs (goal-1 bug) — **open, root cause confirmed**

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
must re-verify it. Existing TESTS cases that currently encode the
fragmented output must be rewritten *first*.

**Required process (governing skills):** full algorithm-records-keeper
cycle — doc-first (new rule, e.g. "inline-run coalescing in block
context" + a TESTS row), RED tests, then code, `make gate` green, one
atomic commit. Not a tweak.

**Fix direction (proposed, needs sign-off):** in block context,
**coalesce consecutive inline children** (bare text nodes + inline tags
`em`/`strong`/`span`/`a`/`b`/`i`/`u`/`code`/`sup`/`sub`/`s`/…) into a
single inline-rendered paragraph; let only block-level children
(`p`/`h1`–`h6`/`ul`/`ol`/`table`/`blockquote`/`pre`/`hr`) delimit
blocks. Open sub-question: whether a lone emphasis that is itself a
complete label (e.g. a standalone `**References**`) should stay
standalone or join its neighbours — needs a precise rule + any enumerated
exceptions.

**Acceptance criteria:** the L2714 example renders as one sentence; the
count of emphasis/bold blocks sandwiched between non-empty text above and
below drops from ≈9,851 to ~0 (or to a small, enumerated set of
genuinely standalone labels); text and organization unchanged; existing
TESTS cases updated to the coalesced output; `make gate` green; doc +
tests + code in one commit.

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

## Standing constraints (apply to all items)

- The manual's TEXT and ORGANIZATION must not change — formatting only
  (user goal 1).
- Historical/Rescinded exclusion stays as committed in
  `algorithms/historical-rescinded-exclusion.md`.
- `output/` (the assembled manual) must **not** be committed while the
  user's "do not commit the assembled manual at this time" hold stands.
- `make gate` green before every commit; Conventional Commits; algorithm
  doc and code change atomically.
