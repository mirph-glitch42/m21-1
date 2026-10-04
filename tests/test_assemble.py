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
    heading; unknown ids, images, and external links stay verbatim
    (algorithms/internal-link-resolution.md).
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


def test_duplicate_names_share_first_anchor() -> None:
    articles = [
        Article(
            id="1",
            name="General",
            body_md=f"[to 2]({_LINK_BASE}2)\n",
        ),
        Article(id="2", name="General", body_md="Second general.\n"),
    ]
    out = assemble(articles, expected_count=2)
    assert "[to 2](#general)" in out


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
    headings = {
        heading_anchor(line[3:].strip()) for line in out.splitlines() if line.startswith("## ")
    }
    anchors = set(re.findall(r"\]\(#([^)]+)\)", out))
    assert anchors <= headings
