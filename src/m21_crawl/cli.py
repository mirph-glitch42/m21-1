"""cli: end-to-end crawl entry point (``python -m m21_crawl.cli``).

Wires the pipeline modules together:

    Client (anonymous session + bounded retries)
      → topic tree (``config.ENDPOINT_TOPIC`` for root ``config.ROOT_TOPIC_ID``)
      → ``tree.flatten_tree`` → ``tree.breadcrumb_paths``
      → per topic in pre-order that carries direct articles
        (``articleCount > 0`` — internal topics may carry articles too):
        ``articles.list_topic_articles`` → per article:
        skip names marked Historical/Rescinded
        (``articles.is_excluded_article`` — no fetch, no delay) →
        ``articles.get_article_content`` → ``mdconv.convert``
      → gate A: listed entries == the root's ``articleTotalCount``
        (truncation backstop; skipping never decrements the listed count)
      → ``assemble.assemble`` (gate B: assembled == listed − excluded)
      → deliverable file write.

Exit codes: ``0`` = every article converted; ``1`` = deliverable written but
one or more articles recorded as failed (placeholders rendered);
``2`` = completeness check failed (nothing written).
"""

import argparse
import os
import sys
import time
from collections.abc import Callable, Sequence
from typing import Any

from .articles import get_article_content, is_excluded_article, list_topic_articles
from .assemble import Article, CompletenessError, assemble
from .client import Client, HttpTransport
from .config import (
    BASE_URL,
    CRAWL_DELAY_SECONDS,
    DEFAULT_RETRIES,
    ENDPOINT_TOPIC,
    LANG,
    MANUAL_FILENAME,
    PORTAL_ID,
    ROOT_TOPIC_ID,
    USERTYPE,
)
from .mdconv import HtmlConversionError, convert
from .tree import breadcrumb_paths, flatten_tree

#: Default deliverable location (relative to the working directory).
DEFAULT_OUT = os.path.join("output", MANUAL_FILENAME)


def build_client(retries: int) -> Client:
    """Production client: `requests` transport + anonymous session.

    Tests monkeypatch this seam to inject a canned `Client` stand-in.
    """
    return Client(HttpTransport(), retries=retries)


def _topic_tree_wrappers(client: Client) -> list[dict[str, Any]]:
    """Fetch the portal topic tree and return its top-level wrapper list.

    Live shape (verified 2026-10-02): ``{"topicTree": [root_wrapper, ...]}``
    — the root manual topic is the first wrapper; there is no top-level
    ``topic`` key on the response.
    """
    data = client.get(
        ENDPOINT_TOPIC.format(topic_id=ROOT_TOPIC_ID),
        {
            "portalId": PORTAL_ID,
            "usertype": USERTYPE,
            "$level": "10",
            "$lang": LANG,
        },
    )
    if not isinstance(data, dict) or "topicTree" not in data:
        raise ValueError("topic-tree response has no 'topicTree' key")
    wrappers = data["topicTree"]
    if not isinstance(wrappers, list) or not wrappers:
        raise ValueError("topic-tree response 'topicTree' is missing or empty")
    return wrappers


