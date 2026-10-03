# In-Order Manual Topic-Tree Crawl (Pre-Order Flatten with Dedupe)

<!-- INDEX:BEGIN format=tsv version=1 -->
id	start_line	end_line
INDEX_BLOCK	3	13
METADATA	15	36
THEORY	37	181
PSEUDOCODE	182	237
WALKTHROUGH	238	286
IMPLEMENTATION	287	376
TESTS	377	416
REFERENCES	417	428
<!-- INDEX:END -->

<!-- SECTION:METADATA -->
## 1. Metadata

| Field | Value |
|---|---|
| Name | In-order manual topic-tree crawl (pre-order flatten with dedupe) |
| Slug | manual-tree-crawl |
| Version | 0.1.0 |
| Status | draft |
| Author | Bionic agent (on behalf of murphyjj) |
| Created | 2026-10-02 |
| Last modified | 2026-10-02 |
| Status history | 0.1.0 (2026-10-02): initial draft |
| Languages | Python 3.12 (implementation); pseudocode is language-agnostic |
| Implementation location | src/m21_crawl/tree.py — fill exact lines after implementation; "—" until then |
| Time complexity | O(N + E) — N distinct topic ids, E child references (see 2.4) |
| Space complexity | O(N + E) worst case (explicit stack + visited set) |
| Determinism | deterministic (pure function of input order and content) |
| Dependencies | none beyond the Python standard library (pure function over parsed JSON) |
| Thread safety | not thread-safe by contract; single-threaded crawl, no shared state |
| Related documents | [html-to-markdown-section-extraction](html-to-markdown-section-extraction.md) |

<!-- SECTION:THEORY -->
## 2. Theory

### 2.1 Problem definition

**Input.** The JSON returned by
`GET https://www.knowva.ebenefits.va.gov/system/ws/v11/ss/topic/554400000004049?portalId=554400000001018&usertype=customer&$level=10&$lang=en-US`.

The response has the shape (verified against live samples):

```json
{
  "topicTree": [
    {
      "topic": {
        "id": 554400000004049,
        "name": "M21-1 Adjudication Procedures Manual",
        "childCount": 17,
        "articleCount": 0,
        "articleTotalCount": 785,
        "parentTopicId": 554400000001924,
        "topicType": 1
      },
      "topicTree": [ { "topic": { ... }, "topicTree": [ ... ] } ]
    }
  ]
}
```

That is: a **wrapper** is `{"topic": <topic object>, "topicTree": [<wrapper>, ...]}`.
The top-level `topicTree` list holds the single root wrapper. A leaf wrapper's
`topicTree` is an empty list. Topic ids are 17-digit JSON integers (Python parses
them exactly as arbitrary-precision ints).

**Output.** A flat list `nodes: list[TopicNode]` where

```
TopicNode(id: str, name: str, depth: int, is_leaf: bool,
          article_count: int, article_total_count: int, parent_id: str | None)
```

`depth` is 0 for top-level wrappers, +1 per nesting level. `is_leaf` is true iff
the wrapper's own `topicTree` list is empty.

**Contract (guaranteed).**

1. **Pre-order:** every node appears before all of its descendants.
2. **Order preservation:** siblings appear in the exact order the API returned
   them. No alphabetical or id-based re-sorting, ever.
3. **Dedupe:** each topic id appears exactly once in the output. If the same id
   is reachable by several paths (a "diamond" reference), the **first occurrence
   in pre-order wins**.
4. **Termination:** the algorithm terminates on cyclic or self-referencing input
   (a topic that lists itself or an ancestor as a child).
5. **Totality:** valid wrapper input always produces a result; malformed input
   (missing `topic` key, missing `id`) raises `ValueError` — never silent loss.

**Forbidden / undefined.** Sorting by name or id; mutating the input structure;
assuming `childCount` equals `len(topicTree)` (we use the structural truth,
`len(topicTree)`, for leaf-ness).

### 2.2 Why this approach

Iterative depth-first search with an explicit stack and a visited set.

Rejected alternatives:

- **Recursive DFS.** Rejected: recursion depth is unbounded by input; a
  pathologically deep tree would hit Python's recursion limit (~1000) and
  `RecursionError`. Iteration removes the exposure entirely.
