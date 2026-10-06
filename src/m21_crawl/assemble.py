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
     anchors of that article's *own* ``## {name}`` heading; anchors are
     GitHub document-order slugs (``Slugger``: a duplicate heading gets
     ``-1``, ``-2``, …, so each id resolves to its own heading); unknown
     ids, images, and external links stay verbatim.

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

# Heading / fence line shapes for body-heading extraction (B3 dedup context;
# same shapes as the test oracle in tests/test_assemble.py).
_BODY_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$")
_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


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


class Slugger:
    """GitHub document-order slug dedup (github-slugger ``occurrences``).

    The first heading to claim a base slug keeps it; later duplicates get
    ``-1``, ``-2``, … — exactly the order GitHub assigns anchors in the
    rendered document (internal-link-resolution.md 2.6, B3). The base slug
    is ``heading_anchor`` (unchanged, 2.5); only the dedup is added.
    """

    def __init__(self) -> None:
        self._seen: dict[str, int] = {}

    def slug(self, text: str) -> str:
        base = heading_anchor(text)
        if base in self._seen:
            self._seen[base] += 1
            return f"{base}-{self._seen[base]}"
        self._seen[base] = 0
        return base


def _body_heading_texts(body_md: str) -> list[str]:
    """Heading texts in ``body_md``, document order, fenced code skipped.

    ``#``-markers stripped; a line is a heading only when not inside a
    fenced code block (opened and closed with the same fence char, up to
    3 leading spaces). Defensive: the live manual has 0 fences today, but
    ``mdconv`` can emit ``` fences for ``<pre>`` (doc 5.2).
    """
    out: list[str] = []
    fence_char: str | None = None
    for line in body_md.splitlines():
        fence = _FENCE.match(line)
        if fence:
            ch = fence.group(1)[0]
            if fence_char is None:
                fence_char = ch
            elif ch == fence_char:
                fence_char = None
            continue
        if fence_char is not None:
            continue
        m = _BODY_HEADING.match(line)
        if m:
            out.append(m.group(1))
    return out


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


def _emitted_body(article: Article) -> str:
    """The article body as it appears in the document (placeholder or body).

    Single source of truth for what gets emitted — used by ``_article_block``
    (rendering) and the final pass's slug walk (dedup context), so the two
    never disagree (doc pseudocode: "the body as EMITTED").
    """
    body = (
        f"> [content unavailable: {article.error}]"
        if article.error is not None
        else article.body_md
    )
    return body.rstrip("\n")


def _article_block(article: Article) -> str:
    parts = [f"## {article.name}"]
    if article.breadcrumb != "":
        parts.append(f"> {article.breadcrumb}")
    body = _emitted_body(article)
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
    # headings this same list produced, in GitHub document order (B3, C4):
    # the H1 title and the TOC H2 first, then each article's H2 and its
    # emitted body's headings in order. An article whose name collides with
    # an earlier heading gets (and its links resolve to) its own deduped
    # slug — e.g. the 2nd "General" → "general-1".
    slugger = Slugger()
    slugger.slug(title)
    slugger.slug("Table of Contents")
    anchor_by_id: dict[str, str] = {}
    for a in deduped:
        anchor_by_id[a.id] = slugger.slug(a.name)
        for bh in _body_heading_texts(_emitted_body(a)):
            slugger.slug(bh)
    return _internalize_links(document, anchor_by_id)
