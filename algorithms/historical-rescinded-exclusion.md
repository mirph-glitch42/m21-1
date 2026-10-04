# Historical/Rescinded Article Exclusion (Marker-Based Filtering + Two-Gate Completeness)

<!-- INDEX:BEGIN format=tsv version=1 -->
id	start_line	end_line
INDEX_BLOCK	3	13
METADATA	15	36
THEORY	37	155
PSEUDOCODE	156	195
WALKTHROUGH	196	234
IMPLEMENTATION	235	288
TESTS	289	299
REFERENCES	300	315
<!-- INDEX:END -->

<!-- SECTION:METADATA -->
## 1. Metadata

| Field | Value |
|---|---|
| Name | Historical/Rescinded article exclusion (name-marker filtering + two-gate completeness contract) |
| Slug | historical-rescinded-exclusion |
| Version | 0.2.0 |
| Status | implemented |
| Author | Bionic agent (on behalf of murphyjj) |
| Created | 2026-10-03 |
| Last modified | 2026-10-03 |
| Status history | 0.1.0 (2026-10-03): initial draft — the deliverable must exclude portal articles marked Historical or Rescinded; the marker lives only in the article name (verified live), and the completeness contract splits into a truncation gate and a fetch gate · 0.2.0 (2026-10-03): implemented in `src/m21_crawl/articles.py` (`_EXCLUDED_RE`, `is_excluded_article`) + `src/m21_crawl/cli.py` (skip-before-fetch, gates A/B in `crawl_manual`); 4 new tests in `tests/test_articles.py` and `tests/test_cli.py` |
| Languages | Python 3.12 (implementation); pseudocode is language-agnostic |
| Implementation location | `src/m21_crawl/articles.py` — `_EXCLUDED_RE` L34; `is_excluded_article` L37–47; `src/m21_crawl/cli.py` — skip-before-fetch L151–156; gate A L185–188; gate B L189–191 |
| Time complexity | O(1) per article name (regex suffix test); skips ≈43 % of content fetches on the live manual (observed) |
| Space complexity | O(1) working state (two counters) beyond the existing crawl state |
| Determinism | deterministic (pure predicate on the verbatim portal name) |
| Dependencies | `m21_crawl.articles` (listing), `m21_crawl.cli` (crawl orchestration), `m21_crawl.assemble` (assembly + count gate) |
| Thread safety | not thread-safe by contract; single-threaded crawl, no shared state |
| Related documents | [manual-tree-crawl](manual-tree-crawl.md), [topic-article-paging](topic-article-paging.md) |

<!-- SECTION:THEORY -->
## 2. Theory

### 2.1 Problem definition

**Input.** The crawl's per-topic article entries — `(id, name)` pairs in
portal order, exactly as produced by the listing pipeline (see
[topic-article-paging](topic-article-paging.md)).

**Output.** The subset of articles that belong in the deliverable: the
portal's *current* policy content. Articles the portal marks as
**Historical** or **Rescinded** are excluded — neither fetched (no
content request is issued) nor assembled (absent from the TOC and body).

**The constraint that makes this an algorithm.** The marker is *not a
structural field*. Verified live (2026-10-03) by scanning **all 785
entries** of the manual:

| Name pattern (verbatim, live) | Count |
|---|---|
| ends ` - Historical` | 290 |
| ends ` - Rescinded` | 48 |
| ends with dash+marker, irregular spacing (` -  Historical` ×3, `K- Historical` ×2) | 5 |
| **excluded total** | **343** |
| other (current) | 442 |

- Every one of the 785 entries has identical structural fields —
  `articleType=0`, `state="P"`, `commitState=1` — in all four name
  buckets. There is no field to filter on.
- Three *current* articles contain the word mid-name, e.g.
  `…Section H - Historical Guidance on Formal Applications and Informal
  Claims Received Prior to March 24, 2015`. Any "contains" rule would
  wrongly drop them.
- The marker's spacing is irregular live (`- Historical`, `-  Historical`,
  `K- Historical`) — a literal `- Historical` match would miss 5 of the
  343.

