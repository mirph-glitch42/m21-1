"""assemble: ordered document assembly + completeness check.

Turns the crawled, per-article Markdown into the final deliverable:

  1. one H1 title (the manual name, from ``config.MANUAL_TITLE``);
  2. a ``## Table of Contents`` numbered list of article names in portal
     order (never re-sorted);
  3. one ``## {name}`` section per article, optionally preceded by a
     ``> {breadcrumb}`` blockquote (the topic chain, root excluded) and
     followed by the article body.

Guarantees (pinned by tests/test_assemble.py):

  - deterministic: same input, byte-identical output;
  - dedupe by article id, first occurrence wins (order preserved);
  - ``len(deduped) != expected_count`` raises ``CompletenessError``
    (the caller — ``cli.crawl_manual`` — passes the expected count as
    listed − excluded; see
    ``algorithms/historical-rescinded-exclusion.md``);
  - an article carrying ``error`` renders the placeholder
    ``> [content unavailable: {error}]`` instead of its body;
  - blocks joined by ``\\n\\n``; exactly one trailing ``\\n``.

Assembly is deliberately trivial (documented in code, per the
pragmatic-programmer skill; no separate algorithm doc — see the package
docstring module list).
"""

from dataclasses import dataclass

from .config import MANUAL_TITLE


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
    return "\n\n".join(parts) + "\n"
