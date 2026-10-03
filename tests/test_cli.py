"""cli: end-to-end crawl wiring + CLI entry point (TDD).

`FakeClient` dispatches canned payloads by request path, mirroring the
portal's three routes (topic tree, article list, article content) so the
whole pipeline runs without a network. It is strict: an article-list
request for a topic it has no articles for is an AssertionError — this pins
that topics with no direct articles (e.g. the root) are never queried.
"""

import re

import pytest

from m21_crawl import cli, config
from m21_crawl.assemble import CompletenessError
from m21_crawl.mdconv import HtmlConversionError
from m21_crawl.mdconv import convert as real_convert

ROOT = config.ROOT_TOPIC_ID

# Fixture portal: the root (no direct articles) has two parts. Part 1 is an
# INTERNAL topic: it carries two direct articles AND a child chapter that
# carries one article — mirroring the live portal, where 71 internal topics
# hold direct articles. Portal order is pre-order: Part 1's own articles
# come before its chapter's articles.
ARTICLES_T100 = [{"id": 111, "name": "Article One"}, {"id": 112, "name": "Article Two"}]
ARTICLES_T101 = [{"id": 113, "name": "Chapter Article"}]
ARTICLES_T200 = [{"id": 222, "name": "Part 2 Article"}]
CONTENT = {
    "111": "<p>First body.</p>",
    "112": "<p>Second body.</p>",
    "113": "<p>Chapter body.</p>",
    "222": "<p>Third body.</p>",
}

EXPECTED_MD = """\
# M21-1 Adjudication Procedures Manual

## Table of Contents

1. Article One
2. Article Two
3. Chapter Article
4. Part 2 Article

## Article One

> Part 1

First body.

## Article Two

> Part 1

Second body.

## Chapter Article

> Part 1 › Chapter 1

Chapter body.

## Part 2 Article

> Part 2

Third body.
"""

EXPECTED_MD_ART112_FAILED = EXPECTED_MD.replace(
    "## Article Two\n\n> Part 1\n\nSecond body.\n",
    "## Article Two\n\n> Part 1\n\n"
    "> [content unavailable: HTML conversion failed for article '112': synthetic]\n",
)


def _wrapper(
    tid: int,
    name: str,
    parent: int | None,
    article_count: int,
    total: int,
    children: list | None = None,
) -> dict:
    topic: dict = {
        "id": tid,
        "name": name,
        "articleCount": article_count,
        "articleTotalCount": total,
    }
    if parent is not None:
        topic["parentTopicId"] = parent
    wrapper = {"topic": topic}
    if children is not None:
        wrapper["topicTree"] = children
    return wrapper


def make_tree_payload(total: int) -> dict:
    """Fixture tree, shaped exactly like the live API response."""
    return {
        "topicTree": [
            _wrapper(
                int(ROOT),
                "M21-1 Adjudication Procedures Manual",
                None,
                0,
                total,
                [
                    _wrapper(
                        100,
                        "Part 1",
                        int(ROOT),
                        2,
                        3,
                        [_wrapper(101, "Chapter 1", 100, 1, 1)],
                    ),
                    _wrapper(200, "Part 2", int(ROOT), 1, 1),
                ],
            )
        ],
        "callInfo": {},
    }


class FakeClient:
    """Canned responses dispatched by request path (the three portal routes)."""

    def __init__(
        self,
        tree: object,
        articles_by_topic: dict[str, list] | None = None,
    ) -> None:
        self.tree = tree
        self.articles_by_topic = (
            articles_by_topic
            if articles_by_topic is not None
            else {"100": ARTICLES_T100, "101": ARTICLES_T101, "200": ARTICLES_T200}
        )
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, path: str, params: dict[str, str]) -> object:
        self.calls.append((path, dict(params)))
        if path == config.ENDPOINT_TOPIC.format(topic_id=config.ROOT_TOPIC_ID):
            return self.tree
        if path == config.ENDPOINT_ARTICLE_LIST:
            topic_id = params["topicId"]
            if topic_id not in self.articles_by_topic:
                raise AssertionError(f"unexpected article-list request for topic {topic_id}")
            entries = self.articles_by_topic[topic_id]
            # Fixture topics fit one page (the portal caps lists at 10 per
            # response and reports the total via `pagingInfo` — see
            # algorithms/topic-article-paging.md).
            return {
                "article": entries,
                "pagingInfo": {
                    "count": len(entries),
                    "pageNumber": 1,
                    "rangeStart": 0,
                    "rangeSize": 10,
                    "maxRange": len(entries),
                },
            }
        match = re.fullmatch(r"/ws/v11/ss/article/(\d+)", path)
        if match:
            return {"article": [{"id": match.group(1), "content": CONTENT[match.group(1)]}]}
        raise AssertionError(f"unexpected request path: {path}")


def test_crawl_manual_byte_exact() -> None:
    fake = FakeClient(make_tree_payload(4))
    markdown, failures = cli.crawl_manual(fake)
    assert failures == 0
    assert markdown == EXPECTED_MD


def test_tree_request_shape() -> None:
    fake = FakeClient(make_tree_payload(4))
    cli.crawl_manual(fake)
    path, params = fake.calls[0]
    assert path == config.ENDPOINT_TOPIC.format(topic_id=config.ROOT_TOPIC_ID)
    assert params == {
        "portalId": config.PORTAL_ID,
        "usertype": config.USERTYPE,
        "$level": "10",
        "$lang": config.LANG,
    }