**Contract.**

1. **Predicate.** An entry is excluded iff its verbatim name ends in the
   whole word `Historical` or `Rescinded` (case-sensitive, as the portal
   marks them), preceded by a non-letter (word boundary) — equivalently
   the regex `(?<![A-Za-z])(?:Historical|Rescinded)$`.
2. **Skip before fetch.** Excluded entries trigger no content request and
   appear nowhere in the deliverable.
3. **Two-gate completeness.** (A) the total number of *listed* entries
   across all topics equals the root topic's `articleTotalCount` — the
   silent-truncation backstop that previously protected the crawl is
   preserved; (B) the assembled (deduped) article count equals
   *listed − excluded*. Both failures raise `CompletenessError` →
   exit code 2, nothing written.

### 2.2 Why this approach

- **Word-boundary name-suffix predicate (chosen).** Matches the portal's
  visible naming convention exactly; live evidence (2.1) shows it captures
  all 343 marked articles and spares the 3 "Historical Guidance …"
  current articles. Irregular spacing (`-  `, `K- `) is handled because
  the boundary is "non-letter before the marker", not a literal
  separator.
- **"Contains Historical/Rescinded".** Rejected: would exclude 3 current
  articles whose titles merely discuss historical guidance.
- **Topic-name based (skip topics named `…Historical`).** Rejected:
  coarser than the marking (the portal marks *articles*, and a topic can
  hold mixed articles); a name heuristic on a different object is a
  second source of truth that can drift from the article names.
- **Case-insensitive matching.** Rejected: the live marker is uniformly
  title-case; matching lowercase would be a speculative rule not grounded
  in observed portal data. Pinned by test.
- **Single gate `assembled == rootTotal − excluded`.** Rejected: a portal
  that truncates *exactly* the excluded number of entries would pass
  silently — the exact class of defect (silent truncation) that motivated
  the original gate. Splitting into gate A (list side) + gate B
  (fetch/assembly side) keeps each side pinned independently.
- **Filter at assembly time (fetch all, drop later).** Rejected: wastes
  ≈343 content fetches and politeness delays for content the deliverable
  can never contain.

### 2.3 Correctness argument

Let `L` = listed entries (all entries returned by the listing pipeline),
`E` = entries with `predicate(name) = true`, `R = L − E` = retained,
`A` = articles assembled after dedupe.

- **I1 (skip-before-fetch ⇒ A ⊆ retained).** An entry reaches assembly
  only if it was not excluded and its content was fetched; excluded
  entries are `continue`d before any request, so nothing marked appears
  in the output.
- **I2 (no false exclusion).** The predicate is a pure function of the
  verbatim name; for names not ending in the marker words (including
  "… - Historical Guidance …", where the marker is not at the end) it
  returns false, so current articles are fetched and assembled.
- **I3 (gate A is truncation-blind to skipping).** Gate A compares
  *listed* against the root total; exclusion happens after listing and
  never decrements `L`. Hence a truncated list (the pre-paging defect)
  still fails gate A even when articles are being skipped.
- **I4 (gate B pins the fetch side).** `A == R` fails iff any retained
  article was lost (fetch error recorded as placeholder *does* count —
  it is assembled with `error` set — but a *missing* article does not),
  or if dedup collapsed ids that the portal reported once.

Gate A + gate B together are strictly stronger than the old single gate
`A == rootTotal` in the presence of skipping, and equal to it when
`E = 0` (the pre-change behavior — pinned by the unchanged fixture
suite). Termination and ordering are inherited from the listing and
assembly algorithms it composes; this algorithm adds a finite predicate
and two integer comparisons.

### 2.4 Complexity

O(1) per name (fixed regex, anchored at the end) plus two integer
counters; the crawl saves one content request + one politeness delay per
excluded entry (343 of 785 on the live manual of 2026-10-03 — ≈43 %
fewer fetches). Space: O(1) beyond existing state.

### 2.5 Deviations

none — documented before implementation.

