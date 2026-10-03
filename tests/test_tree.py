"""tree: pre-order flatten with dedupe (TDD per algorithms/manual-tree-crawl.md).

Sample data is synthetic per the doc's TESTS section (G11); the helper `W`
builds the exact portal wrapper shape `{"topic": {...}, "topicTree": [...]}`.
"""

import copy
import random

from m21_crawl.tree import TopicNode, breadcrumb_paths, flatten_tree, leaf_topics


def W(topic_id: int, name: str, *children: dict) -> dict:
    """Build a portal wrapper (the verified live JSON shape)."""
    return {
        "topic": {
            "id": topic_id,
            "name": name,
            "childCount": len(children),
            "articleCount": 0,
            "articleTotalCount": 0,
        },
        "topicTree": list(children),
    }


def _ids(nodes: list) -> list[int]:
    return [int(node.id) for node in nodes]


# --- doc TESTS cases 1-10 -----------------------------------------------------


def test_case1_happy_path_preorder_depths_leaves() -> None:
    wrappers = [W(1, "R", W(2, "P1", W(3, "C11"), W(4, "C12")), W(5, "P2"))]
    nodes = flatten_tree(wrappers)
    assert _ids(nodes) == [1, 2, 3, 4, 5]
    assert [n.depth for n in nodes] == [0, 1, 2, 2, 1]
    assert {n.id for n in nodes if n.is_leaf} == {"3", "4", "5"}


def test_case2_empty_input() -> None:
    assert flatten_tree([]) == []


def test_case3_single_leaf() -> None:
    nodes = flatten_tree([W(7, "Solo")])
    assert len(nodes) == 1
    assert nodes[0].id == "7"
    assert nodes[0].name == "Solo"
    assert nodes[0].depth == 0
    assert nodes[0].is_leaf is True


def test_case4_cycle_terminates() -> None:
    wrappers = [W(10, "A", W(11, "B", W(10, "A")))]
    assert _ids(flatten_tree(wrappers)) == [10, 11]


def test_case5_self_loop() -> None:
    assert _ids(flatten_tree([W(12, "S", W(12, "S"))])) == [12]


def test_case6_diamond_first_occurrence_wins() -> None:
    wrappers = [W(20, "R", W(21, "X", W(22, "D")), W(23, "Y", W(22, "D")))]
    nodes = flatten_tree(wrappers)
    assert _ids(nodes) == [20, 21, 22, 23]
    assert sum(n.id == "22" for n in nodes) == 1


def test_case7_order_preservation_anti_sort_guard() -> None:
    """A `sorted()` regression would reorder to [30, 31, 32, 33]."""
    wrappers = [W(30, "R", W(33, "C3"), W(31, "C1"), W(32, "C2"))]
    assert _ids(flatten_tree(wrappers)) == [30, 33, 31, 32]


def test_case8_duplicate_top_level_wrappers() -> None:
    assert _ids(flatten_tree([W(40, "X"), W(40, "X")])) == [40]


def test_case9_malformed_input_raises() -> None:
    bad_inputs = [
        [{"topicTree": []}],  # missing "topic" key
        [{"topic": {"name": "no id"}, "topicTree": []}],  # missing id
        [{"topic": {"id": 1}, "topicTree": []}],  # missing name
        [{"topic": {"id": 1, "name": "x"}, "topicTree": "nope"}],  # not a list
    ]
    for wrappers in bad_inputs:
        try:
            flatten_tree(wrappers)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {wrappers}")


def test_case10_four_level_chain_depths() -> None:
    wrappers = [W(1, "L1", W(2, "L2", W(3, "L3", W(4, "L4", W(5, "L5")))))]
    nodes = flatten_tree(wrappers)
    assert _ids(nodes) == [1, 2, 3, 4, 5]
    assert [n.depth for n in nodes] == [0, 1, 2, 3, 4]
    assert [n.id for n in nodes if n.is_leaf] == ["5"]


# --- doc section 5.2 edge cases -------------------------------------------------


def test_topic_tree_key_absent_is_a_leaf() -> None:
    wrappers = [{"topic": {"id": 9, "name": "x"}}]
    nodes = flatten_tree(wrappers)
    assert len(nodes) == 1
    assert nodes[0].is_leaf is True


