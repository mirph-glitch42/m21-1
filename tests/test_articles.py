"""articles: topic article listing (paged) + single-article content fetch (TDD).

Paging contract (see `algorithms/topic-article-paging.md`): the portal caps
the article list at 10 entries per response and reports the total via
`pagingInfo`; the client pages with `$rangestart`/`$rangesize` until
`rangeStart + count >= maxRange`. A response without `pagingInfo` is a
contract violation and must fail loudly (the silent one-page behavior is
exactly the defect that dropped 45 of 785 articles).
"""

from m21_crawl import config
from m21_crawl.articles import (
    get_article_content,
    is_excluded_article,
    list_topic_articles,
)


def paging_info(count: int, max_range: int, range_start: int = 0) -> dict:
    """Synthetic `pagingInfo` shaped exactly like the live portal's."""
    return {
        "count": count,
        "pageNumber": 1 + range_start // 10,
        "rangeStart": range_start,
        "rangeSize": 10,
        "maxRange": max_range,
    }


class PagedFakeClient:
    """Returns one canned page per `get()` call, in order; records requests.

    Raises AssertionError if the code requests more pages than were queued —
    an observable infinite-loop guard.
    """

    def __init__(self, pages: list[dict]) -> None:
        self.pages = pages
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, path: str, params: dict[str, str]) -> object:
        self.calls.append((path, dict(params)))
        if not self.pages:
            raise AssertionError("unexpected extra article-list request")
        return self.pages.pop(0)


class FakeClient:
    """Records get() calls and returns a single canned JSON payload."""

    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, path: str, params: dict[str, str]) -> object:
        self.calls.append((path, dict(params)))
        return self.payload


def test_list_topic_articles_request_shape_and_order() -> None:
    a1 = {"id": 111, "name": "First"}
    a2 = {"id": 222, "name": "Second"}
    fake = FakeClient({"article": [a1, a2], "pagingInfo": paging_info(2, 2)})
    assert list_topic_articles(fake, "554400000004050") == [a1, a2]
    assert len(fake.calls) == 1
    path, params = fake.calls[0]
    assert path == config.ENDPOINT_ARTICLE_LIST
    assert params == {
        "portalId": config.PORTAL_ID,
        "usertype": config.USERTYPE,
        "topicId": "554400000004050",
        "$lang": config.LANG,
        "$rangestart": "0",
        "$rangesize": "10",
    }


def test_list_topic_articles_empty_list() -> None:
    fake = FakeClient({"article": [], "pagingInfo": paging_info(0, 0)})
    assert list_topic_articles(fake, "1") == []
    assert len(fake.calls) == 1


def test_list_topic_articles_pages_until_exhausted() -> None:
    """The fixed bug: 18-entry topic = page of 10 + page of 8, portal order."""
    page1 = [{"id": i, "name": f"A{i:02d}"} for i in range(1, 11)]
    page2 = [{"id": i, "name": f"A{i:02d}"} for i in range(11, 19)]
    fake = PagedFakeClient(
        [
            {"article": page1, "pagingInfo": paging_info(10, 18, range_start=0)},
            {"article": page2, "pagingInfo": paging_info(8, 18, range_start=10)},
        ]
    )
    assert list_topic_articles(fake, "554400000015005") == page1 + page2
    assert [c[1]["$rangestart"] for c in fake.calls] == ["0", "10"]
    assert [c[1]["$rangesize"] for c in fake.calls] == ["10", "10"]


def test_list_topic_articles_stops_on_empty_page() -> None:
    """Server inconsistency: empty page before maxRange — no infinite loop."""
    page1 = [{"id": i} for i in range(10)]
    fake = PagedFakeClient(
        [
            {"article": page1, "pagingInfo": paging_info(10, 18, range_start=0)},
            {"article": [], "pagingInfo": paging_info(0, 18, range_start=10)},
        ]
    )
    assert list_topic_articles(fake, "554400000015005") == page1
    assert len(fake.calls) == 2  # exactly: the empty page ends the loop