<!-- SECTION:PSEUDOCODE -->
## 3. Pseudocode

```
EXCLUDED_RE <- /(?<![A-Za-z])(?:Historical|Rescinded)$/   # case-sensitive

function is_excluded_article(name) -> bool:
    return EXCLUDED_RE matches name

function crawl_manual(client):
    nodes     <- flatten_tree(topic_tree(client))
    root      <- nodes[0]
    expected_root <- root.articleTotalCount    # portal's total (incl. marked)
    articles  <- []
    listed    <- 0
    excluded  <- 0
    failures  <- 0
    first     <- true
    for node in nodes:                          # portal pre-order (sibling doc)
        if node.articleCount == 0:
            continue
        for (article_id, name) in list_topic_articles(client, node.id):
            if is_excluded_article(name):       # I1: skip BEFORE fetch
                listed   <- listed + 1
                excluded <- excluded + 1
                continue                        # no content request, no delay
            listed <- listed + 1
            if not first:
                sleep(delay)                    # only real fetches are paced
            first <- false
            content <- get_article_content(client, article_id)
            articles <- articles ++ [Article(article_id, name,
                                             convert(content), breadcrumb(node))]
    # GATE A (I3): the LIST side is complete — truncation stays loud
    if listed != expected_root:
        raise CompletenessError(expected_root, listed)
    # GATE B (I4): the FETCH side is complete — assemble checks A == listed - excluded
    return assemble(articles, expected_count = listed - excluded), failures
```

<!-- SECTION:WALKTHROUGH -->
## 4. Walk-through (plain English)

### 4.1 Step-by-step

1. As before, walk the topic tree in portal order and list each
   article-carrying topic (paging unchanged).
2. For every entry, look at the *end* of its name. If it ends in the
   word "Historical" or "Rescinded" (whole word — the character before
   it is not a letter), count it as listed *and* excluded, and move on:
   no content request, no politeness delay, nothing in the output.
3. Otherwise count it as listed, pace the crawl, fetch its content,
   convert, and add it to the article list — exactly as before.
4. After the walk, check gate A: did we *list* exactly as many entries
   as the root topic's `articleTotalCount` says the manual has? If not,
   the list endpoint lied (truncation) — fail with exit 2, write
   nothing. Skipping never affects this number.
5. Gate B happens inside `assemble`: the assembled article count must
   equal *listed − excluded*. If an article that should have been
   fetched is missing, fail with exit 2.
6. On success, the deliverable contains only current articles, in
   portal order, with a TOC numbered 1..(listed − excluded).

### 4.2 Worked example

A topic with three articles (live shapes, 2026-10-03):

| # | Name (verbatim) | Predicate | Action |
|---|---|---|---|
| 1 | `M21-1, Part I, Chapter 1, Section A - Historical` | ends `Historical`, preceded by space → **excluded** | counted listed+excluded, no fetch |
| 2 | `M21-1, Part II, Subpart iii, Chapter 2, Section H - Historical Guidance on Formal Applications …` | "Historical" not at end → **retained** | fetched, assembled |
| 3 | `M21-1, Part I, Chapter 5, Section E - Rescinded` | ends `Rescinded` → **excluded** | counted listed+excluded, no fetch |