- **Breadth-first search.** Rejected: BFS emits siblings level by level, which
  interleaves Part I chapters with Part II chapters — destroying the portal's
  reading order (contract 2). Pre-order DFS is the only standard traversal that
  keeps a topic's whole subtree contiguous and in document order.
- **Per-level API calls** (`$level=1` per parent, N round-trips). Rejected:
  `$level=10` was verified to return the full 290-topic tree in a single call;
  N calls would be slower and multiply failure points for zero benefit.
- **Trusting `articleTotalCount` arithmetic to discover leaves.** Rejected:
  the count is a server-side summary; the *structure* (`topicTree`) is the
  source of truth for what exists and in what order.

### 2.3 Correctness argument

Invariant, maintained at every loop iteration:

- **I1 (parent-before-child).** A wrapper is pushed onto the stack only at the
  moment its parent is popped and emitted. Therefore when a node is popped, its
  parent has already been emitted.
- **I2 (no duplicate emission).** A node is emitted only if its id is not in
  `visited`; emission adds it. Hence each id is emitted at most once.
- **I3 (sibling order).** A parent's children are pushed in *reversed* order,
  so the first child in document order sits on top of the stack (LIFO) and is
  popped first. Inductively, siblings are emitted in document order.
- **I4 (termination).** Every push is guarded by `id not in visited`, and a
  wrapper's children are scanned only when that wrapper is *emitted* (at most
  once per id, by I2). Thus the total number of pushes is bounded by the total
  number of child references `E` in the input, and pops ≤ pushes. Each
  iteration does O(1) work plus a scan of the popped wrapper's child list.

I1 ⇒ contract 1. I3 ⇒ contract 2. I2 ⇒ contract 3 (the *first* pre-order
occurrence is the one emitted, because later occurrences find the id already in
`visited`). I4 ⇒ contract 4. Contract 5 falls out of explicit checks before any
traversal step reads `topic["id"]` / `topic["name"]`.

### 2.4 Complexity

Let `N` = number of distinct topic ids in the input, `E` = total number of
child references across all wrappers (sum of `len(topicTree)` over every
wrapper). Each emitted wrapper's child list is scanned once (≤ E scans total);
each scan step is O(1); emission, visited operations are O(1) (hash set).
**Time: O(N + E).** On well-formed trees E = N − 1, so O(N).

**Space: O(N + E)** worst case — the stack can hold up to E wrappers in the
adversarial case of duplicated references (each push is a distinct stack slot
until popped), `visited` holds ≤ N ids, output ≤ N nodes. On well-formed trees:
O(N). *Claimed, unverified* only in the sense that no benchmark has been run;
the bounds follow directly from the argument in 2.3.

### 2.5 Graph-class checklist

- **Graph model:** directed graph of topic references; vertices = topic ids;
  edges = parent→child references encoded in `topicTree`. The real portal data
  is a tree (one parent per child); the algorithm tolerates general directed
  graphs (diamonds, cycles).
- **Representation:** adjacency lists embedded in the JSON payload
  (wrapper.`topicTree`). No adjacency matrix (sparse; matrix would be
  O(N²) memory for no benefit).
- **Visited semantics:** emit-once, *first pre-order occurrence wins*. Checked
  at push time (avoids redundant stack work) and at pop time (final guarantee,
  I2). A node can be pushed twice in adversarial input and still emitted once.
- **Tie-breaking:** document order (API array order). Deterministic; never
  compares ids or names.
- **Disconnected components:** the API returns one root wrapper; if several
  top-level wrappers are supplied (e.g. a future multi-root response), they are
  processed left-to-right, each as its own component, and the output is the
  concatenation. A reference to an id absent from the payload is impossible by
  construction (children always ship inside the payload).
- **Recursion-depth policy:** none — iterative explicit stack; depth ≤ E.
- **Cycle test:** required (TESTS case 4) — a self-loop and a 2-cycle must
  terminate and emit each id exactly once.

### 2.6 Deviations

none — documented before implementation.

<!-- SECTION:PSEUDOCODE -->
## 3. Pseudocode

