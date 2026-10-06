# Internal Link Resolution (Cross-Article Hyperlinks → In-Document Anchors)

<!-- INDEX:BEGIN format=tsv version=1 -->
id	start_line	end_line
INDEX_BLOCK	3	13
METADATA	15	36
THEORY	37	230
PSEUDOCODE	231	325
WALKTHROUGH	326	368
IMPLEMENTATION	369	456
TESTS	457	489
REFERENCES	490	506
<!-- INDEX:END -->

<!-- SECTION:METADATA -->
## 1. Metadata

| Field | Value |
|---|---|
| Name | Internal link resolution — rewrite cross-article hyperlinks into in-document section anchors |
| Slug | internal-link-resolution |
| Version | 0.3.0 |
| Status | implemented |
| Author | Bionic agent (on behalf of murphyjj) |
| Created | 2026-10-03 |
| Last modified | 2026-10-06 |
| Status history | 0.1.0 (2026-10-03): initial draft — the assembled manual's ~14.4k cross-article hyperlinks (eGain article URLs) should become internal `#anchor` links to the target article's `## ` heading; links whose target id is absent from the manual stay as portal URLs · 0.2.0 (2026-10-04): implemented in `src/m21_crawl/assemble.py` (`_ARTICLE_LINK`, `heading_anchor`, `_internalize_links`, final pass in `assemble`) + 7 new tests in `tests/test_assemble.py`; slug worked-examples corrected to the renderer's triple-hyphen form · 0.3.0 (2026-10-06): B3 — anchors are now assigned in *document order* via a github-slugger occurrence replica (`Slugger`), with body-heading context (`_body_heading_texts`); C4 rewritten — duplicate article names map to their own heading's distinct `-N` slug, and an article name colliding with an earlier body heading is correctly suffixed |
| Languages | Python 3.12 (implementation); pseudocode is language-agnostic |
| Implementation location | src/m21_crawl/assemble.py — `_ARTICLE_LINK` L43; `_BODY_HEADING`/`_FENCE` L47–48; `heading_anchor` L79–87; `Slugger` L90–108; `_body_heading_texts` L111–135; `_internalize_links` L138–151; `_emitted_body` L165–177; final pass in `assemble` L218–229 (v0.3.0, 2026-10-06) |
| Time complexity | O(D + (N + H)·L) time: single regex rewrite pass O(D) + a document-order slug build that scans N article names and H body headings at O((N + H)·L) (see THEORY 2.4) |
| Space complexity | O(N + D) working space (id→anchor map of N entries; the rewritten copy of D bytes) |
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

**Live scale (verified 2026-10-03 on the 442-article manual):**

| Observation | Value |
|---|---|
| article-URL hyperlinks (`/system/ws/vNN/ss/article/<id>`) | 14,447 |
| distinct hosts used by those links | 1 (`www.knowva.ebenefits.va.gov`) |
| duplicate article names among the 442 | 0 (→ every anchor is unambiguous) |
| intra-article `#anchor` links (e.g. `#1a`) | thousands — **out of scope** (see 2.2) |

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
- **Intra-article `#anchor` links are deferred.** They already are
  in-document anchors; their *targets* (eGain `<a name="1a">` positions)
  simply don't exist in the converted Markdown. Restoring them requires
  anchor-position recording during HTML→Markdown conversion — a different
  algorithm (converter-side), documented here only as out of scope.

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
returned (A). No other code path mutates the document. □

### 2.4 Complexity

Document of size D bytes, N articles, average name length L:

- map build: O(N) inserts + O(N·L) slug work (each name scanned once);
- rewrite: one left-to-right regex scan of D with a constant-size pattern
  (no nested quantifiers — see 3.1) → O(D);
- total: **O(D + N·L) time, O(N + D) space** (the map plus the rewritten
  copy). The rewrite dominates on the live manual (D ≈ 13.7 MB, N = 442).
  Both terms are linear; no quadratic behavior is possible because the
  pattern has no backtracking loops.

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

### 2.7 Deviations

none — documented before implementation.

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

function internalize(document: str, articles: list, title: str) -> str
    # articles: deduped, in document order; each has .id (str), .name (str),
    #           .body_md (str), .error (str or null). title: the H1 text
    #           (first heading in the doc). The dedup context is the body as
    #           EMITTED: the placeholder when .error is set (it carries no
    #           headings), else .body_md — never headings that are absent
    #           from the document.
    slugger := Slugger()
    slugger.slug(title)                         # H1 — first heading in the doc
    slugger.slug('Table of Contents')           # H2 TOC (always present)
    anchor_by_id := {}                          # article id -> its own H2 slug
    for a in articles:
        anchor_by_id[a.id] := slugger.slug(a.name)      # this article's H2
        emitted := a.placeholder if a.error else a.body_md
        for bh in body_heading_texts(emitted):
            slugger.slug(bh)                    # body headings = dedup context
    pattern := regex(LINK_DEST)                 # capture URL + trailing id
    function repl(match):
        target_id := match.group(id)
        if target_id in anchor_by_id:
            return '](#' + anchor_by_id[target_id] + ')'
        return match.whole                      # unknown id: identity (C7)
    return replace_all(document, pattern, repl) # single left-to-right pass

# Integration point (assemble, after the completeness gates pass):
function assemble(articles, expected_count, title) -> str
    … existing: dedupe_first_wins, CompletenessError gate, TOC, blocks …
    document := join(blocks, "\n\n") + "\n"
    return internalize(document, deduped, title)
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
`internalize(internalize(d)) == internalize(d)`.

**Backtracking budget.** The pattern has no nested/overlapping quantifiers
(`HOST` is one flat char class, ids are `\d+`); worst case is a linear
scan — no catastrophic-backtracking inputs exist for it.

<!-- SECTION:WALKTHROUGH -->
## 4. Walk-through (plain English)

### 4.1 Step-by-step

1. Take the deduped article list exactly as it produced the headings, and
   build a small dictionary: each article id → the slug of its `## `
   heading name (lowercased, punctuation stripped, spaces → hyphens).
   First occurrence wins if an id somehow repeats.
2. Scan the finished document once, left to right, looking for the exact
   shape `](` + article-URL + `)`.
3. For each hit, pull out the trailing id. If the dictionary knows that
   id, replace the URL with `#` plus its slug. If not, copy the original
   text through unchanged.
4. Return the document. Nothing else in the file moved.

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
  one left-to-right document-order walk (pseudocode).
- `_body_heading_texts(body_md) -> list[str]` — the body's heading texts
  in document order, `#`-markers stripped, fenced code blocks skipped
  (defensive; the live manual has 0 fences today, but `mdconv` can emit
  ``` fences for `<pre>`).
- The pattern (compiled once at module level):

  ```
  \]\((https?://[^/\s)]+/system/ws/v\d+/ss/article/(\d+))\)
  ```

  Group 1 = full URL (kept if the id is unknown), group 2 = the id.

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

### 6.1 Property tests

For any article list and any document: (a) `assemble` twice on the same
input is byte-identical; (b) the number of article-URL links can only
decrease, never increase; (c) link *text* is unchanged — the multiset of
`[…](` link texts before equals after.

### 6.2 Performance acceptance

Live manual (D ≈ 13.7 MB, 14,447 candidate tokens): the rewrite pass must
finish well under 1 s on a laptop-class CPU (linear scan; the full crawl
already takes ~3 min, so this pass is negligible by design).

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
