"""articles: topic article listing + single-article content fetch (TDD)."""

from m21_crawl import config
from m21_crawl.articles import get_article_content, list_topic_articles


class FakeClient:
    """Records get() calls and returns a canned JSON payload."""

    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, path: str, params: dict[str, str]) -> object:
        self.calls.append((path, dict(params)))
        return self.payload


def test_list_topic_articles_request_shape_and_order() -> None:
    a1 = {"id": 111, "name": "First"}
    a2 = {"id": 222, "name": "Second"}
    fake = FakeClient({"article": [a1, a2]})
    assert list_topic_articles(fake, "554400000004050") == [a1, a2]
    path, params = fake.calls[0]
    assert path == config.ENDPOINT_ARTICLE_LIST
    assert params == {
        "portalId": config.PORTAL_ID,
        "usertype": config.USERTYPE,
        "topicId": "554400000004050",
        "$lang": config.LANG,
    }


def test_list_topic_articles_empty_list() -> None:
    fake = FakeClient({"article": []})
    assert list_topic_articles(fake, "1") == []


def test_list_topic_articles_missing_key_raises() -> None:
    fake = FakeClient({})
    try:
        list_topic_articles(fake, "1")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_list_topic_articles_non_list_raises() -> None:
    fake = FakeClient({"article": "nope"})
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
