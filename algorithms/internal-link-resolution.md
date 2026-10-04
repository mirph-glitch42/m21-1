# Internal Link Resolution (Cross-Article Hyperlinks → In-Document Anchors)

<!-- INDEX:BEGIN format=tsv version=1 -->
id	start_line	end_line
INDEX_BLOCK	3	13
METADATA	15	36
THEORY	37	184
PSEUDOCODE	185	246
WALKTHROUGH	247	289
IMPLEMENTATION	290	363
TESTS	364	393
REFERENCES	394	408
<!-- INDEX:END -->

<!-- SECTION:METADATA -->
## 1. Metadata

| Field | Value |
|---|---|
| Name | Internal link resolution — rewrite cross-article hyperlinks into in-document section anchors |
| Slug | internal-link-resolution |
| Version | 0.2.0 |
| Status | implemented |
| Author | Bionic agent (on behalf of murphyjj) |
| Created | 2026-10-03 |
| Last modified | 2026-10-04 |
| Status history | 0.1.0 (2026-10-03): initial draft — the assembled manual's ~14.4k cross-article hyperlinks (eGain article URLs) should become internal `#anchor` links to the target article's `## ` heading; links whose target id is absent from the manual stay as portal URLs · 0.2.0 (2026-10-04): implemented in `src/m21_crawl/assemble.py` (`_ARTICLE_LINK`, `heading_anchor`, `_internalize_links`, final pass in `assemble`) + 7 new tests in `tests/test_assemble.py`; slug worked-examples corrected to the renderer's triple-hyphen form |
| Languages | Python 3.12 (implementation); pseudocode is language-agnostic |
| Implementation location | src/m21_crawl/assemble.py — `_ARTICLE_LINK` L41; `heading_anchor` L74–82; `_internalize_links` L85–98; final pass in `assemble` L155–156 (v0.2.0, 2026-10-04) |
| Time complexity | O(D) over the assembled document size D (single regex pass) + O(N) map build (see THEORY 2.4) |
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
4. **First-occurrence semantics.** If two articles shared a name (live data
   shows none), both ids map to the slug of the first `## ` heading with
   that text — matching how a reader's in-page anchor jump resolves.
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

**Invariant B (anchor existence).** The id→anchor map is built from the
*same* deduped list (same order, same names) that emits the `## {name}`
headings. Hence every rewritten anchor is the slug of a heading that
exists in the document. With unique names (verified live) each heading
slug is unique in the document; with duplicate names the anchor resolves
to the first such heading — exactly a reader's in-page anchor semantics —
so the link still lands on an article with that name.

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

### 2.6 Deviations

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

function internalize(document: str, articles: list) -> str
    # articles: deduped, in document order; each has .id (str) and .name (str)
    anchor_by_id := {}                          # insertion-ordered
    for a in articles:
        if a.id not in anchor_by_id:
            anchor_by_id[a.id] := heading_anchor(a.name)   # first wins (C4)
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
    return internalize(document, deduped)
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

- `anchor_by_id: dict[str, str]` — keys: deduped article ids (strings,
  portal ids are numeric strings); values: slugs. Insertion order =
  portal order (Python dicts preserve it) — only relevant for the
  first-wins duplicate-name rule.
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
| Two articles sharing a name | both ids → first heading's slug | reader anchor semantics (C4) |
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
module level. Keep `internalize` private to the module; expose only
`heading_anchor` (public, tested directly) beside the existing
`assemble` / `Article` / `CompletenessError`.

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
| 6 | duplicate names | two ids, both named `General` | both ids resolve to `#general` (first heading) | defined first-wins semantics (C4) |
| 7 | determinism | run #1's input twice | byte-identical outputs | G10 / C5 |
| 8 | gate ordering preserved | 3 articles, `expected_count=2` | `CompletenessError` raised with `.expected==2, .actual==3`, before any rewriting | completeness contract untouched (existing pin) |
| 9 | I2 anchor-existence property | 3 articles with real name shapes, links to all three | every `](#…)` from a candidate matches the slug of a `^## ` heading in the output | links land where they claim to (I2) |

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
  hyphens): <https://github.com/github/slugger>.
- Sibling documents:
  [html-to-markdown-section-extraction](html-to-markdown-section-extraction.md)
  (the only producer of the link tokens this algorithm rewrites; its
  `_rewrite_url` defines the canonical article-URL shape),
  [historical-rescinded-exclusion](historical-rescinded-exclusion.md)
  (explains why some linked ids are *absent* from the manual and must
  stay external).
- Live portal observation (2026-10-03): 442-article manual, 14,447
  article-URL links, single host, zero duplicate names.
