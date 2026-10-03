"""articles: topic article listing + single-article content fetch.

Thin, testable layer over `Client` (which owns session, retries, transport).
Portal contract (verified live 2026-10-02):

  - `GET /ws/v11/ss/article?portalId=...&usertype=...&topicId=...&$lang=...`
    → `{"article": [ {id, name, ...}, ... ]}` in portal order.
  - `GET /ws/v11/ss/article/{articleId}?portalId=...&usertype=...&$lang=...`
    → `{"article": [ {id, ..., content: "<html fragment>"} ]}`.

Neither function re-sorts: callers rely on the API's order.
"""

from typing import Any

from .client import Client
from .config import ENDPOINT_ARTICLE, ENDPOINT_ARTICLE_LIST, LANG, PORTAL_ID, USERTYPE


def list_topic_articles(client: Client, topic_id: str) -> list[dict[str, Any]]:
    """Return the portal-ordered article entries for one topic.

    Raises ValueError when the response lacks the `article` array or it is
    not a list — loud failure beats silently emitting no articles.
    """
    data = client.get(
        ENDPOINT_ARTICLE_LIST,
        {
            "portalId": PORTAL_ID,
            "usertype": USERTYPE,
            "topicId": topic_id,
            "$lang": LANG,
        },
    )
    if not isinstance(data, dict) or "article" not in data:
        raise ValueError(f"topic {topic_id} article-list response has no 'article' key")
    articles = data["article"]
    if not isinstance(articles, list):
        raise ValueError(f"topic {topic_id} article-list response 'article' is not a list")
    return articles


def get_article_content(client: Client, article_id: str) -> str:
    """Return the raw HTML content fragment of one article.

    Raises ValueError when the response has no entries or the entry has no
    `content` field.
    """
    data = client.get(
        ENDPOINT_ARTICLE.format(article_id=article_id),
        {
            "portalId": PORTAL_ID,
            "usertype": USERTYPE,
            "$lang": LANG,
        },
    )
    if not isinstance(data, dict) or not data.get("article"):
        raise ValueError(f"article {article_id} response has no entries")
    entry = data["article"][0]
    content = entry.get("content") if isinstance(entry, dict) else None
    if content is None:
        raise ValueError(f"article {article_id} has no content")
    return content
