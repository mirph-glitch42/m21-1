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
  - deterministic: same input, byte-identical output.
"""

import pytest

from m21_crawl.assemble import Article, CompletenessError, assemble


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
