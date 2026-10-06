"""assemble: ordered document assembly + completeness check (TDD).

Contract (pinned by these byte-exact tests):

  - output = H1 title, a ``## Table of Contents`` numbered list of article
    names in portal order, then one ``## {name}`` section per article, each
    optionally preceded by a ``> {breadcrumb}`` blockquote and followed by
    the article's Markdown body;
  - blocks joined by ``\\n\\n``; exactly one trailing ``\\n``;
  - articles deduped by id, first occurrence wins (order preserved);
  - ``len(deduped) != expected_count`` raises ``CompletenessError`` with
    ``.expected`` / ``.actual``;
  - an article carrying ``error`` renders the placeholder block
    ``> [content unavailable: {error}]`` instead of its body;
  - empty breadcrumb / empty body lines are omitted (no stray ``>`` or
    blank paragraphs);
  - deterministic: same input, byte-identical output;
  - cross-article hyperlinks (eGain article URLs) whose target id is in the
    manual are rewritten to in-document anchors of that article's ``## ``
    heading; unknown ids, images, and external links stay verbatim;
    anchors use GitHub's document-order slug dedup (a duplicate heading
    gets ``-1``, ``-2``, …), so each id resolves to its own heading
    (algorithms/internal-link-resolution.md, B3).
"""

import re

import pytest

from m21_crawl.assemble import Article, CompletenessError, assemble, heading_anchor

# Synthetic portal ids and the live article-URL host (shape verified 2026-10-03).
_LINK_BASE = "https://www.knowva.ebenefits.va.gov/system/ws/v11/ss/article/"


def _articles(n: int) -> list[Article]:
    return [
        Article(id=str(i), name=f"Article {i}", body_md=f"Body {i}.\n", breadcrumb="P1 › C1")
        for i in range(1, n + 1)
    ]


def test_single_article_byte_exact() -> None:
    out = assemble(
        [Article(id="1", name="General", body_md="Intro.\n", breadcrumb="P1 › C1")],
        expected_count=1,
    )
    assert out == (
        "# M21-1 Adjudication Procedures Manual\n"
        "\n"
        "## Table of Contents\n"
        "\n"
        "1. General\n"
        "\n"
        "## General\n"
        "\n"
        "> P1 \u203a C1\n"
        "\n"
        "Intro.\n"
    )


def test_two_articles_order_preserved() -> None:
    out = assemble(_articles(2), expected_count=2)
    toc = out.split("## Table of Contents\n\n")[1].split("\n\n## ")[0]
    assert toc == "1. Article 1\n2. Article 2"
    assert out.index("## Article 1") < out.index("## Article 2")


def test_empty_articles_zero_expected() -> None:
    out = assemble([], expected_count=0)
    assert out == "# M21-1 Adjudication Procedures Manual\n\n## Table of Contents\n"


def test_dedupe_first_wins_preserves_order() -> None:
    articles = [
        Article(id="2", name="Second", body_md="B2.\n"),
        Article(id="1", name="First", body_md="B1.\n"),
        Article(id="2", name="Second (dup)", body_md="DUP.\n"),
    ]
    out = assemble(articles, expected_count=2)
    assert "Second (dup)" not in out
    assert "DUP." not in out
    # first-wins: the id "2" entry (name "Second") keeps its slot before id "1"
    assert out.index("## Second") < out.index("## First")


def test_completeness_mismatch_raises_with_counts() -> None:
    with pytest.raises(CompletenessError) as exc_info:
        assemble(_articles(3), expected_count=785)
    err = exc_info.value
    assert err.expected == 785
    assert err.actual == 3
    assert "785" in str(err) and "3" in str(err)


def test_failed_article_renders_placeholder() -> None:
    article = Article(
        id="1",
        name="Broken",
        body_md="SHOULD NOT APPEAR.\n",
        breadcrumb="P1",
        error="lxml failed on <x",
    )
    out = assemble([article], expected_count=1)
    assert "SHOULD NOT APPEAR." not in out
    assert "> [content unavailable: lxml failed on <x]" in out


def test_empty_breadcrumb_omitted() -> None:
    out = assemble(
        [Article(id="1", name="NoCrumb", body_md="B.\n", breadcrumb="")], expected_count=1
    )
    assert out == (
        "# M21-1 Adjudication Procedures Manual\n"
        "\n"
        "## Table of Contents\n"
        "\n"
        "1. NoCrumb\n"
        "\n"
        "## NoCrumb\n"
        "\n"
        "B.\n"
    )