def _article_entries(client: Client, topic_id: str) -> list[tuple[str, str]]:
    """Return ``(article_id, name)`` pairs for one topic, portal order."""
    entries = list_topic_articles(client, topic_id)
    pairs: list[tuple[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict) or "id" not in entry:
            raise ValueError(f"article entry in topic {topic_id!r} is missing 'id'")
        article_id = str(entry["id"])
        if "name" not in entry:
            raise ValueError(f"article {article_id} in topic {topic_id!r} is missing 'name'")
        pairs.append((article_id, str(entry["name"])))
    return pairs


def crawl_manual(
    client: Client,
    *,
    delay: float = CRAWL_DELAY_SECONDS,
    sleep: Callable[[float], None] | None = None,
) -> tuple[str, int]:
    """Crawl the current manual; return ``(markdown, failure_count)``.

    Articles marked Historical/Rescinded (see
    ``articles.is_excluded_article``) are skipped: no content request, no
    politeness delay. Completeness is checked with two gates (see
    ``algorithms/historical-rescinded-exclusion.md`` §3):

    - gate A (truncation): the LISTED entries across all topics must equal
      the root topic's ``articleTotalCount``; a mismatch raises
      ``CompletenessError``. Skipping never decrements the listed count, so
      a silently truncated list still fails loudly;
    - gate B (fetch/assemble): the assembled count must equal listed −
      excluded; ``assemble`` raises ``CompletenessError`` on a mismatch;

    - articles are fetched in portal order (tree pre-order → listing order);
      every topic with direct articles (``articleCount > 0``) is fetched —
      internal topics may carry articles as well as children — and topics
      without direct articles trigger no article-list request; nothing is
      ever re-sorted;
    - ``sleep(delay)`` runs before every article content fetch except the
      first (politeness) — marked articles are never fetched, so they add no
      delay;
    - an article whose HTML cannot be converted is recorded as
      ``Article.error`` (rendered as a placeholder by ``assemble``) and
      counted in the returned failure count; it does not abort the crawl.

    ``sleep`` defaults to ``time.sleep``, resolved at call time so tests can
    monkeypatch ``time.sleep``.
    """
    sleeper: Callable[[float], None] = time.sleep if sleep is None else sleep

    nodes = flatten_tree(_topic_tree_wrappers(client))
    root = nodes[0]
    if root.id != ROOT_TOPIC_ID:
        raise ValueError(f"topic tree root id {root.id!r} != expected root {ROOT_TOPIC_ID!r}")
    expected = root.article_total_count
    crumbs = breadcrumb_paths(nodes)

    articles: list[Article] = []
    failures = 0
    listed = 0
    excluded = 0
    first = True
    for node in nodes:
        if node.article_count == 0:
            continue  # no direct articles (e.g. the root) — no list request
        for article_id, name in _article_entries(client, node.id):
            listed += 1
            if is_excluded_article(name):
                # Marked Historical/Rescinded: counted for gate A but never
                # fetched — no content request, no politeness delay.
                excluded += 1
                continue
            if not first:
                sleeper(delay)
            first = False
            try:
                content = get_article_content(client, article_id)
                body = convert(content, base_url=BASE_URL, article_id=article_id)
            except HtmlConversionError as exc:
                failures += 1
                # The breadcrumb (position in the manual) is still valid, so it
                # is kept; only the body is replaced by the placeholder.
                articles.append(
                    Article(
                        id=article_id,
                        name=name,
                        breadcrumb=crumbs.get(node.id, ""),
                        error=str(exc),
                    )
                )
                continue
            articles.append(
                Article(
                    id=article_id,
                    name=name,
                    body_md=body,
                    breadcrumb=crumbs.get(node.id, ""),
                )
            )

    # Gate A (truncation): the portal's complete list must have been seen.
    # Skipping marked articles never decrements `listed`, so this stays loud.
    if listed != expected:
        raise CompletenessError(expected, listed)
    # Gate B (fetch/assemble): every retained article was converted or
    # placeholdered; `assemble` raises CompletenessError on a mismatch.
    return assemble(articles, expected_count=listed - excluded), failures


def main(argv: Sequence[str] | None = None) -> int:
    """Parse args, run the crawl, write the deliverable; return the exit code."""
    parser = argparse.ArgumentParser(
        prog="m21_crawl",
        description="Crawl the complete M21-1 manual from the Knowva eBenefits portal.",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help=f"output Markdown path (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=CRAWL_DELAY_SECONDS,
        help="politeness delay between article fetches in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="max retries per request for 429/5xx/transport errors (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    client = build_client(args.retries)
    try:
        markdown, failures = crawl_manual(client, delay=args.delay)
    except CompletenessError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(markdown)

    if failures:
        print(f"warning: {failures} article(s) could not be converted", file=sys.stderr)
    print(f"wrote {args.out} ({len(markdown.encode('utf-8'))} bytes, {failures} failed article(s))")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
