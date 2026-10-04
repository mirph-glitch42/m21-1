"""assemble: ordered document assembly + completeness check + internal links.

Turns the crawled, per-article Markdown into the final deliverable:

  1. one H1 title (the manual name, from ``config.MANUAL_TITLE``);
  2. a ``## Table of Contents`` numbered list of article names in portal
     order (never re-sorted);
  3. one ``## {name}`` section per article, optionally preceded by a
     ``> {breadcrumb}`` blockquote (the topic chain, root excluded) and
     followed by the article body;
  4. internal link resolution (final pass):
     ``algorithms/internal-link-resolution.md`` — cross-article hyperlinks
     (eGain article URLs) whose target id is in the manual become in-document
     anchors of that article's ``## {name}`` heading (``heading_anchor``);
     unknown ids, images, and external links stay verbatim.

Guarantees (pinned by tests/test_assemble.py):

  - deterministic: same input, byte-identical output;
  - dedupe by article id, first occurrence wins (order preserved);
  - ``len(deduped) != expected_count`` raises ``CompletenessError``
    (the caller — ``cli.crawl_manual`` — passes the expected count as
    listed − excluded; see
    ``algorithms/historical-rescinded-exclusion.md``);
  - an article carrying ``error`` renders the placeholder
    ``> [content unavailable: {error}]`` instead of its body;
  - blocks joined by ``\\n\\n``; exactly one trailing ``\\n``;
  - internal link resolution is a pure, single-pass rewrite: it never
    creates or removes links, only redirects known cross-article ids to
    existing headings (doc invariants A/B/C).
"""

import re
from dataclasses import dataclass

from .config import MANUAL_TITLE

# eGain article-URL link destination (any host; mdconv already canonicalized
# the shape — algorithms/html-to-markdown-section-extraction.md ``_rewrite_url``).
# Group 2 is the article id: the canonical identity used for resolution.
_ARTICLE_LINK = re.compile(r"\]\((https?://[^/\s)]+/system/ws/v\d+/ss/article/(\d+))\)")


class CompletenessError(RuntimeError):
    """The assembled article count does not match the portal's expectation."""

    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"completeness check failed: expected {expected} articles but assembled {actual}"
        )


@dataclass(frozen=True)
class Article:
    """One article slot in the assembled manual.

    ``body_md`` is the article's Markdown (from ``mdconv.convert``); it is
    ignored when ``error`` is set. ``breadcrumb`` is the topic chain for the
    article's topic, e.g. ``"Part 1 \u203a Chapter 1-1"`` (already joined,
    root excluded); ``""`` means no breadcrumb line is emitted.
    """

    id: str
    name: str
    body_md: str = ""
    breadcrumb: str = ""
    error: str | None = None


def heading_anchor(heading: str) -> str:
    """GitHub/GFM anchor slug for a heading (internal-link-resolution.md 2.5).

    Lowercase; keep Unicode letters/digits, spaces, hyphens; spaces → ``-``.
    ``"M21-1, Part II - POA"`` → ``"m21-1-part-ii---poa"`` (the triple
    hyphen from ``" - "`` is intentional — it matches the renderer).
    """
    kept = "".join(ch for ch in heading.lower() if ch.isalnum() or ch in " -")
    return kept.replace(" ", "-")


def _internalize_links(document: str, anchor_by_id: dict[str, str]) -> str:
    """Rewrite known cross-article links to in-document anchors (doc C1–C7).

    Unknown ids, images, external links, and every non-candidate byte pass
    through verbatim (invariant A: identity recovery).
    """

    def _replace(match: re.Match[str]) -> str:
        anchor = anchor_by_id.get(match.group(2))
        if anchor is None:
            return match.group(0)  # unknown id: keep the portal URL (C7)
        return f"](#{anchor})"

    return _ARTICLE_LINK.sub(_replace, document)


def _dedupe_first_wins(articles: list[Article]) -> list[Article]:
    seen: set[str] = set()
    out: list[Article] = []
    for article in articles:
        if article.id in seen:
            continue
        seen.add(article.id)
        out.append(article)
    return out


def _article_block(article: Article) -> str:
    parts = [f"## {article.name}"]
    if article.breadcrumb != "":
        parts.append(f"> {article.breadcrumb}")
    body = (
        f"> [content unavailable: {article.error}]"
        if article.error is not None
        else article.body_md
    )
    body = body.rstrip("\n")
    if body != "":
        parts.append(body)
    return "\n\n".join(parts)


def assemble(
    articles: list[Article],
    *,
    expected_count: int,
    title: str = MANUAL_TITLE,
) -> str:
    """Assemble the final Markdown document (see module docstring).

    Raises ``CompletenessError`` when the deduped article count differs from
    ``expected_count``; raises ``TypeError`` for a non-int ``expected_count``.
    """
    if not isinstance(expected_count, int):
        raise TypeError("expected_count must be an int")
    deduped = _dedupe_first_wins(list(articles))
    if len(deduped) != expected_count:
        raise CompletenessError(expected_count, len(deduped))

    toc_lines = "\n".join(f"{i}. {a.name}" for i, a in enumerate(deduped, start=1))
    parts = [f"# {title}"]
    if toc_lines != "":
        parts.append("## Table of Contents\n\n" + toc_lines)
    else:
        parts.append("## Table of Contents")
    parts.extend(_article_block(a) for a in deduped)
    document = "\n\n".join(parts) + "\n"
    # Final pass (after the gates): resolve cross-article hyperlinks to the
    # headings this same list produced. Ids are unique post-dedupe; duplicate
    # names share the first heading's slug (first-occurrence semantics, C4).
    anchor_by_id = {a.id: heading_anchor(a.name) for a in deduped}
    return _internalize_links(document, anchor_by_id)
