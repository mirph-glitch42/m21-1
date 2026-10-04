"""articles: topic article listing (paged) + single-article content fetch.

Thin, testable layer over `Client` (which owns session, retries, transport).
Portal contract (verified live 2026-10-02; paging verified 2026-10-03):

  - `GET /ws/v11/ss/article?portalId=...&usertype=...&topicId=...&$lang=...`
    → `{"article": [ {id, name, ...}, ... ],
              "pagingInfo": {count, pageNumber, rangeStart, rangeSize,
                             maxRange}}` in portal order.
    The response is CAPPED at 10 entries with no error field (silent);
    the complete list is fetched by paging with `$rangestart` (0-based
    offset) and `$rangesize` (slice length) — the same RANGE mode the
    portal's own Angular UI uses. See
    `algorithms/topic-article-paging.md` for the loop, its termination
    argument, and the loud-failure contract.
  - `GET /ws/v11/ss/article/{articleId}?portalId=...&usertype=...&$lang=...`
    → `{"article": [ {id, ..., content: "<html fragment>"} ]}`.

Neither function re-sorts: callers rely on the API's order.
"""

import re
from typing import Any

from .client import Client
from .config import ENDPOINT_ARTICLE, ENDPOINT_ARTICLE_LIST, LANG, PORTAL_ID, USERTYPE

#: Slice length for paged article-list requests. The server's own default
#: `rangeSize` (every observed response reports `rangeSize: 10`), so it is
#: guaranteed to be honored; a larger value would risk an unverified cap.
#: Cost of the small page: ≤ 1 extra call for a topic with > 10 articles.
PAGE_SIZE = 10

_EXCLUDED_RE = re.compile(r"(?<![A-Za-z])(?:Historical|Rescinded)$")


def is_excluded_article(name: str) -> bool:
    """Return True if a portal article name is marked Historical or Rescinded.

    The marker is a name suffix only — the portal carries no structural field
    to filter on (verified live: all 785 entries are structurally identical).
    See `algorithms/historical-rescinded-exclusion.md` §2.1. Match the whole
    word `Historical` or `Rescinded` (case-sensitive, as the portal marks
    them), preceded by a non-letter, at the very end of the name. A mid-name
    occurrence (e.g. "…Historical Guidance on …") is NOT a marker and is kept.
    """
    return _EXCLUDED_RE.search(name) is not None


def _paging_total(data: dict[str, Any], topic_id: str) -> tuple[int, int]:
    """Return `(count, maxRange)` from a page response.

    Strict by contract (algorithms/topic-article-paging.md §5.2): the
    portal always sends `pagingInfo` with integer `count`/`maxRange`; a
    malformed response raises ValueError instead of degrading silently to
    one page (that silent single-page behavior is the defect this module
    exists to prevent).
    """
    pi = data.get("pagingInfo")
    if not isinstance(pi, dict):
        raise ValueError(f"topic {topic_id} article-list response has no 'pagingInfo'")
    count = pi.get("count")
    max_range = pi.get("maxRange")
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError(f"topic {topic_id} pagingInfo 'count' is not an int")
    if not isinstance(max_range, int) or isinstance(max_range, bool):
        raise ValueError(f"topic {topic_id} pagingInfo 'maxRange' is not an int")
    return count, max_range


def list_topic_articles(client: Client, topic_id: str) -> list[dict[str, Any]]:
    """Return the complete, portal-ordered article entries for one topic.

    Pages through the portal's capped list (`PAGE_SIZE` per request) until
    `rangeStart + count >= maxRange` (or an empty page). Raises ValueError
    when a response lacks the `article` array, it is not a list, or
    `pagingInfo` is malformed — loud failure beats silently emitting a
    truncated list.
    """
    out: list[dict[str, Any]] = []
    range_start = 0
    while True:
        data = client.get(
            ENDPOINT_ARTICLE_LIST,
            {
                "portalId": PORTAL_ID,
                "usertype": USERTYPE,
                "topicId": topic_id,
                "$lang": LANG,
                "$rangestart": str(range_start),
                "$rangesize": str(PAGE_SIZE),
            },
        )
        if not isinstance(data, dict) or "article" not in data:
            raise ValueError(f"topic {topic_id} article-list response has no 'article' key")
        articles = data["article"]
        if not isinstance(articles, list):
            raise ValueError(f"topic {topic_id} article-list response 'article' is not a list")
        count, max_range = _paging_total(data, topic_id)
        out.extend(articles)  # append in request order — portal order preserved
        if count == 0:
            break  # empty page: nothing more to fetch
        if range_start + count >= max_range:
            break  # final slice reached
        range_start += count  # step by the RETURNED length: a smaller honored
        # slice must never cause entries to be skipped
    return out


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
