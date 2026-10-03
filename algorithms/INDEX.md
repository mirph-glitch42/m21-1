# Algorithm Registry

> One row per algorithm document in this directory. Keep sorted by slug.
> Update the row in the **same change** that changes the document (G8/G9).
> Status values: `draft` · `implemented` · `backfilled` · `deprecated`.

| Slug | Name | Version | Status | File | One-line summary |
|---|---|---|---|---|---|
| html-to-markdown-section-extraction | Rich HTML → Markdown block converter (eGain article content extraction) | 0.2.0 | implemented | [html-to-markdown-section-extraction.md](html-to-markdown-section-extraction.md) | Total, deterministic block/inline tree-walk that turns CMS article HTML (tables, layout tables, spans, eGainArticleLink) into byte-stable GFM Markdown |
| manual-tree-crawl | In-order manual topic-tree crawl (pre-order flatten with dedupe) | 0.2.0 | implemented | [manual-tree-crawl.md](manual-tree-crawl.md) | Iterative visited-set DFS that flattens the portal topic tree into the manual's pre-order, deduped, cycle-safe topic list |

## Rules

1. Add a row when a document is created; never delete a row (mark `deprecated` instead).
2. The `File` link is the canonical location — no copies elsewhere in the repo.
3. `Version` must equal the document's `METADATA` version (CI can assert this).
4. Backfilled rows keep `Status: backfilled` permanently as a provenance marker; behavioral changes do not remove it.
5. CI check: every `algorithms/*.md` (except `INDEX.md`) has exactly one row, and every row points at an existing file.