```
# Contract of helpers:
#   wrapper_topic(w)  -> w["topic"]; raises ValueError if key missing
#   wrapper_children(w) -> w["topicTree"] or []; raises ValueError if
#                          "topicTree" present but not a list

function flatten_tree(wrappers) -> list[TopicNode]:
    # Pre: wrappers is a list (possibly empty) of wrapper objects.
    # Post: returns nodes satisfying contracts 1-5 of section 2.1.
    result  <- []
    visited <- {}                      # set of emitted topic ids
    stack   <- []                      # entries: (wrapper, depth)

    # Push top-level wrappers in REVERSED order so that wrappers[0]
    # (first in document order) is popped first. (I3)
    for w in reverse(wrappers):
        stack.push((w, 0))

    while stack is not empty:
        (w, depth) <- stack.pop()
        t          <- wrapper_topic(w)          # raises ValueError if malformed
        node_id    <- str(t["id"])              # raises KeyError -> caller maps to ValueError
        node_name  <- t["name"]                 # same

        if node_id in visited:
            continue                            # already emitted earlier (I2): skip
        visited.add(node_id)

        children <- wrapper_children(w)
        result.append(TopicNode(
            id=node_id, name=node_name, depth=depth,
            is_leaf=(len(children) == 0),        # structural leaf-ness (2.1)
            article_count=t.get("articleCount", 0),
            article_total_count=t.get("articleTotalCount", 0),
            parent_id=(str(t["parentTopicId"]) if t.get("parentTopicId") is not None else None)))

        # Push children in REVERSED order: first child ends up on top (I3).
        # Guard each push: skip ids already emitted (I2, I4).
        for c in reverse(children):
            c_id <- str(wrapper_topic(c)["id"])
            if c_id not in visited:
                stack.push((c, depth + 1))

    return result

function leaf_topics(nodes) -> list[TopicNode]:
    # Contract: returns exactly the nodes with is_leaf true, same order.
    return [n for n in nodes if n.is_leaf]
```

Termination argument: see I4 in 2.3 — total pushes ≤ E (each child reference is
scanned only when its parent is emitted, and each id is emitted at most once).

<!-- SECTION:WALKTHROUGH -->
## 4. Walk-through (plain English)

### 4.1 Step-by-step

1. Read the top-level list of wrappers (for the live portal: exactly one — the
   root "M21-1 Adjudication Procedures Manual").
2. Put every top-level wrapper on a stack, last-first, all at depth 0.
3. Pop the top wrapper. If we have already emitted this topic id somewhere
   earlier, drop it (duplicate reference) and go to the next pop.
4. Otherwise, record it: its id, name, current depth, whether it has children,
   and its article counts. This is the node's single emission.
