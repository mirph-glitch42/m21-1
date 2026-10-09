# Algorithm Registry

> One row per algorithm document in this directory. Keep sorted by slug.
> Update the row in the **same change** that changes the document (G8/G9).
> Status values: `draft` · `implemented` · `backfilled` · `deprecated`.

| Slug | Name | Version | Status | File | One-line summary |
|---|---|---|---|---|---|
| historical-rescinded-exclusion | Historical/Rescinded article exclusion (name-marker filtering + two-gate completeness) | 0.2.0 | implemented | [historical-rescinded-exclusion.md](historical-rescinded-exclusion.md) | Word-boundary name-suffix predicate that skips portal articles marked `Historical`/`Rescinded` before fetch, with a truncation gate (listed == root total) kept loud beside the fetch gate (assembled == listed − excluded) |
| html-to-markdown-section-extraction | Rich HTML → Markdown block converter (eGain article content extraction) | 0.11.0 | implemented | [html-to-markdown-section-extraction.md](html-to-markdown-section-extraction.md) | Total, deterministic block/inline tree-walk that turns CMS article HTML (tables, layout tables, spans, eGainArticleLink) into byte-stable GFM Markdown — layout frames dissolve to real headings (D8), incl. container-wrapped labels (D12), Change Date frames render as quote blocks (B11), decorative hr rules render nothing (D9), raw spaces in link/image destinations become %20 (D10), legacy-host URLs remap to the live host (D11), invisible heading-bearing first cells stay frame labels (D5∪D12) |
| internal-link-resolution | Internal link resolution — rewrite cross-article hyperlinks into in-document section anchors | 0.5.0 | implemented | [internal-link-resolution.md](internal-link-resolution.md) | Anchors computed in document order (github-slugger occurrence replica) ahead of rendering; eGain article-URL hyperlinks rewritten to the target article's own `## ` heading anchor; TOC entries link to their article's own anchor (B7); in-document `#fragment` links (incl. To Top) resolved against the defined-anchor set — case-variants canonicalized, absent `art_{id}_…` remapped to the article's H2 (B8); unknown ids keep the portal URL |
| manual-tree-crawl | In-order manual topic-tree crawl (pre-order flatten with dedupe) | 0.2.0 | implemented | [manual-tree-crawl.md](manual-tree-crawl.md) | Iterative visited-set DFS that flattens the portal topic tree into the manual's pre-order, deduped, cycle-safe topic list |
| topic-article-paging | Paged topic article listing (RANGE-mode pagination, `pagingInfo`-driven termination) | 0.2.0 | implemented | [topic-article-paging.md](topic-article-paging.md) | `$rangestart`/`$rangesize` paging loop that collects every article of a topic in portal order despite the portal's silent 10-per-page cap |

## Rules

1. Add a row when a document is created; never delete a row (mark `deprecated` instead).
2. The `File` link is the canonical location — no copies elsewhere in the repo.
3. `Version` must equal the document's `METADATA` version (CI can assert this).
4. Backfilled rows keep `Status: backfilled` permanently as a provenance marker; behavioral changes do not remove it.
5. CI check: every `algorithms/*.md` (except `INDEX.md`) has exactly one row, and every row points at an existing file.