def test_article_requests_follow_portal_order() -> None:
    fake = FakeClient(make_tree_payload(4))
    cli.crawl_manual(fake)
    # Pre-order: internal topic 100 is queried (it carries articles), then
    # its child 101, then sibling leaf 200. The root (articleCount=0) is
    # never queried — the strict FakeClient would raise otherwise.
    list_calls = [q["topicId"] for p, q in fake.calls if p == config.ENDPOINT_ARTICLE_LIST]
    assert list_calls == ["100", "101", "200"]
    content_paths = [p for p, _ in fake.calls if p.startswith("/ws/v11/ss/article/")]
    assert content_paths == [
        config.ENDPOINT_ARTICLE.format(article_id="111"),
        config.ENDPOINT_ARTICLE.format(article_id="112"),
        config.ENDPOINT_ARTICLE.format(article_id="113"),
        config.ENDPOINT_ARTICLE.format(article_id="222"),
    ]


def test_sleep_between_article_fetches() -> None:
    fake = FakeClient(make_tree_payload(4))
    sleeps: list[float] = []
    cli.crawl_manual(fake, delay=2.5, sleep=sleeps.append)
    # 4 articles -> a delay before every fetch except the first.
    assert sleeps == [2.5, 2.5, 2.5]


def make_inconsistent_tree() -> dict:
    """Server-side inconsistency the completeness gate exists to catch.

    The root advertises ``articleTotalCount = 4``, but its parts carry only
    3 direct articles: topic 200 declares ``articleCount = 0``. A portal in
    this state would serve 3 articles for a 4-article manual.
    """
    tree = make_tree_payload(4)
    topic200 = tree["topicTree"][0]["topicTree"][1]["topic"]
    topic200["articleCount"] = 0
    topic200["articleTotalCount"] = 0
    return tree


def test_completeness_error_on_count_mismatch() -> None:
    fake = FakeClient(make_inconsistent_tree())
    with pytest.raises(CompletenessError) as excinfo:
        cli.crawl_manual(fake)
    assert excinfo.value.expected == 4
    assert excinfo.value.actual == 3


def _fail_only_article(article_id: str):
    """A convert stand-in that fails only for one article, passes the rest through."""

    def boom(html: object, **kwargs: object) -> str:
        if str(kwargs.get("article_id", "")) == article_id:
            raise HtmlConversionError(article_id, ValueError("synthetic"))
        return real_convert(html, **kwargs)

    return boom


def test_conversion_failure_yields_placeholder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "convert", _fail_only_article("112"))
    fake = FakeClient(make_tree_payload(4))
    markdown, failures = cli.crawl_manual(fake)
    assert failures == 1
    assert markdown == EXPECTED_MD_ART112_FAILED


def test_root_id_mismatch_raises() -> None:
    tree = make_tree_payload(4)
    tree["topicTree"][0]["topic"]["id"] = 999
    fake = FakeClient(tree)
    with pytest.raises(ValueError):
        cli.crawl_manual(fake)


def test_missing_topic_tree_raises() -> None:
    fake = FakeClient({"callInfo": {}})
    with pytest.raises(ValueError):
        cli.crawl_manual(fake)


def test_empty_topic_tree_raises() -> None:
    fake = FakeClient({"topicTree": []})
    with pytest.raises(ValueError):
        cli.crawl_manual(fake)


def test_main_writes_file_and_returns_zero(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = tmp_path / "sub" / "manual.md"
    monkeypatch.setattr(
        cli,
        "build_client",
        lambda retries: FakeClient(make_tree_payload(4)),
    )
    sleeps: list[float] = []
    monkeypatch.setattr(cli.time, "sleep", sleeps.append)
    rc = cli.main(["--out", str(out)])
    assert rc == 0
    assert out.read_text(encoding="utf-8") == EXPECTED_MD
    # 4 articles -> default delay (0.1) before the 2nd, 3rd and 4th fetch.
    assert sleeps == [0.1, 0.1, 0.1]


def test_main_passes_retries_to_client_factory(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def factory(retries: int) -> FakeClient:
        seen["retries"] = retries
        return FakeClient(make_tree_payload(4))

    monkeypatch.setattr(cli, "build_client", factory)
    rc = cli.main(["--out", str(tmp_path / "manual.md"), "--retries", "7"])
    assert rc == 0
    assert seen["retries"] == 7


def test_main_returns_one_when_articles_failed(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "convert", _fail_only_article("112"))
    monkeypatch.setattr(
        cli,
        "build_client",
        lambda retries: FakeClient(make_tree_payload(4)),
    )
    out = tmp_path / "manual.md"
    rc = cli.main(["--out", str(out)])
    assert rc == 1
    # The deliverable is still written, with the placeholder for the failed article.
    assert out.read_text(encoding="utf-8") == EXPECTED_MD_ART112_FAILED


def test_main_returns_two_on_completeness_failure(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "build_client",
        lambda retries: FakeClient(make_inconsistent_tree()),
    )
    out = tmp_path / "manual.md"
    rc = cli.main(["--out", str(out)])
    assert rc == 2
    assert "expected 4" in capsys.readouterr().err
    assert not out.exists()


def test_default_out_under_output(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "build_client", lambda retries: FakeClient(make_tree_payload(4)))
    rc = cli.main([])
    assert rc == 0
    out = tmp_path / "output" / config.MANUAL_FILENAME
    assert out.read_text(encoding="utf-8") == EXPECTED_MD