5. Push all of its children onto the stack, last-first (so the first child in
   the manual's order comes off next), each at depth + 1, skipping any child id
   we have already emitted.
6. Repeat 3–5 until the stack is empty. The recorded list is the manual's
   topic order.

### 4.2 Worked example

Input (synthetic, mirrors TESTS case 1) — `wrappers` holds root R:

```
R  (depth 0)
├── P1 (depth 1)
│   ├── C11 (depth 2, leaf)
│   └── C12 (depth 2, leaf)
└── P2 (depth 1, leaf)
```

Trace:

1. Push R. Stack: `[R]`.
2. Pop R. Not visited → emit `R` (depth 0, not leaf: 2 children). Push P2 then
   P1 (reversed). Stack: `[P1, P2]` (P1 on top).
3. Pop P1. Emit `P1` (depth 1, not leaf). Push C12 then C11. Stack:
   `[C11, C12, P2]`.
4. Pop C11. Emit `C11` (depth 2, leaf). No children. Stack: `[C12, P2]`.
5. Pop C12. Emit `C12` (depth 2, leaf). Stack: `[P2]`.
6. Pop P2. Emit `P2` (depth 1, leaf). Stack: `[]`.
7. Stack empty → stop.

Output order: `R, P1, C11, C12, P2` — exactly pre-order, exactly the document
order, and `leaf_topics` returns `C11, C12, P2`.

Now the cycle (TESTS case 4): A→B→A. Push A; pop A, emit, push B (B not
visited); pop B, emit, its child A is already visited → not pushed; stack empty.
Output `A, B`. Terminated, no infinite loop, no duplicate.

<!-- SECTION:IMPLEMENTATION -->
## 5. Implementation notes (entry-level guide)

### 5.1 Data structures

```python
@dataclass(frozen=True)
class TopicNode:
    id: str  # canonical string form of the JSON integer id
    name: str  # verbatim API name (no trimming)
    depth: int  # 0 = top-level wrapper
    is_leaf: bool  # len(wrapper["topicTree"]) == 0
    article_count: int  # topic["articleCount"] (direct articles)
    article_total_count: int  # topic["articleTotalCount"] (incl. descendants)
    parent_id: str | None  # topic["parentTopicId"] as str, or None


def flatten_tree(wrappers: list[dict]) -> list[TopicNode]: ...
def leaf_topics(nodes: list[TopicNode]) -> list[TopicNode]: ...
```

- `wrappers` are the raw JSON dicts (read-only; **never mutate them**).
- `stack` is a plain Python `list` used LIFO (`append`/`pop`), holding
  `(wrapper, depth)` tuples. No heap, no deque needed.
- `visited` is a `set[str]`.

### 5.2 Edge cases and defined behavior

| Case | Defined behavior | Why |
|---|---|---|
| Empty wrapper list `[]` | returns `[]` | no topics, nothing to emit |
| Single wrapper, no children | one node, `depth=0`, `is_leaf=True` | degenerate tree |
| Cycle A→B→A | terminates; output `A, B` (or `B, A` by pre-order); each id once | contract 4 |
| Self-loop A→A | terminates; output `A` once | contract 4 |
| Diamond (id D referenced under two siblings) | D emitted once, under the FIRST sibling in pre-order | contract 3, first-occurrence-wins |
| Duplicate top-level wrappers (same id) | emitted once | contract 3 |
| Wrapper missing `topic` key, or `topic` missing `id`/`name` | raises `ValueError` with the offending id/path | contract 5 — loud failure beats silent loss |
| `topicTree` key absent | treated as empty list (leaf) | API omits empty lists in some responses; lenient on absence, strict on type |
| `topicTree` present but not a list | raises `ValueError` | malformed payload must not be walked |
| Extra unknown keys in `topic` | ignored | forward-compat |
| Topic with `articleCount=0` but non-empty children | still emitted; leaf-ness is structural | counts are summaries, not structure |

### 5.3 Invariants and how to test them

| Invariant | How a test observes a violation |
|---|---|
| Parent emitted before child (pre-order) | build a 3-level tree; assert output index(parent) < index(child) for every edge |
| No duplicate ids in output | feed a diamond and a cycle; assert `len(nodes) == len({n.id for n in nodes})` |
| Sibling order preserved | feed children in order `[C3, C1, C2]`; assert output order is `[C3, C1, C2]` (a sort bug would give `[C1, C2, C3]`) |
| Termination on cycles | feed A→B→A and A→A; assert the call returns (a timeout in CI also catches hangs) |
| Read-only input | deep-copy the input, run, assert the copy is unchanged |

### 5.4 Pitfalls and known traps

- **Sorting by name/id "to tidy up"** — the single most likely regression. The
  manual must be in portal order; any `sorted()` on the node list is a defect.
  TESTS case 7 exists to catch exactly this.
- **Push order.** Pushing children in document order (not reversed) silently
  reverses the manual. The reversed-push + LIFO combination is what preserves
  order; keep both together.
- **JSON integer ids are 17-digit numbers.** Python parses them exactly (no
  float coercion), but keep them as `str` in the public `TopicNode` so URLs and
  logs stay uniform. Do not format them as floats.
- **`childCount` is not authoritative.** The portal's `childCount` field is a
  summary; leaf-ness must come from the actual `topicTree` list (5.2).
- **Mutating input** (e.g. popping children off the wrapper while walking)
  destroys the structure for a second pass and breaks the read-only test.
- **Recursion.** Do not "simplify" this to a recursive helper; the whole point
  of the iterative design is unbounded input depth (2.2).

### 5.5 Language notes

Pure Python 3.12, standard library only (`dataclasses`, typing). The reference
structure is:

```python
def flatten_tree(wrappers: list[dict]) -> list[TopicNode]:
    result: list[TopicNode] = []
    visited: set[str] = set()
    stack: list[tuple[dict, int]] = [(w, 0) for w in reversed(wrappers)]
    while stack:
        wrapper, depth = stack.pop()
        ...  # per section 3, with the ValueError checks of 5.2
    return result
```

No standard-library shortcut replaces this traversal (no `itertools` one-liner
exists for visited-set DFS over JSON), so the explicit loop IS the reference
implementation.

<!-- SECTION:TESTS -->
## 6. Test cases and sample data

All sample data is **synthetic** (G11): ids are small integers, names are
invented. In the real portal these are 17-digit ids like `554400000004049`.
A helper builds wrappers: `W(id, name, *children)` → `{"topic": {"id": id,
"name": name, ...}, "topicTree": list(children)}`.

| # | Name | Input (sample data) | Expected output | Why it matters |
|---|---|---|---|---|
| 1 | happy path (pre-order, depths, leaves) | `W(1,"R", W(2,"P1", W(3,"C11"), W(4,"C12")), W(5,"P2"))` | ids `[1,2,3,4,5]`; depths `[0,1,2,2,1]`; leaves `{3,4,5}` | core contract: order + structure |
| 2 | empty input | `[]` | `[]` | degenerate input must not crash |
| 3 | single leaf | `W(7,"Solo")` | `[TopicNode(7,"Solo",depth=0,is_leaf=True)]` | minimal tree |
| 4 | cycle A→B→A | `W(10,"A", W(11,"B", W(10,"A")))` | ids `[10,11]`, terminates | contract 4: no infinite loop |
| 5 | self-loop | `W(12,"S", W(12,"S"))` | ids `[12]` | contract 4 |
| 6 | diamond, first-occurrence-wins | `W(20,"R", W(21,"X", W(22,"D")), W(23,"Y", W(22,"D")))` | ids `[20,21,22,23]`; `22` appears once, after `21` | contract 3 |
| 7 | order preservation (anti-sort guard) | `W(30,"R", W(33,"C3"), W(31,"C1"), W(32,"C2"))` | ids `[30,33,31,32]` | catches any `sorted()` regression |
| 8 | duplicate top-level wrappers | `[W(40,"X"), W(40,"X")]` | ids `[40]` | contract 3 at the root list |
| 9 | malformed: missing id | `W_missing_id` (topic dict without `"id"`) | raises `ValueError` | contract 5: loud failure |
| 10 | depth 4 trace | 4-level chain `1→2→3→4→5` | depths `[0,1,2,3,4]`, only id 5 is a leaf | mirrors the live portal's shape (depth 4) |

### 6.1 Property tests (preferred)

For any input (random wrapper forest, seeded):

- **P1:** `len(output) ≤ number of distinct ids in input`.
- **P2:** for every emitted non-root node, its parent (per the input edge)
  was emitted earlier (pre-order property).
- **P3:** for inputs with all-distinct ids, output length == total node count
  and the sequence equals the recursive pre-order enumeration (cross-check with
  an independent naive recursive reference inside the test).
- **P4:** determinism — two runs on the same input produce identical lists.
- **P5:** input structure is unchanged after the call (deep-equality).

### 6.2 Performance acceptance

Live tree: 290 topics, 219 leaves, depth 4 (single API call, ~100 KB JSON).
`flatten_tree` must complete in < 50 ms on a laptop-class CPU (claimed,
unverified — trivially within O(N+E) for N=290).

<!-- SECTION:REFERENCES -->
## 7. References

- VA Knowva eBenefits topic service v11 (reverse-engineered contract; live
  samples verified 2026-10-02): `GET /system/ws/v11/ss/topic/{topicId}` with
  `$level=10` returns the full tree in one call; root `articleTotalCount=785`.
- CLRS 3rd ed., §22 (graph search): DFS pre-order properties and the
  visited-set termination argument used in 2.3.
- Sibling document: [html-to-markdown-section-extraction](html-to-markdown-section-extraction.md)
  (consumes the leaf topics and article ordering established here).
- algorithm-records-keeper skill, `references/use-cases/graph.md` checklist
  (applied in 2.5).
