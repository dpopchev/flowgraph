"""The relations of a record checked as it is read: each names what the record holds.

A relation is checked at the write by the command that makes it; a file edited by hand or merged
can still name an id or a term that is not in the record, or close a cycle of what depends on what
or of one kind between terms. This reads every edge of the record as plain data, those of
`flowgraph.graph` and the terms its knowledge lines are about, and refuses the first that is
broken, naming the file that holds it. It reads and writes nothing else.
"""

from collections.abc import Callable, Mapping
from pathlib import Path

from flowgraph.feature.file import feature_file
from flowgraph.graph import Edge, nodes_and_edges
from flowgraph.item_id import parse_work_item_id_of_any_kind
from flowgraph.knowledge_list import collected
from flowgraph.parent import parse_feature_id
from flowgraph.record.store import Store
from flowgraph.term import term_file
from flowgraph.work_item import work_item_path

# The ids the work items of other worktrees hold, asked for only when an id is missing.
Elsewhere = Callable[[], frozenset[str]]

FEATURE = "feature"
TERM = "term"
WORK_ITEMS = frozenset({"story", "upkeep", "bug", "spike"})

# What the end of each kind of edge must be, and what the refusal calls the relation.
ENDS: dict[str, frozenset[str]] = {
    "under": frozenset({FEATURE}),
    "depends on": WORK_ITEMS,
    "filed during": WORK_ITEMS,
    "superseded by": WORK_ITEMS,
    "amends": WORK_ITEMS,
    "is a": frozenset({TERM}),
    "part of": frozenset({TERM}),
    "about": frozenset({TERM}),
}
NAMED = {"under": "parent"}

# The kinds of edge that must not close a cycle.
ACYCLIC = ("depends on", "is a", "part of")


class RelationReadError(ValueError):
    """A relation of the record read that names nothing, or closes a cycle."""


def find_cycle(follows: Mapping[str, list[str]]) -> list[str] | None:
    """The first cycle of the graph that maps each id to the ids it follows; None when it has none.

    The cycle is listed from where it is found and ends on the id it starts from. The ids are
    tried in order, so one record gives one answer.
    """
    done: set[str] = set()
    for start in sorted(follows):
        path: list[str] = []
        stack = [(start, iter(sorted(follows.get(start, []))))]
        on_path = {start}
        path.append(start)
        while stack:
            node, pending = stack[-1]
            following = next(pending, None)
            if following is None:
                stack.pop()
                path.pop()
                on_path.discard(node)
                done.add(node)
            elif following in on_path:
                return [*path[path.index(following) :], following]
            elif following not in done:
                stack.append((following, iter(sorted(follows.get(following, [])))))
                path.append(following)
                on_path.add(following)
    return None


def _file_of(record: Path, id_: str, kinds: Mapping[str, str]) -> Path:
    """The file of the Feature, the work item or the term of that id in the record."""
    match kinds[id_]:
        case "feature":
            return feature_file(record, parse_feature_id(id_))
        case "term":
            return term_file(record, id_)
        case _:
            return work_item_path(record, parse_work_item_id_of_any_kind(id_))


def _names(edge: Edge, kinds: Mapping[str, str], elsewhere: Elsewhere) -> str | None:
    """What is wrong with the end of the edge: the end it names; None when it is as it must be."""
    kind, _, end = edge
    ends = ENDS[kind]
    if kinds.get(end) in ends:
        return None
    if end not in kinds:
        if ends is WORK_ITEMS and end in elsewhere():
            return None
        return f"{NAMED.get(kind, kind)} names {end}, which is not in the record"
    return f"{NAMED.get(kind, kind)} names {end}, which is not a {' or '.join(sorted(ends))}"


def check_relations(record: Path, store: Store, elsewhere: Elsewhere) -> None:
    """Check every relation of the record: what each names is in it, and no cycle is closed.

    The work items of the other worktrees, read through elsewhere, are in the record too: a work
    item one holds is not a missing id. Raises RelationReadError with one line, the file that
    holds the relation first, for the first relation in the order of its kind and its ends that
    names an id or a term the record does not hold, then for the first cycle; nothing is written.
    """
    nodes, edges = nodes_and_edges(store)
    kinds = {str(node["id"]): str(node["kind"]) for node in nodes}
    lines = [("about", entry.item, term) for entry in collected(store) for term in entry.about]
    named = sorted({edge for edge in [*edges, *lines] if edge[0] in ENDS})
    for edge in named:
        refused = _names(edge, kinds, elsewhere)
        if refused is not None:
            raise RelationReadError(f"{_file_of(record, edge[1], kinds)}: {refused}")
    for kind in ACYCLIC:
        follows: dict[str, list[str]] = {}
        for each, start, end in named:
            if each == kind:
                follows.setdefault(start, []).append(end)
        cycle = find_cycle(follows)
        if cycle is not None:
            path = _file_of(record, cycle[0], kinds)
            raise RelationReadError(f"{path}: {kind} closes a cycle: {' -> '.join(cycle)}")