With root `articleTotalCount = 3` for this mini-manual: `listed = 3`
→ gate A passes (`3 == 3`); `excluded = 2` → expected assembled `= 1`;
the one fetched article assembles → gate B passes (`1 == 1`). Output:
TOC with a single entry (#2's name). The old single gate would have
compared `1 == 3` and failed — which is why it had to be split.

<!-- SECTION:IMPLEMENTATION -->
## 5. Implementation

### 5.1 API surface

```python
# src/m21_crawl/articles.py
_EXCLUDED_RE: re.Pattern[str]  # module-level compiled regex


def is_excluded_article(name: str) -> bool: ...


# src/m21_crawl/cli.py (crawl_manual)
#   - `listed` / `excluded` counters
#   - gate A: `if listed != root.article_total_count: raise CompletenessError(...)`
#   - gate B: `assemble(articles, expected_count=listed - excluded)`
```

The predicate lives in `articles.py` (the article-domain module: naming
and listing contract); the gates live in `crawl_manual` (orchestration).
`assemble` is unchanged — its `expected_count` parameter is now supplied
as *listed − excluded* instead of the raw root total, and its docstring
is updated accordingly.

### 5.2 Edge cases

| Case | Behavior | Why |
|---|---|---|
| `…Section A - Historical` | excluded | standard marker |
| `…Section E - Rescinded` | excluded | standard marker |
| `…Chapter 4 -  Historical` (two spaces) | excluded | boundary = non-letter, spacing irrelevant (live, ×3) |
| `…Section K- Historical` (no space after dash) | excluded | boundary = non-letter (live, ×2) |
| name is exactly `Historical` / `Rescinded` | excluded | start-of-string satisfies the boundary |
| `…Section H - Historical Guidance on …` | **retained** | marker not at end (live: 3 such current articles) |
| `…- historically` (lowercase) | **retained** | contract is the portal's title-case marking; no live counterexample (pinned by test) |
| name ends `Historically` / `Rescinding` | **retained** | whole-word suffix only |
| duplicate id, first occurrence excluded, second retained | the retained one assembles (first-wins on the *retained* set) | dedupe semantics unchanged; decision is per-entry, in portal order |
| `E = 0` (no marked articles) | behavior identical to the pre-change crawl | `listed == rootTotal` (gate A) and `A == listed` (gate B) collapse to the old single gate |

### 5.3 Invariants and how to test them

- **I1** — a FakeClient whose topic mixes retained and marked articles
  must record **no** content request for the marked ones, and the output
  must contain only retained names (byte-exact expected document).
- **I2** — the three live "Historical Guidance …" shapes must be
  retained (unit tests on the predicate with the verbatim live names).
- **I3** — a fixture whose root total exceeds the listed count *while
  marked articles are present* must raise `CompletenessError` (the
  truncation stays loud even with skipping in effect).
- **I4** — the unchanged fixture suite (no marked names, root total
  equals article count) must pass byte-identically: pins `E = 0`
  equivalence with the old gate.

<!-- SECTION:TESTS -->
## 6. Tests

| Test (module) | Pins |
|---|---|
| `test_is_excluded_article_markers` (test_articles) | all live marker shapes (2.1 table) → excluded |
| `test_is_excluded_article_retained_names` (test_articles) | "Historical Guidance …" (×3 live shapes), `Historically`, lowercase `historical`, plain names → retained |
| `test_crawl_manual_skips_historical_rescinded` (test_cli) | I1 + I2: only retained articles fetched, byte-exact output, no content call for marked entries, gate passes with root total = listed |
| `test_completeness_gate_a_survives_skipping` (test_cli) | I3: root total > listed, with marked articles present → `CompletenessError`, `expected` = root total |
| existing `test_crawl_manual_byte_exact`, `test_sleep_between_article_fetches`, `test_main_returns_two_on_completeness_failure`, … | I4: `E = 0` equivalence; exit-code contract unchanged (0 / 1 / 2) |

<!-- SECTION:REFERENCES -->
## 7. References

- VA Knowva eBenefits article-list v11 (live full scan, 2026-10-03):
  785/785 entries carry `articleType=0, state="P", commitState=1`;
  marker distribution 290 / 48 / 5 / 442 by name shape (2.1); three
  current articles contain "Historical" mid-name.
- Sibling document: [manual-tree-crawl](manual-tree-crawl.md) (the
  pre-order walk whose entries this filters; supplies the root
  `articleTotalCount` used by gate A).
- Sibling document: [topic-article-paging](topic-article-paging.md)
  (the listing pipeline; its §2.3 backstop note — "caught downstream by
  the completeness check against the root topic's `articleTotalCount`"
  — is preserved here as gate A).
- `src/m21_crawl/assemble.py` (assembly + count gate; unchanged code).
- algorithm-records-keeper skill, `references/guards.md` (G1–G12 applied).
