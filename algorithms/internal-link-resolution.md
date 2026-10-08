# Internal Link Resolution (Cross-Article Hyperlinks → In-Document Anchors)

<!-- INDEX:BEGIN format=tsv version=1 -->
id	start_line	end_line
INDEX_BLOCK	3	13
METADATA	15	36
THEORY	37	377
PSEUDOCODE	378	529
WALKTHROUGH	530	621
IMPLEMENTATION	622	759
TESTS	760	806
REFERENCES	807	828
<!-- INDEX:END -->

<!-- SECTION:METADATA -->
## 1. Metadata

| Field | Value |
|---|---|
| Name | Internal link resolution — rewrite cross-article hyperlinks into in-document section anchors |
| Slug | internal-link-resolution |
| Version | 0.5.0 |
| Status | implemented |
| Author | Bionic agent (on behalf of murphyjj) |
| Created | 2026-10-03 |
| Last modified | 2026-10-08 |
| Status history | 0.1.0 (2026-10-03): initial draft — the assembled manual's ~14.4k cross-article hyperlinks (eGain article URLs) should become internal `#anchor` links to the target article's `## ` heading; links whose target id is absent from the manual stay as portal URLs · 0.2.0 (2026-10-04): implemented in `src/m21_crawl/assemble.py` (`_ARTICLE_LINK`, `heading_anchor`, `_internalize_links`, final pass in `assemble`) + 7 new tests in `tests/test_assemble.py`; slug worked-examples corrected to the renderer's triple-hyphen form · 0.3.0 (2026-10-06): B3 — anchors are now assigned in *document order* via a github-slugger occurrence replica (`Slugger`), with body-heading context (`_body_heading_texts`); C4 rewritten — duplicate article names map to their own heading's distinct `-N` slug, and an article name colliding with an earlier body heading is correctly suffixed · 0.4.0 (2026-10-07): B7 — the `## Table of Contents` is now a *linked* numbered list: each entry is `[name](#anchor)`, pointing at that article's own `## {name}` H2 anchor (the same id-keyed `anchor_by_id` map, so duplicate names still disambiguate). The anchor build is hoisted *ahead* of TOC rendering — the TOC is a heading-free list, so the slug walk and every existing anchor are unchanged — and `_internalize_links` leaves the TOC's `#`-fragment links untouched (they are not article-URL candidates), so the pass stays idempotent on the TOC; the TOC's visible text, numbering, and order are byte-identical (only link wrapping is added) · 0.5.0 (2026-10-08): B8 — a second pass resolves the manual's in-document `#fragment` links (intra-article links, `To Top` links) against the document's **defined-anchor set** (headings slugged in document order + raw `<a id>` named anchors; first-wins per lowercased key): stage 1 **canonicalizes** a case-variant fragment (e.g. `#…_top` vs defined `#…_Top`) to the exact defined spelling; stage 2 **remaps** a still-unresolved `art_{id}_…` fragment to the article's own `## ` H2 anchor (top of the article); exact matches, TOC links, external URLs, and fragments whose id is not in the manual pass through byte-identical (a dead ref is never fabricated). Verified 2026-10-08 on the 442-article manual: 23,068 internal links, 214 dead (91 case-variants + 123 truly absent, 168 distinct — 100% remappable) → post-fix re-census 0 dead |
| Languages | Python 3.12 (implementation); pseudocode is language-agnostic |
| Implementation location | src/m21_crawl/assemble.py — `_ARTICLE_LINK` L52; `_BODY_HEADING`/`_FENCE` L56–57; `_NAMED_ANCHOR` L65; `_FRAGMENT_LINK` L69; `_ART_ID` L72 (B8); `heading_anchor` L103–111; `Slugger` L114–133; `_body_heading_texts` L135–159; `_internalize_links` L162–175; `_defined_anchors` L178–214 (B8); `_resolve_fragment_links` L216–250 (B8); `_emitted_body` L263–275; anchor-hoist + linked TOC + both rewrite passes in `assemble` L288–338 (v0.5.0, 2026-10-08) |
| Time complexity | O(D + (N + H)·L) time: the B3/B7 document-order slug build O((N + H)·L) + two linear rewrite passes over D (article-URLs, then B8 fragments; the B8 anchor walk is O(D) and its canonical map O(A), A ≤ D) (see THEORY 2.4) |
| Space complexity | O(N + A + D) working space (id→anchor map of N entries; B8 canonical map of A anchors; the rewritten copy of D bytes) |
| Determinism | deterministic (pure string transform; map built in portal order) |
| Dependencies | `m21_crawl.assemble` (deduped article list + document string) |
| Thread safety | pure function over immutable input — safe to call concurrently |
| Related documents | [html-to-markdown-section-extraction](html-to-markdown-section-extraction.md), [historical-rescinded-exclusion](historical-rescinded-exclusion.md) |

<!-- SECTION:THEORY -->
## 2. Theory

### 2.1 Problem definition

**Input.** Two artifacts that `assemble` already holds:

1. the deduped article list `[(id, name), …]` in portal (document) order —
   the same list that produced the `## {name}` headings and the TOC;
2. the assembled document string (H1 + TOC + article blocks), after the
   completeness gates have passed.

**Output.** The same document with every *resolvable cross-article
hyperlink* rewritten from

```
[text](https://www.knowva.ebenefits.va.gov/system/ws/v11/ss/article/<id>)
```

to

```
[text](#<slug>)
```

where `<slug>` is the GitHub/GFM anchor of the target article's `## {name}`
heading. Everything else is byte-identical.

In addition (B7), the `## Table of Contents` list is emitted *linked*:
each entry `[name]` becomes `[name](#<slug>)`, where `<slug>` is that
entry's **own** article's `## {name}` H2 anchor (the same id-keyed
`anchor_by_id` map). The TOC's visible text, numbering, and order are
unchanged — only the link wrapping is added (goal 1: no text or
organization change).

In addition (B8), the manual's existing *in-document* `#fragment` links
(intra-article links and the per-article `To Top` links) are resolved
against the document's **defined-anchor set** — every heading's
document-order slug plus every raw `<a id>` named-anchor id (2.7):