def test_list_topic_articles_steps_by_returned_count() -> None:
    """Server caps the page at 5: step must be the returned count, not 10."""
    p1 = [{"id": i} for i in range(1, 6)]
    p2 = [{"id": i} for i in range(6, 11)]
    p3 = [{"id": i} for i in range(11, 13)]
    fake = PagedFakeClient(
        [
            {"article": p1, "pagingInfo": {"count": 5, "rangeStart": 0, "maxRange": 12}},
            {"article": p2, "pagingInfo": {"count": 5, "rangeStart": 5, "maxRange": 12}},
            {"article": p3, "pagingInfo": {"count": 2, "rangeStart": 10, "maxRange": 12}},
        ]
    )
    assert list_topic_articles(fake, "1") == p1 + p2 + p3
    assert [c[1]["$rangestart"] for c in fake.calls] == ["0", "5", "10"]


def test_list_topic_articles_missing_key_raises() -> None:
    fake = FakeClient({})
    try:
        list_topic_articles(fake, "1")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_list_topic_articles_non_list_raises() -> None:
    fake = FakeClient({"article": "nope", "pagingInfo": paging_info(1, 1)})
    try:
        list_topic_articles(fake, "1")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_list_topic_articles_missing_paginginfo_raises() -> None:
    """No pagingInfo = contract violation; silent one-page is the old bug."""
    fake = FakeClient({"article": [{"id": 1}]})
    try:
        list_topic_articles(fake, "1")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_list_topic_articles_non_int_count_raises() -> None:
    fake = FakeClient({"article": [{"id": 1}], "pagingInfo": {"count": "10", "maxRange": 18}})
    try:
        list_topic_articles(fake, "1")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_get_article_content_request_shape() -> None:
    fake = FakeClient({"article": [{"id": 999, "content": "<p>hi</p>"}]})
    assert get_article_content(fake, "554400000181468") == "<p>hi</p>"
    path, params = fake.calls[0]
    assert path == config.ENDPOINT_ARTICLE.format(article_id="554400000181468")
    assert params == {
        "portalId": config.PORTAL_ID,
        "usertype": config.USERTYPE,
        "$lang": config.LANG,
    }


def test_get_article_content_no_entries_raises() -> None:
    fake = FakeClient({"article": []})
    try:
        get_article_content(fake, "1")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_get_article_content_missing_content_raises() -> None:
    fake = FakeClient({"article": [{"id": 1}]})
    try:
        get_article_content(fake, "1")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_is_excluded_article_markers() -> None:
    """Every live marker shape (full 785-entry scan, 2026-10-03) is excluded.

    See `algorithms/historical-rescinded-exclusion.md` §2.1: 290 ` - Historical`,
    48 ` - Rescinded`, and 5 with irregular dash spacing (3 ` -  Historical`,
    2 `K- Historical`) — all must match despite the spacing.
    """
    names = [
        "M21-1, Part I, Chapter 1, Section A - Historical",
        "M21-1, Part I, Chapter 2, Section E - Rescinded",
        "M21-1, Part I, Chapter 4 -  Historical",  # two spaces (live)
        # no space after the dash (live):
        "M21-1, Part III, Subpart iv, Chapter 4, Section K- Historical",
        "M21-1, Part III, Subpart iii, Chapter 1, Section E -  Historical",  # two spaces (live)
        "Historical",  # the marker is the entire name
        "Rescinded",
    ]
    for name in names:
        assert is_excluded_article(name), name


def test_is_excluded_article_retained_names() -> None:
    """The marker only counts as a whole word at the END of the name.

    Three live *current* articles contain 'Historical' mid-name — a 'contains'
    rule would wrongly drop them. Case-sensitive: the portal's marking is
    title-case; no live counterexample exists (pinned here).
    """
    names = [
        # live current articles (the word is not at the end):
        "M21-1, Part II, Subpart iii, Chapter 2, Section H - Historical "
        "Guidance on Formal Applications and Informal Claims Received "
        "Prior to March 24, 2015",
        "M21-1, Part V, Subpart ii, Chapter 4, Section B - Historical "
        "Guidance on the Assignment of Effective Dates",
        "M21-1, Part X, Subpart ii, Chapter 6, Section H - Historical "
        "Information on Estate Limitations",
        # different word / case / plain names:
        "M21-1, Part I, Chapter 1, Section A - Historically",
        "M21-1, Part I, Chapter 1, Section A - historical",
        "M21-1, Part I, Chapter 1, Section A",
    ]
    for name in names:
        assert not is_excluded_article(name), name