def test_empty_body_omits_body_block() -> None:
    out = assemble([Article(id="1", name="Empty", body_md="", breadcrumb="P1")], expected_count=1)
    assert out == (
        "# M21-1 Adjudication Procedures Manual\n"
        "\n"
        "## Table of Contents\n"
        "\n"
        "1. Empty\n"
        "\n"
        "## Empty\n"
        "\n"
        "> P1\n"
    )


def test_body_trailing_newline_normalized() -> None:
    # Bodies may or may not carry their own trailing newline; output shape is fixed.
    out = assemble(
        [Article(id="1", name="A", body_md="No newline here", breadcrumb="")],
        expected_count=1,
    )
    assert out.endswith("## A\n\nNo newline here\n")
    assert not out.endswith("\n\n")


def test_deterministic_byte_identical() -> None:
    articles = _articles(4)
    assert assemble(articles, expected_count=4) == assemble(articles, expected_count=4)


def test_custom_title() -> None:
    out = assemble(
        [Article(id="1", name="A", body_md="B.\n")],
        expected_count=1,
        title="Custom Manual",
    )
    assert out.startswith("# Custom Manual\n\n")


# --- internal link resolution (algorithms/internal-link-resolution.md) ------

_TITLE = "M21-1 Adjudication Procedures Manual"


def _oracle_slug(text: str, seen: dict[str, int]) -> str:
    base = heading_anchor(text)
    if base in seen:
        seen[base] += 1
        return f"{base}-{seen[base]}"
    seen[base] = 0
    return base


def _oracle_headings(body: str) -> list[str]:
    """Heading texts in ``body`` (document order), fenced code skipped."""
    out: list[str] = []
    fence_char: str | None = None
    for line in body.splitlines():
        fence = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if fence:
            ch = fence.group(1)[0]
            if fence_char is None:
                fence_char = ch
            elif ch == fence_char:
                fence_char = None
            continue
        if fence_char is not None:
            continue
        h = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if h:
            out.append(h.group(1))
    return out


def _oracle(articles: list[Article], title: str = _TITLE) -> tuple[dict[str, str], set[str]]:
    """Independent document-order slug oracle (doc cases 9 and 12).

    Walks the emitted document's headings in order — H1 title, H2 TOC, then
    each article's H2 name and its *emitted* body's headings (fence-aware) —
    and records (a) the slug each article id's own H2 receives and (b) the
    set of every heading's slug.
    """
    seen: dict[str, int] = {}

    def slug(text: str) -> str:
        return _oracle_slug(text, seen)

    all_anchors: set[str] = {slug(title), slug("Table of Contents")}
    anchor_by_id: dict[str, str] = {}
    for a in articles:
        a_anchor = slug(a.name)  # this article's own H2
        anchor_by_id[a.id] = a_anchor
        all_anchors.add(a_anchor)
        body = f"> [content unavailable: {a.error}]" if a.error is not None else a.body_md
        all_anchors.update(slug(h) for h in _oracle_headings(body))
    return anchor_by_id, all_anchors


def test_cross_article_link_resolves_to_anchor() -> None:
    articles = [
        Article(
            id="554400000011111",
            name="M21-1, Part I, Subpart i - Intro",
            body_md=f"[see POA]({_LINK_BASE}554400000022222)\n",
        ),
        Article(id="554400000022222", name="M21-1, Part II - POA", body_md="POA body.\n"),
    ]
    out = assemble(articles, expected_count=2)
    assert "[see POA](#m21-1-part-ii---poa)" in out
    assert f"[see POA]({_LINK_BASE}554400000022222)" not in out


def test_no_candidate_links_byte_identical() -> None:
    body = "Plain text. [ext](https://www.ecfr.gov/current)\n"
    article = Article(id="1", name="General", body_md=body)
    out1 = assemble([article], expected_count=1)
    out2 = assemble([article], expected_count=1)
    assert out1 == out2
    assert "[ext](https://www.ecfr.gov/current)" in out1


def test_unknown_id_and_image_untouched() -> None:
    body = f"[old]({_LINK_BASE}999)\n\n![d](https://www.knowva.ebenefits.va.gov/img/cpkm/x.png)\n"
    out = assemble([Article(id="1", name="General", body_md=body)], expected_count=1)
    assert f"[old]({_LINK_BASE}999)" in out
    assert "![d](https://www.knowva.ebenefits.va.gov/img/cpkm/x.png)" in out


def test_heading_anchor_real_name_shape() -> None:
    assert heading_anchor("M21-1, Part II, Subpart iii - X") == "m21-1-part-ii-subpart-iii---x"
    assert heading_anchor("General") == "general"
    assert heading_anchor("VA's POA Rules") == "vas-poa-rules"