- **stage 1 (canonicalize):** a fragment that differs only in case from a
  defined anchor (e.g. link `#art_…_top`, defined `art_…_Top`) is
  rewritten to the defined anchor's exact spelling, so case-sensitive
  renderers resolve it exactly as case-insensitive ones do;
- **stage 2 (remap):** a fragment that is still unresolved but of the
  form `art_{id}_…` with `{id}` in the manual is rewritten to that
  article's own `## {name}` H2 anchor — the article's first emitted
  anchor, i.e. its top;
- every other fragment (exact matches — including the TOC's own links —,
  external URLs, images, and fragments whose id is not in the manual)
  passes through byte-identical. A dead reference to an id that is
  absent is a portal-side broken ref: it is left as-is and enumerable,
  never fabricated into a fake anchor.

**Live scale (verified 2026-10-03 on the 442-article manual):**

| Observation | Value |
|---|---|
| article-URL hyperlinks (`/system/ws/vNN/ss/article/<id>`) | 14,447 |
| distinct hosts used by those links | 1 (`www.knowva.ebenefits.va.gov`) |
| duplicate article names among the 442 | 0 (→ every anchor is unambiguous) |
| intra-article `#anchor` links (e.g. `#1a`) | resolved by B8 (2.7); the dead ones are all `art_{id}_…` refs |
| in-document `#fragment` links (B8 census 2026-10-08) | 23,068 |
| defined anchors: heading slugs + `<a id>` named (B8) | 21,468 (21,464 unique; 0 case collisions) |
| dead internal links (B8) | 214 = 91 case-variants (91 distinct) + 123 truly-absent (77 distinct, 58 article ids; 100% remappable) |
| `To Top` links (B8) | 418 (417 exact `[To Top]`; 95 dead pre-fix; all live after the fix) |

**Contract.**

1. **Candidate shape.** Only Markdown link destinations matching the eGain
   article-URL form (any `http(s)` host, `/system/ws/v<digits>/ss/article/`,
   bare digit id, no query string) are candidates. This is exactly the shape
   `mdconv` canonicalizes (see
   [html-to-markdown-section-extraction](html-to-markdown-section-extraction.md),
   `_rewrite_url`).
2. **Resolve by id.** A candidate is rewritten iff its id is a key of the
   manual's deduped id set. The id — not the host or path host — is the
   canonical article identity.
3. **Anchor = heading slug of the target's `## {name}` heading**, computed
   with the GitHub/GFM slug rules (2.5).