def test_topic_fields_passthrough() -> None:
    wrappers = [
        {
            "topic": {
                "id": 554400000004049,
                "name": "M21-1 Adjudication Procedures Manual",
                "articleCount": 3,
                "articleTotalCount": 785,
                "parentTopicId": 554400000001924,
            },
            "topicTree": [],
        }
    ]
    node = flatten_tree(wrappers)[0]
    assert node.id == "554400000004049"
    assert node.article_count == 3
    assert node.article_total_count == 785
    assert node.parent_id == "554400000001924"


def test_parent_id_none_when_absent() -> None:
    nodes = flatten_tree([{"topic": {"id": 1, "name": "x"}, "topicTree": []}])
    assert nodes[0].parent_id is None


# --- doc section 6.1 property tests ----------------------------------------------


def _naive_preorder(wrappers: list[dict]) -> list[str]:
    """Independent recursive reference (valid only for cycle-free, distinct ids)."""
    out: list[str] = []

    def rec(wrapper: dict) -> None:
        out.append(str(wrapper["topic"]["id"]))
        for child in wrapper.get("topicTree", []):
            rec(child)

    for wrapper in wrappers:
        rec(wrapper)
    return out


def _random_forest(rng: random.Random, n: int) -> list[dict]:
    """Random forest of n distinct topics; each node i>1 gets a random earlier parent."""
    children: dict[int, list[int]] = {i: [] for i in range(1, n + 1)}
    parents: set[int] = set()
    for i in range(2, n + 1):
        parent = rng.randrange(1, i)
        children[parent].append(i)
        parents.add(i)

    def build(topic_id: int) -> dict:
        return {
            "topic": {"id": topic_id, "name": f"t{topic_id}"},
            "topicTree": [build(c) for c in children[topic_id]],
        }

    return [build(i) for i in range(1, n + 1) if i not in parents]


def test_property_random_forest_matches_reference() -> None:
    for seed in range(10):
        wrappers = _random_forest(random.Random(seed), 40)
        expected = _naive_preorder(wrappers)
        assert [node.id for node in flatten_tree(wrappers)] == expected


def test_property_deterministic() -> None:
    wrappers = [W(1, "R", W(2, "P1"), W(3, "P2"))]
    assert flatten_tree(wrappers) == flatten_tree(wrappers)


def test_property_input_not_mutated() -> None:
    wrappers = [W(1, "R", W(2, "P", W(3, "L")))]
    snapshot = copy.deepcopy(wrappers)
    flatten_tree(wrappers)
    assert wrappers == snapshot


# --- leaf_topics ------------------------------------------------------------------


def test_leaf_topics_filters_and_preserves_order() -> None:
    wrappers = [W(1, "R", W(2, "P1", W(3, "C11"), W(4, "C12")), W(5, "P2"))]
    leaves = leaf_topics(flatten_tree(wrappers))
    assert [n.id for n in leaves] == ["3", "4", "5"]


# --- breadcrumb_paths ------------------------------------------------------------------


def _node(nid: str, name: str, depth: int, parent_id: str | None) -> TopicNode:
    return TopicNode(
        id=nid,
        name=name,
        depth=depth,
        is_leaf=depth > 0,
        article_count=0,
        article_total_count=0,
        parent_id=parent_id,
    )


def test_breadcrumb_paths_chain_excludes_root_includes_self() -> None:
    nodes = [
        _node("root", "M21-1 Manual", 0, None),
        _node("p1", "Part 1", 1, "root"),
        _node("c1", "Chapter 1-1", 2, "p1"),
        _node("s1", "Section 1-1-1", 3, "c1"),
    ]
    paths = breadcrumb_paths(nodes)
    assert paths == {
        "root": "",
        "p1": "Part 1",
        "c1": "Part 1 \u203a Chapter 1-1",
        "s1": "Part 1 \u203a Chapter 1-1 \u203a Section 1-1-1",
    }


def test_breadcrumb_paths_missing_parent_stops_chain() -> None:
    nodes = [_node("x", "X", 2, "ghost")]  # parent id not in the node set
    assert breadcrumb_paths(nodes) == {"x": "X"}


def test_breadcrumb_paths_parent_cycle_terminates() -> None:
    nodes = [_node("a", "A", 1, "b"), _node("b", "B", 2, "a")]  # a -> b -> a (malformed)
    paths = breadcrumb_paths(nodes)
    # walk stops before revisiting a node: each id appears at most once
    assert paths["a"] == "B \u203a A"
    assert paths["b"] == "A \u203a B"