def test_self_link_resolves() -> None:
    body = f"[self]({_LINK_BASE}11)\n"
    out = assemble([Article(id="11", name="General", body_md=body)], expected_count=1)
    assert "[self](#general)" in out


def test_duplicate_names_get_distinct_anchors() -> None:
    articles = [
        Article(
            id="1",
            name="General",
            body_md=f"[to self]({_LINK_BASE}1) [to 2]({_LINK_BASE}2)\n",
        ),
        Article(id="2", name="General", body_md="Second general.\n"),
    ]
    out = assemble(articles, expected_count=2)
    assert "[to self](#general)" in out
    assert "[to 2](#general-1)" in out
    assert f"[to 2]({_LINK_BASE}2)" not in out


def test_slugger_dedup_sequence() -> None:
    from m21_crawl.assemble import Slugger

    s = Slugger()
    assert s.slug("A") == "a"
    assert s.slug("A") == "a-1"
    assert s.slug("A") == "a-2"
    assert s.slug("B") == "b"


def test_article_name_collides_with_earlier_body_heading() -> None:
    articles = [
        Article(
            id="1",
            name="X",
            body_md=f"### General\n\n[go to 2]({_LINK_BASE}2)\n",
        ),
        Article(id="2", name="General", body_md="Second general.\n"),
    ]
    out = assemble(articles, expected_count=2)
    # the earlier "### General" claimed the base slug in document order, so
    # article 2's own H2 "General" must resolve to its deduped slug
    assert "[go to 2](#general-1)" in out
    assert f"[go to 2]({_LINK_BASE}2)" not in out


def test_fenced_code_heading_not_counted() -> None:
    articles = [
        Article(
            id="1",
            name="X",
            body_md=f"Example:\n\n```\n# not a heading\n```\n\n[go to 2]({_LINK_BASE}2)\n",
        ),
        Article(id="2", name="General", body_md="Second general.\n"),
    ]
    out = assemble(articles, expected_count=2)
    # the fenced "# not a heading" is not a real heading, so the base slug
    # is still free for article 2's H2
    assert "[go to 2](#general)" in out
    assert "[go to 2](#general-1)" not in out


def test_article_named_table_of_contents() -> None:
    article = Article(
        id="1",
        name="Table of Contents",
        body_md=f"[self]({_LINK_BASE}1)\n",
    )
    out = assemble([article], expected_count=1)
    # the TOC H2 always exists, so the article's H2 must be suffixed
    assert "[self](#table-of-contents-1)" in out
    assert f"[self]({_LINK_BASE}1)" not in out


def test_error_article_body_headings_not_counted() -> None:
    articles = [
        Article(id="1", name="Broken", body_md="### General\n", error="lxml failed"),
        Article(id="2", name="General", body_md=f"[go to 2]({_LINK_BASE}2)\n"),
    ]
    out = assemble(articles, expected_count=2)
    # article 1's body is not emitted (placeholder), so "### General" never
    # claimed a slug and article 2's H2 keeps the base slug
    assert "[go to 2](#general)" in out
    assert "[go to 2](#general-1)" not in out


def test_property_article_anchors_match_document_order() -> None:
    """Case 12: every article link target equals the oracle's document-order
    slug for that article's own H2 (0-mismatch property)."""
    articles = [
        Article(
            id="1",
            name="General",
            body_md=f"### Rules\n\n[self]({_LINK_BASE}1)\n",
        ),
        Article(
            id="2",
            name="General",
            body_md=f"### Rules\n\n[self]({_LINK_BASE}2)\n",
        ),
        Article(
            id="3",
            name="Rules",
            body_md=f"### General\n\n[self]({_LINK_BASE}3)\n",
        ),
    ]
    out = assemble(articles, expected_count=3)
    anchor_by_id, _ = _oracle(articles)
    assert anchor_by_id == {"1": "general", "2": "general-1", "3": "rules-2"}
    for a in articles:
        assert f"[self](#{anchor_by_id[a.id]})" in out
        assert f"[self]({_LINK_BASE}{a.id})" not in out


def test_all_resolved_anchors_exist_as_headings() -> None:
    names = [
        "M21-1, Part I, Subpart i, Chapter 1 - A",
        "M21-1, Part II, Subpart iii - B",
        "M21-1, Part V - C",
    ]
    articles = [
        Article(
            id=str(i),
            name=name,
            body_md=f"[a]({_LINK_BASE}{i}) [b]({_LINK_BASE}{1 + (i - 1) % 3})\n",
        )
        for i, name in enumerate(names, start=1)
    ]
    out = assemble(articles, expected_count=3)
    _, all_anchors = _oracle(articles)
    anchors = set(re.findall(r"\]\(#([^)]+)\)", out))
    assert anchors <= all_anchors