4. **Document-order dedup (B3).** Anchors are assigned in the order the
   headings appear in the final document (H1 title, `## Table of Contents`,
   then each article's `## {name}` heading followed by its body headings).
   The first heading to claim a base slug keeps it; a later heading with
   the same base slug gets `-1`, `-2`, … (a github-slugger occurrence
   replica). Hence two articles sharing a name map to *distinct* anchors
   (the 2nd resolves to its own heading's `name-1`), and an article name
   that collides with an earlier body heading is suffixed so the link still
   lands on the article's own heading (2.6).
5. **Pure & deterministic.** Same input → byte-identical output; no
   timestamps, no randomness, no I/O.
6. **No link created or destroyed.** Only the *destination* of existing
   links changes; link text, order, count, and every non-candidate byte are
   untouched.
7. **Unknown targets stay external.** Links to ids not in the manual
   (other portals, articles excluded as Historical/Rescinded) keep their
   portal URL — they still resolve online, and faking an anchor would
   create dead in-document links.
8. **The TOC is linked (B7).** The `## Table of Contents` entries are
   emitted as `[name](#<slug>)` using the *same* id-keyed `anchor_by_id`
   map as cross-article links, so every TOC entry resolves to its
   article's own `## {name}` H2 anchor (duplicate names disambiguate via
   the Slugger's `-N` suffix). The TOC is a heading-free list — it
   contributes nothing to the slug walk — and its `#`-fragment links are
   not article-URL candidates, so `_internalize_links` leaves them
   untouched and the pass stays idempotent on the TOC. The TOC's visible
   text, numbering, and order are byte-identical (only link wrapping is
   added).
9. **Fragment isolation (B8).** Only bare `#fragment` link destinations
   — a `](` immediately followed by `#` with no `)` inside the
   destination — are candidates for stages 1–2. External URL
   destinations (even with a `#fragment` suffix), image URLs, and
   non-link text are never touched.
10. **Canonical existence (B8).** Every fragment rewritten by stage 1 or
    2 is byte-identical to a defined anchor in the document (a heading
    slug or a named-anchor id); the pass can never *introduce* a dead
    link (Invariant D).
11. **Top-of-article remap (B8).** A truly absent `art_{id}_…` fragment
    remaps to the article's `## ` H2 anchor (its first emitted anchor,
    i.e. its top). Link text, count, and order are unchanged; fragments
    whose id is not in the manual stay as-is (C7's identity recovery).

### 2.2 Why this approach

- **Location: `assemble`, not `mdconv`.** `mdconv.convert` is a pure
  per-article transformer; it deliberately knows nothing about the rest of
  the manual (its contract is "same input + same base_url → identical
  output"). Resolving cross-article links requires the *whole* manual's
  id→name set — assembly-level knowledge. Doing it here keeps the converter
  pure and avoids a two-pass crawl or a global map threaded through every
  converter call.
- **Single regex pass + dict lookup, not a Markdown parser.** The link form
  is machine-generated and uniform (mdconv is the only link producer). A
  full Markdown parser would add a dependency and a whole new failure
  surface to change one URL token.
- **Rejected alternatives.**
  1. *Resolve inside `mdconv` with a precomputed map* — rejected: forces
     the converter to depend on whole-manual state (violates its pinned
     purity contract and ~40 byte-exact tests).
  2. *Insert explicit anchor markers (`<a id=…>`)* — rejected: GitHub
     already derives anchors from headings; marker injection would
     duplicate every heading and change the visible document.
  3. *Keep URLs, add a link index appendix* — rejected: the links remain
     external; the point is in-document navigation.
- **Intra-article `#anchor` links (B8).** The manual's in-document
  `#fragment` links fall into two families. The `art_{id}_…` family is
  resolvable: its targets are the article's own headings or named
  anchors, so B8 canonicalizes case-variants and remaps the truly-absent
  ones to the article's own H2 (2.7). The *other* family — bare eGain
  marker positions (`#1a`, `<a name="1a">`) that mdconv dropped — has no
  target in the converted Markdown; restoring those would require
  anchor-position recording during HTML→Markdown conversion (a different,
  converter-side algorithm). The B8 census shows every dead fragment in
  this manual is `art_{id}_…`-shaped, so nothing of that kind remains
  after the fix.

### 2.3 Correctness argument

**Invariant A (candidate isolation).** A rewrite happens only inside a
`]( <article-URL> )` token. The pattern (3.1) requires the exact eGain
article-URL shape terminated by `)`. Non-candidate bytes — external URLs,
image URLs (`/img/…`), bare text, code spans, TOC lines, breadcrumbs, the
`> [content unavailable: …]` placeholder — contain no such token and pass
through verbatim (the substitution function returns the original substring
for every non-match, and `re.sub` copies non-matching spans as-is).

**Invariant B (anchor existence + uniqueness).** The id→anchor map is
built by walking the deduped list in the *same* order that emits the
headings, feeding each article's `## {name}` heading (and the body
headings that follow it) to the document-order `Slugger`. When the walk
reaches an article, the Slugger has already consumed the title, the TOC,
and every H2 + body heading of all earlier articles — exactly the context
GitHub sees when it slugs that heading. Hence every rewritten anchor is
precisely the slug GitHub assigns to that article's *own* heading: it
exists in the document and is unambiguous. With duplicate names each
article resolves to its own heading's distinct `-N` slug (C4, 2.6).

**Invariant C (identity of the rest).** The rewrite is a function of the
matched substring alone (id lookup is exact string equality). Link text is
outside the match, so it is untouched.

**Sketch.** Each `](…)` token either matches the article-URL shape or not.
If not: byte-identical (A). If yes: id lookup either succeeds → replaced
by the anchor of an existing heading (B), or fails → original substring
returned (A). No other code path mutates the document.

**Invariant D (canonical existence, B8).** Every fragment rewritten by
stage 1 or 2 is byte-identical to an anchor the document actually
defines — a heading slug or a `<a id>` id. Stage 1 rewrites only to
values of the defined-anchor set; stage 2 only to
`anchor_by_id[id]` (the article's own H2 slug, itself a heading slug).
Hence the fragment pass can never *introduce* a dead link: the dead
count can only decrease.

**Invariant E (identity of the rest, B8).** A fragment passes through
unchanged unless it (a) exactly names a defined anchor (kept verbatim —
this is what saves the TOC's own links), (b) is a case-variant of one,
or (c) is `art_{id}_…` with a known id. External URL destinations,
image URLs, and fragments whose id is not in the manual match no rewrite
rule and are byte-identical (C7). □

### 2.4 Complexity

Document of size D bytes, N articles, average name length L:

- map build: O(N) inserts + O(N·L) slug work (each name scanned once);
- rewrite: one left-to-right regex scan of D with a constant-size pattern
  (no nested quantifiers — see 3.1) → O(D);
- total: **O(D + N·L) time, O(N + D) space** (the map plus the rewritten
  copy). The rewrite dominates on the live manual (D ≈ 13.7 MB, N = 442).
  Both terms are linear; no quadratic behavior is possible because the
  pattern has no backtracking loops.
- B8 fragment pass: one fence-aware line walk collecting the defined
  anchor set (O(D) + A inserts, A ≤ D) + one lowercased canonical map
  (O(A) hash work) + one left-to-right `re.sub` scan of D → **O(D) time,
  O(A + D) space** on top of the above. Still linear; the live pass
  measures well under 1 s (6.2).

### 2.5 Slug rules (GitHub/GFM)

`heading_anchor(heading)` — the anchor a Markdown renderer (GitHub,
VS Code, most GFM viewers) assigns to `## {heading}`:

1. case-fold to lowercase (Unicode-aware);
2. keep Unicode letters and digits, spaces, and hyphens; drop every other
   character (commas, periods, quotes, dashes that are not `-`);
3. replace each space with one hyphen.

Worked: `M21-1, Part II, Subpart iii, Chapter 2, Section H - X` →
`m21-1-part-ii-subpart-iii-chapter-2-section-h---x` (note the *triple*
hyphen from ` - `: spaces become hyphens and the existing hyphen stays).

### 2.6 Document-order dedup (the Slugger, B3)

`heading_anchor` gives a heading's *base* slug. But GitHub assigns the
visible anchor in **document order**: the first heading to claim a base
slug keeps it, and every later heading that slugs to the same base gets a
`-1`, `-2`, … suffix (github-slugger's `occurrences` logic). Because the
assembled manual carries thousands of body headings (the promoted frame
labels such as `I.i.1.A.1.a.`) plus one H2 per article, a base slug is
often claimed *before* an article's H2 reaches it — so the article's own
heading receives the suffix, and a link hard-wired to the unsuffixed base
slug is dead.

`Slugger` reproduces exactly that occurrence counting on top of the
*unchanged* `heading_anchor` base slug:

1. `slug(text)` → `base = heading_anchor(text)`. Emphasis markers such as
   `**` are dropped because they are not alnum/space/hyphen — matching
   GitHub, which slugs the *rendered* text (so `**Reorganization Matrix**`
   and `Reorganization Matrix` share a base slug);
2. if `base` has not been seen → return `base` and record it as seen (0);
3. if `base` was already seen `k` times → return `base-k` and record it as
   seen `k+1` times (1st → `base`, 2nd → `base-1`, 3rd → `base-2`, …).

The walk that feeds the Slugger is the final document's heading order: the
H1 title, the `## Table of Contents` heading, then for each article its
`## {name}` H2 followed by its body headings in order (fenced code blocks
skipped — 5.2). By the time the walk reaches an article, the Slugger has
already consumed the title, the TOC, and every H2 + body heading of all
*earlier* articles — precisely the context GitHub sees when it slugs that
article's heading. The article's own anchor is the Slugger's return value
for its H2.

**Why the base slug is unchanged.** `heading_anchor` already agrees with
GitHub on the base form (verified: 0 mismatches across all 442 article
headings). B3 only layers the occurrence dedup on top; it does not change
how a single heading is slugged.

**Named anchors (B8 context).** Besides headings, the document defines
anchors with explicit `<a id="…" name="…"></a>` markers (mdconv preserves
eGain's named markers; 9,507 in the live manual). A renderer resolves a
`#fragment` link against *both* heading slugs and named-anchor ids. The
id→anchor map `anchor_by_id` (headings only) is therefore the *remap*
authority (stage 2), while the full *defined-anchor set* — heading slugs
plus named ids — is the *canonicalization* authority (stage 1, 2.7).

### 2.7 Defined-anchor set and fragment resolution (B8)

**Defined anchor set.** The anchors a renderer resolves against in the
final document are exactly: (a) every heading's document-order slug (the
`Slugger`'s return values, 2.6 — H1, `## Table of Contents`, every
article H2, every body heading; fenced code blocks skipped), plus
(b) every raw `<a id="X">` named-anchor id, taken verbatim (a renderer
uses the id as-is — it is *not* slugged). `defined_anchors(document)`
walks the document once, fence-aware, collecting both families in
document order.

**Two-stage resolution.** Given the anchor set and the id→anchor map:

1. **Stage 1 — canonicalize (case-folded lookup).** For each link whose
   destination is a bare `#fragment`: if the fragment is an exact member
   of the anchor set → keep verbatim (this is what saves the TOC's own
   links). Otherwise, if `fragment.lower()` equals the lowercased form of
   some defined anchor → rewrite to that anchor's *exact* spelling
   (first definition wins, document order). This repairs case-variants
   such as link `#art_…_top` vs defined `art_…_Top`, in either
   direction.
2. **Stage 2 — remap to top of article.** If still unresolved and the
   fragment matches `art_{digits}_…` and that id is in the manual →
   rewrite to `anchor_by_id[id]`, the article's own H2 slug — its first
   emitted anchor, i.e. its top. This repairs the `To Top`-style refs
   whose exact marker (e.g. `<a id="art_…_top">`) mdconv dropped while
   the article heading survived.

Everything else — external URLs, images, fragments whose id is not in
the manual, fragments that are neither exact, case-variant, nor
`art_{id}` — passes through byte-identical. A dead reference is never
*fabricated*: the pass only ever rewrites to anchors that provably
exist (Invariant D).

**Why stage 1 before stage 2.** Stage 2's rewrite target
(`anchor_by_id`) is always a heading slug and therefore already in the
anchor set; running canonicalization first means stage 2 only fires on
fragments stage 1 couldn't fix, and the combined pass is idempotent — a
second pass finds every rewritten fragment exact-defined and rewrites
nothing.

**Scale (live, 2026-10-08).** 23,068 in-document `#` links; 21,468
defined anchors (21,464 unique, 0 case collisions); 214 dead = 91
case-variant (91 distinct) + 123 truly-absent (77 distinct) instances —
all 168 distinct fragments are `art_{id}_…` with a known id (100%
remappable). Post-fix re-census: 0 dead internal links; all 418 `to top`
links live.

### 2.8 Deviations

- **Stage 2 remaps to the article's H2, not to a "top" marker.** The
  manual's `To Top` links point at per-article `<a id="art_{id}_top">`
  markers that mdconv drops; the article's own H2 is the nearest
  surviving anchor (the article's top). Visible link text (`To Top`) is
  preserved — only the destination changes (goal 1).
- **Case-folded canonicalization is an extension, not a slug rule.**
  Renderers disagree on case-insensitive fragment matching (case-sensitive
  on some, case-insensitive on others); the manual mixes `top`/`Top` and
  `January`/`january` for the same marker. Canonicalizing to the defined
  spelling is strictly more correct in every renderer: an exact match
  beats a case-folded match everywhere.

none else — documented before implementation.

<!-- SECTION:PSEUDOCODE -->
## 3. Pseudocode

```
# Token table (the only candidates)
LINK_DEST      := ']' '(' URL ')'
URL            := 'http://' HOST PATH | 'https://' HOST PATH
HOST           := one or more chars not in {'/', whitespace, ')'}
PATH           := '/system/ws/v' DIGITS '/ss/article/' DIGITS
DIGITS         := one or more [0-9]

# Everything else in the document is non-candidate (identity).

function heading_anchor(heading) -> str
    s := lowercase(heading)                     # Unicode-aware case fold
    keep := ""
    for ch in s:
        if ch is a Unicode letter or digit:
            keep := keep + ch                   # GFM keeps alphanumerics
        else if ch in {' ', '-'}:
            keep := keep + ch                   # spaces & hyphens survive
        # else: punctuation/symbols dropped (commas, periods, quotes, …)
    return replace_all(keep, ' ', '-')          # single spaces -> hyphens

function Slugger()                              # github-slugger occurrence replica
    seen := {}                                  # base slug -> count of prior uses
    function slug(text) -> str:
        base := heading_anchor(text)            # base form UNCHANGED (2.5)
        if base in seen:
            seen[base] := seen[base] + 1
            return base + '-' + seen[base]      # 2nd -> base-1, 3rd -> base-2, …
        seen[base] := 0
        return base                             # 1st -> base

function body_heading_texts(body_md) -> list    # headings in doc order, fences skipped
    texts := []
    in_fence := false
    for line in split(body_md, '\n'):
        if line matches FENCE:                  # ^\s{0,3}(`{3,}|~{3,})
            toggle in_fence (same fence char);  # a fence line is never a heading
            continue
        if in_fence:
            continue
        if line matches '^(#{1,6})\s+(.+?)\s*$':
            texts.append(captured heading text) # '## ' marker stripped
    return texts

function build_anchor_map(articles, title) -> dict
    # articles: deduped, in document order; each has .id (str), .name (str),
    #           .body_md (str), .error (str or null). title: the H1 text
    #           (first heading in the doc). The dedup context is the body as
    #           EMITTED: the placeholder when .error is set (it carries no
    #           headings), else .body_md — never headings that are absent
    #           from the document.
    # NOTE (B7): the TOC is a numbered list, not a heading — it contributes
    # nothing to this walk, so building the map BEFORE the TOC is rendered is
    # circularity-free and leaves every anchor byte-identical.
    slugger := Slugger()
    slugger.slug(title)                         # H1 — first heading in the doc
    slugger.slug('Table of Contents')           # H2 TOC (always present)
    anchor_by_id := {}                          # article id -> its own H2 slug
    for a in articles:
        anchor_by_id[a.id] := slugger.slug(a.name)      # this article's H2
        emitted := a.placeholder if a.error else a.body_md
        for bh in body_heading_texts(emitted):
            slugger.slug(bh)                    # body headings = dedup context
    return anchor_by_id

function internalize(document: str, anchor_by_id: dict) -> str
    # Rewrite ONLY known cross-article article-URL links to anchors. The TOC's
    # `#`-fragment links (B7) are NOT article-URL candidates, so they pass
    # through byte-identical — the pass is idempotent on the TOC.
    pattern := regex(LINK_DEST)                 # capture URL + trailing id
    function repl(match):
        target_id := match.group(id)
        if target_id in anchor_by_id:
            return '](#' + anchor_by_id[target_id] + ')'
        return match.whole                      # unknown id: identity (C7)
    return replace_all(document, pattern, repl) # single left-to-right pass

# B8: fragment resolution — runs AFTER internalize, on the finished document
function defined_anchors(document) -> list
    # Fence-aware line walk; order = document order (2.7).
    out := []
    in_fence := false
    for line in split(document, '\n'):
        if line matches FENCE:                 # ^\s{0,3}(`{3,}|~{3,})
            toggle in_fence (same fence char); continue
        if in_fence: continue
        if line matches '^(#{1,6})\s+(.+?)\s*$':
            out.append(slugger_context.slug(captured heading))  # doc-order slug
        else:
            for m in line.find_all(NAMED_ANCHOR):  # <a id="X" …> ANYWHERE in line
                out.append(m.group(id))           # raw id, verbatim (not slugged)
    return out

function resolve_fragments(document, anchor_set, anchor_by_id) -> str
    exact := set(anchor_set)
    canonical := {}                    # lower(fragment) -> exact spelling
    for a in anchor_set:               # first definition wins (document order)
        canonical.setdefault(a.lower(), a)
    function repl(match):
        frag := match.group(fragment)  # raw, spaces included — no encoding here
        if frag in exact:
            return match.whole         # already defined (incl. TOC links)
        if frag.lower() in canonical:
            return '](#' + canonical[frag.lower()] + ')'      # stage 1
        m := frag.match(ART_ID)        # art_<digits>_… (case-insensitive id)
        if m and m.group(id) in anchor_by_id:
            return '](#' + anchor_by_id[m.group(id)] + ')'    # stage 2 (top)
        return match.whole             # unknown: identity (C7) — never fabricate
    return replace_all(document, regex(FRAGMENT_LINK), repl)

# Integration point (assemble, after the completeness gates pass):
function assemble(articles, expected_count, title) -> str
    deduped := dedupe_first_wins(articles)
    if len(deduped) != expected_count:
        raise CompletenessError(expected_count, len(deduped))
    anchor_by_id := build_anchor_map(deduped, title)   # B7: hoisted ahead of TOC
    toc := ''                                          # B7: linked entries
    for i, a in enumerate(deduped, start=1):
        toc := toc + str(i) + '. [' + a.name + '](#' + anchor_by_id[a.id] + ')'
    blocks := ['# ' + title, '## Table of Contents\n\n' + toc]
    for a in deduped:
        blocks.append(article_block(a))   # '## name', optional '> breadcrumb', body
    document := join(blocks, "\n\n") + "\n"
    document := internalize(document, anchor_by_id)    # cross-article links
    anchor_set := defined_anchors(document)             # B8: defined anchors
    return resolve_fragments(document, anchor_set, anchor_by_id)  # B8: #frags
```

**Ambiguity policy.** The token is unambiguous by construction (fixed
shape); resolution is exact string equality on the id — no prefix,
contains, or fuzzy matching.

**Error model.** There is no error class for this transform. Non-candidates
and unknown ids pass through unchanged (recovery = identity). Malformed
links (unbalanced brackets, query string on the URL, fragment) simply do
not match and survive as-is.

**Idempotence.** After one pass, resolved links are `](#slug)` — the
pattern requires `http(s)://`, so a second pass rewrites nothing:
`internalize(internalize(d)) == internalize(d)`. B8 is likewise
idempotent: every fragment `resolve_fragments` rewrites becomes
exact-defined, so a second pass hits only the "already defined" branch.
Stage order (canonicalize → remap) is what makes this provable: remap
targets are heading slugs, hence already in the anchor set.

**Backtracking budget.** The pattern has no nested/overlapping quantifiers
(`HOST` is one flat char class, ids are `\d+`); worst case is a linear
scan — no catastrophic-backtracking inputs exist for it.

<!-- SECTION:WALKTHROUGH -->
## 4. Walk-through (plain English)

### 4.1 Step-by-step

1. Take the deduped article list exactly as it produced the headings, and
   build a small dictionary: each article id → the slug of its `## `
   heading name (lowercased, punctuation stripped, spaces → hyphens).
   First occurrence wins if an id somehow repeats. This map is built
   *before* the document is rendered (B7), so the `## Table of Contents`
   list is emitted **linked** — each entry `[name]` becomes
   `[name](#slug)` pointing at that entry's own article heading — using the
   exact same map the link-rewriting pass below uses.
2. Scan the finished document once, left to right, looking for the exact
   shape `](` + article-URL + `)`.
3. For each hit, pull out the trailing id. If the dictionary knows that
   id, replace the URL with `#` plus its slug. If not, copy the original
   text through unchanged.
4. That makes the cross-article links internal. Now walk the *finished*
   document once more and collect every anchor it defines: each heading's
   document-order slug (2.6) and each raw `<a id>` named-anchor id, in
   the order they appear (code fences skipped).
5. Scan that document for bare `#fragment` link destinations. For each:
   if the fragment exactly names a defined anchor, leave it alone (this
   is what protects the TOC's own links). If it only *differs in case*
   from a defined anchor, rewrite it to the defined anchor's exact
   spelling (so case-sensitive renderers resolve it too). If it is still
   unresolved but names an article (`art_{id}_…`) that is in the manual,
   point it at that article's own `## ` heading — the article's top,
   which is what its `To Top` link meant. Anything else — external URLs,
   unknown ids — is copied through unchanged.
6. Return the document. Cross-article links are internal, and the
   manual's own intra-article and `To Top` links now resolve in every
   renderer. Nothing else in the file moved.

### 4.2 Worked example

Articles (deduped, portal order):

| id | name |
|---|---|
| `554400000011111` | `M21-1, Part I, Subpart i - Intro` |
| `554400000022222` | `M21-1, Part II - POA` |

Document body (simplified) contains:

```
[see POA](https://www.knowva.ebenefits.va.gov/system/ws/v11/ss/article/554400000022222)
[old ref](https://www.knowva.ebenefits.va.gov/system/ws/v11/ss/article/999)
![diagram](https://www.knowva.ebenefits.va.gov/img/cpkm/x.png)
```

1. Map: `554400000011111 → m21-1-part-i-subpart-i---intro`,
   `554400000022222 → m21-1-part-ii---poa`.
2. First token: shape matches, id `554400000022222` is known →
   `[see POA](#m21-1-part-ii---poa)`.
3. Second token: shape matches, id `999` unknown → unchanged.
4. Third token: `/img/…` is not the article-URL shape → unchanged.

Result: exactly one link changed; the external reference and the image
still point at the portal.

### 4.3 Worked example (B8 fragment resolution)

Article `…95621` (named `M21-1 Guidance`) emits, among other things:

```
## M21-1 Guidance
<a id="art_…95621_Letter" name="…"></a>
<a id="art_…95621_Top" name="…"></a>
```

and another article's body contains:

```
[see letter](#art_…95621_Letter)      # exact defined anchor
[see letter](#art_…95621_letter)      # case-variant (defined: …_Letter)
[to top](#art_…95621_to top)          # marker absent, id known
```

1. The anchor set includes `art_…95621_Letter`, `art_…95621_Top`, and
   the article's own H2 slug (its top).
2. `[see letter](#…_Letter)` — fragment exact-defined → kept verbatim.
3. `[see letter](#…_letter)` — not exact, but lowercases to the same key
   as a defined anchor → rewritten to `#art_…95621_Letter` (stage 1).
4. `[to top](#art_…95621_to top)` — still unresolved, but its id
   `…95621` is in the manual → rewritten to the article's own H2 slug —
   the top of the article (stage 2).

Result: all three links resolve; only the two broken destinations
changed, and link text is untouched.

<!-- SECTION:IMPLEMENTATION -->
## 5. Implementation notes (entry-level guide)

### 5.1 Data structures

- `Slugger` — a github-slugger occurrence replica. Internal state:
  `_seen: dict[str, int]` mapping each base slug to how many times it has
  been claimed. `slug(text)` returns `base` on first use and `base-k` on
  the (k+1)-th (2nd → `base-1`, 3rd → `base-2`, …). It reuses
  `heading_anchor` for the base slug, so the single-heading base form is
  unchanged (2.5).
- `anchor_by_id: dict[str, str]` — keys: deduped article ids (strings,
  portal ids are numeric strings); values: the slug the document-order
  `Slugger` assigns to that article's *own* `## {name}` heading. Built by
  one left-to-right document-order walk (pseudocode). (B7: the walk is
  hoisted *ahead* of TOC rendering so the TOC can link each entry to its
  own anchor; the TOC is a heading-free list, so it contributes nothing to
  the walk and hoisting leaves every anchor byte-identical.)
- `_body_heading_texts(body_md) -> list[str]` — the body's heading texts
  in document order, `#`-markers stripped, fenced code blocks skipped
  (defensive; the live manual has 0 fences today, but `mdconv` can emit
  ``` fences for `<pre>`).
- The pattern (compiled once at module level):

  ```
  \]\((https?://[^/\s)]+/system/ws/v\d+/ss/article/(\d+))\)
  ```

  Group 1 = full URL (kept if the id is unknown), group 2 = the id.
- B8 (v0.5.0) patterns and functions:
  - `_NAMED_ANCHOR` — `<a\s+id="([^"]+)"` — matched per line with
    `re.search`/`findall` **anywhere in the line** (named anchors occur
    inline in text lines; a line-anchored `match` undercounts — 5.4).
  - `_FRAGMENT_LINK` — `\]\(#([^)]*)\)` — the only fragment candidates
    (bare `#` destinations; group 1 = the raw fragment, spaces
    included).
  - `_ART_ID` — `art_(\d+)` — the article identity inside a
    still-unresolved fragment (stage 2).
  - `defined_anchors(document) -> list[str]` — the fence-aware line walk
    of 2.7: heading slugs (reusing the document-order `Slugger`) plus
    raw `<a id>` ids, in document order.
  - `resolve_fragments(document, anchor_set, anchor_by_id) -> str` — the
    two-stage `re.sub` pass of 2.7 (exact → canonicalize → remap →
    identity).
  - `assemble` runs `_internalize_links` first, then
    `resolve_fragments` (stage order, 2.7).

### 5.2 Edge cases and defined behavior

| Case | Defined behavior | Why |
|---|---|---|
| Document with no candidate links | byte-identical | identity (C6) |
| Empty article list (`expected_count=0`) | document unchanged (no map) | nothing to resolve |
| Link to the article's own id | anchor to its own heading | self-navigation is valid |
| Link to an id not in the manual | URL unchanged | still resolves on the portal (C7) |
| Image `![alt](https://…/img/…)` | unchanged | not the article-URL shape (A) |
| External link (`ecfr.gov`, …) | unchanged | not the article-URL shape (A) |
| Two articles sharing a name | each id → its own heading's distinct slug (1st → `base`, 2nd → `base-1`) | document-order dedup (C4, B3) |
| Article name collides with an earlier body heading (earlier `### General`) | the article's own H2 is suffixed (`general-1`); its links use it | the body heading already claimed the base slug in document order (2.6) |
| Fenced code block containing a `#` line | the `#` line is NOT counted as a heading | fence-aware extraction (`_body_heading_texts`) |
| Article URL with query string | unchanged (pattern requires digits then `)`) | mdconv strips queries; anything left is not canonical (A) |
| Uppercase name, commas, ` - ` | slug per 2.5 (triple hyphen preserved) | must match the renderer, not our taste |
| Unicode in names (e.g. `’`) | non-alnum dropped, letters kept | Unicode-aware slug (2.5) |
| Link text containing `](` | text untouched — only the URL token is replaced | match is scoped to the destination (B) |
| `> [content unavailable: …]` placeholder | unchanged | no `](URL)` token present (A) |
| Fragment exact-defined (incl. TOC links, `art_…_Letter`) | kept verbatim | stage-0 short-circuit (2.7) |
| Case-variant fragment (`#…_top` vs defined `…_Top`, either direction) | rewritten to the defined anchor's exact spelling | stage 1 canonicalization (2.7) |
| Truly-absent `art_{id}_…` with known id (`To Top` marker dropped by mdconv) | rewritten to the article's own H2 slug (its top) | stage 2 remap (2.7) |
| Fragment `art_{id}_…` with id NOT in the manual | unchanged | never fabricated (C7, Invariant D) |
| Fragment with raw spaces (`#…_to top`) | resolved by exact / case-folded raw lookup (no percent-encoding here — B9) | named ids are taken verbatim (2.7) |
| Named anchor inline in a text line | collected by per-line `search`/`findall`, not line-anchored `match` | inline anchors exist (5.4) |

### 5.3 Invariants and how to test them

- **I1 (count conservation).** `# article-URL links after` ==
  `# article-URL links before` − `# known-id links before`. Test: build a
  document with 2 known + 1 unknown link; assert exactly one URL remains
  and one anchor appears.
- **I2 (anchor existence).** Every rewritten anchor equals the slug of a
  `## ` heading line present in the document. Test: collect
  `^## ` headings, slug them, assert every `](#…)` produced from a
  candidate is in that set.
- **I3 (identity).** A document containing no article-URL links is
  byte-identical through `assemble` twice. Test: compare strings.
- **I4 (canonical existence, B8).** Every fragment the pass rewrites
  equals a defined anchor (heading slug or named id) byte-for-byte.
  Test: collect `defined_anchors` over the output; assert every
  destination that changed is in that set.
- **I5 (dead count only decreases, B8).** `dead_after ≤ dead_before`,
  with 0 new dead links introduced. Test: census (exact + case-folded
  membership) before and after; assert no previously-live fragment
  becomes dead.

### 5.4 Pitfalls and known traps

- **`](URL)` is a substring of `![alt](URL)`.** A lookbehind on `](`
  cannot tell links from images — the discriminator is the *URL shape*,
  and image URLs never have the article shape. Do not "fix" this by
  excluding `](` globally.
- **Don't match on the host.** The id is the canonical identity; links
  from other hosts (or protocol variants) to the same id must resolve.
- **ASCII-only slugging is wrong.** Names contain Unicode (`’`); an ASCII
  filter would drop Unicode letters and disagree with the renderer's
  anchor. Use Unicode-aware alnum.
- **Query strings.** If a candidate ever carries a query, the pattern
  deliberately fails to match and the link stays external — a safe
  fallback, not a defect.
- **Do not add a third-party slugger package.** One 4-line function,
  pinned by byte-exact tests — cheaper than a dependency (pragmatic
  reuse-of-stdlib rule).
- **Use `search`/`findall`, not `match`, for named anchors (B8).** Named
  anchors occur *inline* in text lines; a line-anchored `re.match`
  undercounts them (9,477 vs the true 9,507 on the live manual) and
  yields wrong dead counts. Match `<a\s+id="…"` anywhere in the line.
- **Don't percent-encode fragments in this pass (B8).** Named ids carry
  raw spaces (`art_…_to top`); the canonical lookup is on the *raw*
  fragment. URL-encoding spaces belongs to the later B9 destination
  rewrite, not here — encoding here would break the exact/case-folded
  lookups and change live links.
- **Stage order matters (B8).** Canonicalize before remap: remap targets
  are already in the anchor set, which is what makes the combined pass
  provably idempotent.
- **Never fabricate a dead reference (B8).** A fragment whose id is not
  in the manual (Historical/Rescinded or foreign) must stay as-is;
  rewriting it to a "nearest" article would create a *wrong* link that
  silently resolves — worse than a dead one.

### 5.5 Language notes

Python: `re.sub(pattern, repl_fn, document)` with `repl_fn` returning the
replacement string; `str.lower()` and `str.isalnum()` are Unicode-aware —
rely on both rather than hand-rolled ASCII tables. Compile the pattern at
module level. `Slugger` is a small class holding `_seen: dict[str, int]`;
`_body_heading_texts` is a pure line scan (flat fence/heading patterns, no
backtracking). Keep `internalize` and `_body_heading_texts` private to the
module; expose `heading_anchor` and `Slugger` (both public, tested
directly) beside the existing `assemble` / `Article` / `CompletenessError`.

<!-- SECTION:TESTS -->
## 6. Test cases and sample data

All sample data is synthetic (G11); ids are 11-digit fake portal ids.

| # | Name | Input (sample data) | Expected output | Why it matters |
|---|---|---|---|---|
| 1 | happy: cross-article link resolved | articles `("…11111", "M21-1, Part I, Subpart i - Intro")`, `("…22222", "M21-1, Part II - POA")`; body link `[see POA](https://www.knowva.ebenefits.va.gov/system/ws/v11/ss/article/…22222)` | `[see POA](#m21-1-part-ii---poa)`; raw URL absent | the feature itself (C1–C3) |
| 2 | edge: no candidate links | one article, body `Plain text. [ext](https://www.ecfr.gov/current)` | byte-identical through `assemble` | identity (A, C6) |
| 3 | degenerate: unknown id + image kept | body links `[old](…/article/999)` and `![d](https://…/img/cpkm/x.png)` | both unchanged; no `#` anchor introduced | unknown targets stay portal-resolvable (C7); images never rewritten (A) |
| 4 | boundary: slug of a real name shape | name `M21-1, Part II, Subpart iii - X` | `m21-1-part-ii-subpart-iii---x` (triple hyphen from ` - `) | anchor must equal the renderer's, byte for byte (2.5) |
| 5 | self-link | article `("…11111", "General")` linking to `…11111` | `[t](#general)` | self-navigation is valid (5.2) |
| 6 | duplicate names | two ids, both named `General` | 1st id → `#general`; 2nd id → `#general-1` (its own heading) | document-order dedup; each id → its own heading (C4, B3) |
| 7 | determinism | run #1's input twice | byte-identical outputs | G10 / C5 |
| 8 | gate ordering preserved | 3 articles, `expected_count=2` | `CompletenessError` raised with `.expected==2, .actual==3`, before any rewriting | completeness contract untouched (existing pin) |
| 9 | I2 anchor-existence property | 3 articles with real name shapes, links to all three | every `](#…)` from a candidate matches the `Slugger`'s document-order slug for some heading in the output | links land where they claim to (I2) |
| 10 | Slugger dedup sequence (direct) | `Slugger().slug` on `A`, `A`, `A`, `B` | `a`, `a-1`, `a-2`, `b` | github-slugger occurrence logic, byte-exact (2.6) |
| 11 | article name vs earlier body heading | article 1 named `X` with body `### General`; article 2 named `General` | article 2's own H2 → `#general-1`; a link to it uses `#general-1` | the body heading already claimed `general` in document order (2.6) |
| 12 | 0-mismatch property | any article list with duplicate names + body-heading collisions | every emitted `](#…)` article anchor equals the `Slugger`'s document-order slug for that article's H2 | links land on the article's own heading, never a dead anchor (B3) |
| 13 | happy: TOC entries are internal links (B7) | 3 articles, two sharing the name `General`; `assemble` | each TOC line == `{i}. [{name}](#{anchor})` where `anchor` is that article's own H2 slug (1st `General` → `general`, 2nd → `general-1`) | the TOC navigates to each entry's own article heading (B7) |
| 14 | byte: TOC visible text and order unchanged (B7) | same articles as #13; strip the `[text](#anchor)` link wrapping from the TOC lines | the plain list equals the pre-B7 `{i}. {name}` form byte-for-byte | goal 1: only link wrapping is added — no text or organization change |
| 15 | property: `_internalize_links` idempotent on the TOC (B7) | a document with a linked TOC plus one known article-URL link; run `_internalize_links` twice | the TOC's `#`-fragment links are byte-identical on both passes, while the article-URL link resolves once | the TOC fragment links are not candidates, so the pass cannot corrupt or double-rewrite them |
| 16 | property: 0 dead TOC anchors (B7 census) | duplicate-named articles (as in #13) | every TOC `#target` ∈ the oracle's full anchor set (`all_anchors`) | every TOC link lands on a real heading — the offline core of the live "442 TOC links verified" criterion |
| 17 | happy: case-variant fragment canonicalized (B8) | article `("…11111", "General")` with named anchor `<a id="art_…11111_Top" name="…"></a>`; body links `[t](#art_…11111_top)` and `[u](#ART_…11111_TOP)` | both rewrite to `#art_…11111_Top` — the defined anchor's exact spelling, in either case direction | stage 1 (2.7); case-sensitive renderers now resolve it |
| 18 | happy: absent `art_{id}_…` remapped to the article's top (B8) | article `("…11111", "General")`; body link `[to top](#art_…11111_to top)` (the marker itself is not emitted) | rewrites to the article's own H2 slug `#general` | stage 2 (2.7); `To Top` lands on the top of the article |
| 19 | edge: unknown id never fabricated (B8) | one article `("…11111", "General")`; body links `[x](#art_99999999999_x)` and `[y](#something_else)` | both byte-identical — no anchor invented | C7 / Invariant D — a dead ref is never faked (2.7) |
| 20 | edge: raw-space fragments (B8) | named `<a id="art_…11111_to top">`; body links `[a](#art_…11111_to top)` (exact) and `[b](#art_…11111_TO TOP)` (case-variant) | exact kept verbatim; case-variant rewritten to `#art_…11111_to top` (raw space preserved) | named ids are verbatim; lookups run on the raw fragment — no percent-encoding here (B9) |
| 21 | property: fragment pass idempotent (B8) | a document with case-variant + absent + exact fragments; run `_resolve_fragment_links` twice | output of pass 1 == output of pass 2 (every rewritten fragment is exact-defined on pass 2) | idempotence (2.7 / 3) |
| 22 | property: dead count only decreases (B8) | same document as #21; census (exact + case-folded membership) before and after | every resolvable dead fragment is gone; no previously-live fragment becomes dead | I5 — the pass can never introduce a dead link (2.7) |
| 23 | edge: external URL fragments untouched (B8) | body links `[e](https://www.ecfr.gov/current#sec-1)` and `![d](https://…/img/x.png#f)` | both byte-identical | fragment pass is scoped to bare `#` destinations (C9, Invariant E) |

### 6.1 Property tests

For any article list and any document: (a) `assemble` twice on the same
input is byte-identical; (b) the number of article-URL links can only
decrease, never increase; (c) link *text* is unchanged — the multiset of
`[…](` link texts before equals after.

### 6.2 Performance acceptance

Live manual (D ≈ 13.7 MB, 14,447 candidate tokens): the rewrite pass must
finish well under 1 s on a laptop-class CPU (linear scan; the full crawl
already takes ~3 min, so this pass is negligible by design). The B8
fragment pass (anchor walk + `re.sub` over the same D, 23,068 fragment
tokens) is the same order and also finishes well under 1 s on a
laptop-class CPU (verified 2026-10-08).

<!-- SECTION:REFERENCES -->
## 7. References

- GitHub `slugger` — the reference implementation of GitHub's anchor
  slug rules (lowercase, keep alphanumerics/spaces/hyphens, spaces →
  hyphens) **and its `occurrences` dedup** (1st → `base`, 2nd → `base-1`,
  3rd → `base-2`, …), which `Slugger` (B3) replicates on top of the
  unchanged base slug: <https://github.com/github/slugger>.
- Sibling documents:
  [html-to-markdown-section-extraction](html-to-markdown-section-extraction.md)
  (the only producer of the link tokens this algorithm rewrites; its
  `_rewrite_url` defines the canonical article-URL shape),
  [historical-rescinded-exclusion](historical-rescinded-exclusion.md)
  (explains why some linked ids are *absent* from the manual and must
  stay external).
- Live portal observation (2026-10-03): 442-article manual, 14,447
  article-URL links, single host, zero duplicate names.
- Live fragment census (2026-10-08, B8): 23,068 in-document `#fragment`
  links; 21,468 defined anchors (21,464 unique; 0 case collisions); 214
  dead (91 case-variant + 123 truly-absent instances, 168 distinct — all
  `art_{id}_…`, 100% remappable); 418 `to top` links, 95 dead pre-fix.
  Post-fix re-census: 0 dead internal links.
