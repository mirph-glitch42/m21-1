"""tree: pre-order flatten of the portal topic tree, with dedupe.

Implements the algorithm specified in `algorithms/manual-tree-crawl.md`:
iterative depth-first pre-order traversal over the portal wrapper JSON
(`{"topic": {...}, "topicTree": [...]}`) using an explicit stack and a
visited set, so that:

  - every topic id is emitted exactly once (first pre-order occurrence wins);
  - sibling order is the API's document order (never re-sorted);
  - cyclic or self-referencing input terminates;
  - malformed input (missing `topic`/`id`/`name`, non-list `topicTree`)
    raises `ValueError` — loud failure beats silent loss.

The input structure is never mutated.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TopicNode:
    """One topic in pre-order (field meanings per the algorithm doc, 2.1)."""

    id: str  # canonical string form of the JSON integer id
    name: str  # verbatim API name (no trimming)
    depth: int  # 0 = top-level wrapper
    is_leaf: bool  # len(wrapper["topicTree"]) == 0 (structural, not count-based)
    article_count: int  # topic["articleCount"] (direct articles)
    article_total_count: int  # topic["articleTotalCount"] (incl. descendants)
    parent_id: str | None  # topic["parentTopicId"] as str, or None


def _wrapper_topic(wrapper: object, where: str) -> dict:
    """Return `wrapper["topic"]`, raising ValueError for malformed wrappers."""
    if not isinstance(wrapper, dict) or "topic" not in wrapper:
        raise ValueError(f"malformed topic wrapper at {where}: missing 'topic' key")
    topic = wrapper["topic"]
    if not isinstance(topic, dict):
        raise ValueError(f"malformed topic wrapper at {where}: 'topic' is not an object")
    return topic


def _wrapper_children(wrapper: dict, where: str) -> list:
    """Return `wrapper["topicTree"]` (absent key = empty list; strict on type)."""
    if "topicTree" not in wrapper:
        return []
    children = wrapper["topicTree"]
    if not isinstance(children, list):
        raise ValueError(f"malformed topic wrapper at {where}: 'topicTree' is not a list")
    return children


def _topic_id(topic: dict, where: str) -> str:
    """Extract the string topic id, raising ValueError when missing."""
    if "id" not in topic:
        raise ValueError(f"malformed topic at {where}: missing 'id'")
    return str(topic["id"])


def flatten_tree(wrappers: list[dict]) -> list[TopicNode]:
    """Flatten portal wrapper JSON into a pre-order list of TopicNode.

    Pre: `wrappers` is a list of wrapper objects (possibly empty).
    Post: output satisfies contracts 1-5 of the algorithm doc (pre-order,
    document order, first-occurrence-wins dedupe, termination, totality).
    """
    result: list[TopicNode] = []
    visited: set[str] = set()
    # Push top-level wrappers reversed so wrappers[0] pops first (doc 2.3 I3).
    stack: list[tuple[dict, int]] = [(w, 0) for w in reversed(wrappers)]

    while stack:
        wrapper, depth = stack.pop()
        where = f"depth {depth}"
        topic = _wrapper_topic(wrapper, where)
        node_id = _topic_id(topic, where)

        if node_id in visited:
            continue  # already emitted earlier in pre-order (doc 2.3 I2)
        visited.add(node_id)

        if "name" not in topic:
            raise ValueError(f"malformed topic at {where} (id={node_id!r}): missing 'name'")

        children = _wrapper_children(wrapper, where)
        result.append(
            TopicNode(
                id=node_id,
                name=topic["name"],
                depth=depth,
                is_leaf=len(children) == 0,
                article_count=topic.get("articleCount", 0),
                article_total_count=topic.get("articleTotalCount", 0),
                parent_id=(
                    str(topic["parentTopicId"]) if topic.get("parentTopicId") is not None else None
                ),
            )
        )

        # Push children reversed: first child in document order ends up on top
        # of the LIFO stack (doc 2.3 I3); skip already-emitted ids (I2/I4).
        for child in reversed(children):
            child_id = _topic_id(
                _wrapper_topic(child, f"depth {depth + 1} (child)"), f"depth {depth + 1} (child)"
            )
            if child_id not in visited:
                stack.append((child, depth + 1))

    return result


def leaf_topics(nodes: list[TopicNode]) -> list[TopicNode]:
    """Return the leaf nodes (structural leaf-ness) in the same order."""
    return [node for node in nodes if node.is_leaf]


def breadcrumb_paths(nodes: list[TopicNode]) -> dict[str, str]:
    """Map each topic id to its ancestor chain joined by ``\u203a``.

    The chain walks ``parent_id`` links upward while ``depth > 0`` (the
    depth-0 root — the manual title itself — is excluded) and includes the
    topic's own name. Order is root-to-topic. A missing parent id or a
    parent cycle stops the walk early (loud nowhere, but never hangs).
    """
    by_id: dict[str, TopicNode] = {node.id: node for node in nodes}
    paths: dict[str, str] = {}
    for node in nodes:
        chain: list[str] = []
        seen: set[str] = set()
        current: TopicNode | None = node
        while current is not None and current.depth > 0 and current.id not in seen:
            seen.add(current.id)
            chain.append(current.name)
            current = by_id.get(current.parent_id) if current.parent_id is not None else None
        paths[node.id] = " \u203a ".join(reversed(chain))
    return paths
