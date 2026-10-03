# Paged Topic Article Listing (Range-Based Pagination for the Knowva Article List)

<!-- INDEX:BEGIN format=tsv version=1 -->
id	start_line	end_line
INDEX_BLOCK	3	13
METADATA	15	36
THEORY	37	139
PSEUDOCODE	140	185
WALKTHROUGH	186	216
IMPLEMENTATION	217	282
TESTS	283	317
REFERENCES	318	336
<!-- INDEX:END -->

<!-- SECTION:METADATA -->
## 1. Metadata

| Field | Value |
|---|---|
| Name | Paged topic article listing (range-based pagination, `pagingInfo`-driven termination) |
| Slug | topic-article-paging |
| Version | 0.2.0 |
| Status | implemented |
| Author | Bionic agent (on behalf of murphyjj) |
| Created | 2026-10-03 |
| Last modified | 2026-10-03 |
| Status history | 0.1.0 (2026-10-03): initial draft — the portal silently caps article lists at 10 per response; the crawl was dropping 45 of 785 articles · 0.2.0 (2026-10-03): implemented in `src/m21_crawl/articles.py` (`PAGE_SIZE`, `_paging_total`, paged `list_topic_articles`); strict `pagingInfo` validation in the contract; 5 new tests in `tests/test_articles.py` |
| Languages | Python 3.12 (implementation); pseudocode is language-agnostic |
| Implementation location | `src/m21_crawl/articles.py` — `PAGE_SIZE` L27–31; `_paging_total` L34–52; `list_topic_articles` L55–91 |
| Time complexity | O(P) HTTP calls, P = number of pages ≤ maxRange (see 2.4) |
| Space complexity | O(T) — T = total article entries for the topic |
| Determinism | deterministic (pure orchestration of the server's responses) |
| Dependencies | `m21_crawl.client.Client` (session + transport), `m21_crawl.config` (portal constants) |
| Thread safety | not thread-safe by contract; single-threaded crawl, no shared state |
| Related documents | [manual-tree-crawl](manual-tree-crawl.md), [html-to-markdown-section-extraction](html-to-markdown-section-extraction.md) |

<!-- SECTION:THEORY -->
## 2. Theory

### 2.1 Problem definition

**Input.** A topic id (17-digit portal id, e.g. `554400000015005`) and an
authenticated portal client (`Client.get(path, params)` → parsed JSON).

**Output.** The complete list of that topic's direct article entries, in the
portal's order.

**The constraint that makes this an algorithm.** The portal's article-list
endpoint is *capped and silent about it*:

```
GET /ws/v11/ss/article?portalId=...&usertype=...&topicId=...&$lang=...
→ {"article": [ ...at most 10 entries... ],
   "pagingInfo": {"count": 10, "pageNumber": 1, "rangeStart": 0,
                  "rangeSize": 10, "maxRange": 18}}
```

Verified live (2026-10-03): 13 topics declare `articleCount` 11–20 but the
unpaged call returns exactly 10 entries with HTTP 200 and no error field.
The total for the topic is reported as `pagingInfo.maxRange`; the slice
actually returned is `[pagingInfo.rangeStart, pagingInfo.rangeStart +
pagingInfo.count)`.

Paging is opt-in via query parameters, also verified live: the portal's own
Angular UI (`app-bundle.js`, `SelfServiceArticleService`) sends RANGE mode —
`angular.equals(n,"RANGE")&&(s.$rangestart=l,s.$rangesize=m)` — i.e. the
parameters `$rangestart` (0-based offset) and `$rangesize` (slice length).
Other guessed names (`top`, `skip`, `page`, `pageSize`, `pageNumber`,
`rangeStart`, …) are silently ignored and page 1 is returned.

**Contract.**

1. Every entry of the topic is returned exactly once, in portal order
   (concatenation of the slices in request order; nothing re-sorted).
2. The loop terminates: bounded by `maxRange`, the server-declared total.
3. Loud failure: a response without `article` (a list) or `pagingInfo`
   (int `count`, int `maxRange`) raises `ValueError` — a silent single page
   is precisely the defect this algorithm exists to prevent.

### 2.2 Why this approach

- **RANGE mode with `maxRange`-driven termination (chosen).** The exact
  scheme the portal UI uses; `maxRange` makes termination self-describing
  and the step is the *returned* page length, so a server that honors a
  smaller slice than requested cannot skip entries.
- **Single call with a large `$rangesize`.** Rejected: 50 was honored for an
  18-entry topic, but the server cap is unverified — a silent truncation at
  an unknown cap would reproduce exactly the bug being fixed.
- **PAGE mode (`$pagenum`/`$pagesize`).** Verified working, but page count
  would have to be guessed or probed; RANGE + `maxRange` needs no guessing.
- **Loop until an empty page.** Costs one extra call per topic (290 topics
  → 290 extra round-trips) and trusts the server to return empty past the
  end, where `maxRange` already states the end.
- **Ignore paging (the pre-fix behavior).** Rejected: it is the defect —
  740 of 785 articles assembled, caught by the completeness gate.

### 2.3 Correctness argument

Invariant after each completed iteration, with accumulated offset
`range_start` (the 0-based offset of the *next* slice):

- **I1 (order).** `out` equals the concatenation of the slices
  `[0, c₁), [c₁, c₁+c₂), …` returned so far, in request order. The server
  returns each slice in portal order and the slices are requested in
  ascending offset order, so `out` is a portal-ordered prefix of the topic's
  list. (Verified live: page 1 + page 2 concatenated byte-order-match the
  order of a single 18-entry request.)
- **I2 (disjoint, covering slices).** Consecutive requests start at the
  previous request's `range_start + count`, so no entry index belongs to two
  slices (no duplicates), and on exit `range_start + count ≥ maxRange`, so
  the union covers `[0, maxRange)` — every entry index the server reports as
  existing (no omissions).
- **I3 (termination).** A continued iteration increments `range_start` by
  `count ≥ 1`; the loop can continue only while `range_start + count <
  maxRange`, i.e. `range_start < maxRange`. Hence at most `maxRange`
  iterations — finite, server-declared.

I1 + I2 imply the output contract; I3 implies termination. The residual
risk — the server lying about `maxRange` or returning an early empty page —
is caught downstream by the completeness check against the root topic's
`articleTotalCount` (crawl exit 2), not by this function.

### 2.4 Complexity

Let `T` = total entries of the topic, `P` = number of calls. Each call
returns `count_i` entries; the loop makes `P` calls where
`Σ count_i = T` (well-behaved server). Time is `O(Σ count_i + P) =
O(T + P)`; since every non-empty page contributes at least one entry,
`P ≤ T`, so **time O(T)** plus `P` network round-trips (the dominant cost,
independent of this algorithm's bookkeeping). Space is **O(T)** for the
output list plus O(1) working state (`range_start`, the current page). For
the real crawl: T = 785 total, and at most 13 topics need a second page
(declared 11–20 at page size 10) — ≤ 13 extra calls, negligible against the
~785 content fetches.

### 2.5 Deviations

none — documented before implementation.

<!-- SECTION:PSEUDOCODE -->
## 3. Pseudocode

```
PAGE_SIZE <- 10        # the server's own default rangeSize; verified honored

function list_topic_articles(client, topic_id) -> entries:
    # Pre: client is an authenticated portal client.
    # Post: entries is the complete, portal-ordered article list of topic_id;
    #      or a ValueError was raised (malformed response).
    out         <- []
    range_start <- 0                      # 0-based offset of the next slice
    loop:
        page <- client.get(ARTICLE_LIST_PATH, {
            "portalId": PORTAL_ID, "usertype": USERTYPE,
            "topicId": topic_id, "$lang": LANG,
            "$rangestart": str(range_start),  # offset of this slice (RANGE mode)
            "$rangesize": str(PAGE_SIZE),     # slice length
        })
        # Strict shape checks — the portal always sends both keys; a
        # malformed response must fail loudly, never degrade to one page.
        if page is not a mapping or "article" not in page:
            raise ValueError(topic_id, "no 'article' key")
        batch <- page["article"]
        if batch is not a list:
            raise ValueError(topic_id, "'article' is not a list")
        pi <- page["pagingInfo"]
        if pi is not a mapping:
            raise ValueError(topic_id, "no 'pagingInfo'")
        count     <- pi["count"]
        max_range <- pi["maxRange"]
        if count is not an int or max_range is not an int:
            raise ValueError(topic_id, "pagingInfo count/maxRange not ints")
        out <- out ++ batch               # append in request order (I1)
        if count == 0:                    # empty page: nothing more to fetch
            break
        if range_start + count >= max_range:    # final slice reached (I2)
            break
        range_start <- range_start + count      # step by the RETURNED length,
    return out                    # never by PAGE_SIZE (a smaller honored slice
                                  # must not skip entries — I2)

Termination (I3): each continued iteration raises range_start by count ≥ 1,
and continuation requires range_start < max_range ⇒ ≤ max_range iterations.
```

<!-- SECTION:WALKTHROUGH -->
## 4. Walk-through (plain English)

### 4.1 Step-by-step

1. Ask the portal for slice `[0, 10)` of the topic's articles
   (`$rangestart=0`, `$rangesize=10`).
2. Check the answer is well-formed (article list + `pagingInfo` with int
   `count`/`maxRange`); if not, fail loudly.
3. Append the returned entries to the result, after everything already
   collected — portal order is preserved because we request slices in
   ascending order and never re-sort.
4. Read `count` and `maxRange`. If the page was empty, stop. If
   `range_start + count` already reached `maxRange`, this was the last
   slice — stop.
5. Otherwise advance `range_start` by the number of entries actually
   returned and go to step 1. Stepping by the returned count (not by the
   requested page size) means a server that honors a smaller slice than
   requested can never cause entries to be skipped.

### 4.2 Worked example

Synthetic topic with 18 entries (ids `A01…A18`), `maxRange=18`:

| Call | Request | Response entries | `count` | `maxRange` | Stop check (`offset + count ≥ maxRange`) | Result |
|---|---|---|---|---|---|---|
| 1 | `$rangestart=0, $rangesize=10` | `A01…A10` | 10 | 18 | 0 + 10 = 10 ≥ 18? no | continue; next offset = 10 |
| 2 | `$rangestart=10, $rangesize=10` | `A11…A18` | 8 | 18 | 10 + 8 = 18 ≥ 18? yes | stop |

Result: `A01…A18` — 18 entries, 2 calls, no duplicates, portal order.

<!-- SECTION:IMPLEMENTATION -->
## 5. Implementation notes (entry-level guide)

### 5.1 Data structures

- `out: list[dict[str, Any]]` — append-only result; never re-sorted (the
  crawl relies on portal order end-to-end).
- `range_start: int` — 0-based offset of the next slice; starts at 0 and
  advances by each page's `count`.
- `PAGE_SIZE = 10` — module constant in `articles.py`. The server's own
  default `rangeSize` (every observed response has `rangeSize: 10`); a
  larger value (50) was verified honored, but 10 is the value the server
  demonstrably always accepts, so it is the safe choice. Cost of the small
  page: at most 13 extra calls across the whole manual (13 topics declare
  11–20 articles).

### 5.2 Edge cases and defined behavior

| Case | Defined behavior | Why |
|---|---|---|
| Topic with 0 articles (`count=0`, `maxRange=0`) | one call, returns `[]` | empty page branch stops the loop immediately |
| Single article (`maxRange=1`) | one call, returns the one entry | `0 + 1 ≥ 1` stops after page 1 |
| `maxRange` exactly 10 | one call (no second request) | `0 + 10 ≥ 10` — the final-slice check, not the empty page, ends the loop |
| `maxRange` 11 | two calls: 10 + 1 | second slice has `count=1`; `10 + 1 ≥ 11` stops |
| Server returns fewer than `PAGE_SIZE` (cap) | step by the returned `count`; next offset = previous offset + count | stepping by `PAGE_SIZE` would skip the gap |
| Empty page before `maxRange` (server inconsistency) | loop stops with what was collected; the crawl's completeness check against the root `articleTotalCount` fails loudly (exit 2) | loud, centralized failure beats a per-topic hang |
| Response without `article` key / `article` not a list / without `pagingInfo` / non-int `count` or `maxRange` | raises `ValueError` | silent single-page degradation is the defect this algorithm removes |

### 5.3 Invariants and how to test them

- **I1 (order):** a fake client that returns labeled slices must see the
  result as the concatenation of those slices in call order.
- **I2 (no duplicates / no omissions):** the fake records the
  `$rangestart` of every call; assert the sequence is exactly
  `0, c₁, c₁+c₂, …` and the result length equals `maxRange` (well-behaved
  fake).
- **I3 (termination):** the fake for the "empty page before maxRange" case
  returns an empty list forever; the call must not loop past the empty page
  (assert call count is exactly 2).
- **Loud failure:** each malformed payload (no `article`, non-list
  `article`, no `pagingInfo`, string `count`) must raise `ValueError`.

### 5.4 Pitfalls and known traps

- **Stepping by `PAGE_SIZE` instead of the returned `count`** skips entries
  whenever the server honors a slice smaller than requested.
- **Trusting HTTP 200.** The portal returns 200 with a truncated list and
  no error field; `pagingInfo` is the only signal.
- **Guessing parameter names.** `$rangestart`/`$rangesize` (note the
  dollar signs, OData style) are the only names the server accepts; `top`,
  `skip`, `page`, `pageSize`, `rangeStart`, `pageNumber`, … are silently
  ignored and page 1 is returned — the previous bug.
- **Re-sorting.** Any `sorted()` on the collected entries is a defect: the
  manual's order is the portal's order.
- **Python `isinstance(True, int)` is `True`.** The portal sends real JSON
  integers; a boolean `count` would be a malformed response either way —
  not worth special-casing, but do not "fix" it into accepting booleans.

### 5.5 Language notes

Python 3.12. A plain `while True:` with explicit `break`s (mirrors the
pseudocode); query parameters are `dict[str, str]` per the `Client`
protocol, so offsets/sizes are passed as `str(...)`. No generator trickery
— the function owns the loop so the termination argument stays visible in
the source.

<!-- SECTION:TESTS -->
## 6. Test cases and sample data

All data synthetic (G11); the fake client is a paged responder that records
every `(path, params)` pair, so request sequences are assertable.

| # | Name | Input (sample data) | Expected output | Why it matters |
|---|---|---|---|---|
| 1 | happy path, single page | 1 page: `article=[A1, A2]`, `pagingInfo={count:2, maxRange:2}` | `[A1, A2]`, exactly 1 call, `$rangestart="0"`, `$rangesize="10"` | request shape + order baseline |
| 2 | edge: empty topic | `article=[]`, `pagingInfo={count:0, maxRange:0}` | `[]`, exactly 1 call | zero-capacity input terminates immediately |
| 3 | multi-page (the fixed bug) | page 1: 10 entries, `{count:10, maxRange:18}`; page 2: 8 entries, `{count:8, maxRange:18}` | 18 entries in slice order; `$rangestart` sequence `["0", "10"]`; 2 calls | topics declaring 11–20 must not lose entries |
| 4 | degenerate: early empty page | page 1: 10 entries, `{count:10, maxRange:18}`; page 2: `[]`, `{count:0, maxRange:18}` | the 10 entries; exactly 2 calls (no loop past the empty page) | I3 under server inconsistency; completeness gate is the backstop |
| 5 | adversarial: server caps the page | `maxRange=12`; pages of 5, 5, 2 (`count` 5, 5, 2) | 12 entries; `$rangestart` sequence `["0", "5", "10"]` | step must be the returned `count`, not `PAGE_SIZE` (I2) |
| 6 | malformed: no `pagingInfo` | `{"article": [A1]}` | `ValueError` | loud failure replaces silent one-page degradation |
| 7 | malformed: `article` not a list | `{"article": "nope"}` | `ValueError` | pre-existing strictness preserved |
| 8 | malformed: non-int `count` | `article=[A1]`, `pagingInfo={count:"10", maxRange:18}` | `ValueError` | type-strict `pagingInfo` parsing |

### 6.1 Property tests (preferred)

For any `maxRange M` and any well-behaved fake (slices of the canonical
list, `count` = slice length):

- result length = M and result = the canonical list (no duplicates, no
  omissions, portal order);
- the `$rangestart` sequence is strictly increasing and each value equals
  the sum of all previous page counts;
- call count = 1 + ⌊(M − 1) / effective_page_length⌋.

### 6.2 Performance acceptance

Real crawl: 785 articles, 13 topics need a second page → ≤ 13 extra list
calls on top of the 290 topics' first pages; within the existing ~5-minute
crawl budget (dominated by the ~785 content fetches and the politeness
delay).

<!-- SECTION:REFERENCES -->
## 7. References

- VA Knowva eBenefits article service v11 (reverse-engineered contract;
  live samples verified 2026-10-03): `GET /system/ws/v11/ss/article` with
  `$rangestart`/`$rangesize` (RANGE mode) → `{"article": [≤10 entries],
  "pagingInfo": {count, pageNumber, rangeStart, rangeSize, maxRange}}`;
  unparameterized calls return page 1 only, HTTP 200, no error field.
- The portal's Angular UI bundle (`app-bundle.js`,
  `SelfServiceArticleService`): `angular.equals(n,"PAGE") ?
  (s.$pagenum=l, s.$pagesize=m) : angular.equals(n,"RANGE") &&
  (s.$rangestart=l, s.$rangesize=m)` — the paging parameter names the
  official client uses.
- Sibling document: [manual-tree-crawl](manual-tree-crawl.md) (walks the
  tree whose topics this listing serves; supplies the expected-count
  backstop via the root's `articleTotalCount`).
- Sibling document: [html-to-markdown-section-extraction](html-to-markdown-section-extraction.md)
  (converts each fetched article's HTML body).
- algorithm-records-keeper skill, `references/guards.md` (G1–G12 applied).
