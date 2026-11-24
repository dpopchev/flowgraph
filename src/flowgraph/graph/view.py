"""The graph of a record: its nodes, its typed edges and its knowledge lines, as one JSON document.

A view: it reads the record as plain data and changes nothing. A node is a Feature, a work item, a
Task or a term, with its id, its kind, its title -- the meaning of a term -- and its bucket where
it has one. A Task node also holds its state, as status writes it. An edge has a kind and two
ends, from and to: a work item is under a Feature, a Task is of its work item, a work item
depends on, was filed during, is superseded by or amends another, a term is a kind of or part
of another, and a work item or a Feature is about a term. The knowledge lines are a list of
their own. The nodes are in the order of their ids, the edges in the order of their kinds as
listed here and then of their ends, the lines by item and time, so two runs on one record print
the same bytes.
"""

import json
from collections.abc import Iterable

from flowgraph.feature import feature_bucket
from flowgraph.knowledge.list import KnowledgeEntry, collected
from flowgraph.parent import parse_feature_id
from flowgraph.record.store import Store
from flowgraph.relation.depends import record_standing
from flowgraph.status import rows_by_id, rows_under
from flowgraph.status.buckets import BUCKETS
from flowgraph.task import TaskRow

# The one format of the graph, and the default.
JSON = "json"

# The kinds of edge, in the order the document lists them.
EDGES = (
    "under",
    "task of",
    "depends on",
    "filed during",
    "superseded by",
    "amends",
    "is a",
    "part of",
    "about",
)

type Node = dict[str, str | None]
type Edge = tuple[str, str, str]


class FormatError(ValueError):
    """A format of the graph that is none there is."""


def chosen_format(format_: str) -> str:
    """The format of the graph asked for.

    Raises FormatError naming the word when it is not json.
    """
    if format_ != JSON:
        raise FormatError(f"--format {format_!r} is not {JSON}, the one format of the graph")
    return format_


def _node(id_: str, kind: str, title: str, bucket: str | None = None) -> Node:
    """A node as the document writes it: its keys are always these four, in this order."""
    return {"id": id_, "kind": kind, "title": title, "bucket": bucket}


def task_node(task: TaskRow, item_state: str) -> Node:
    """The node of a Task: the four keys of a node, then its state as status writes it.

    Its bucket is the one `fgraph show` lists it in, Removed with its work item; the state tells
    a started Task from a blocked one, both in InProgress.
    """
    held = "removed" if item_state == "removed" else task.state
    bucket = next(name for name, states in BUCKETS if held in states)
    return {**_node(task.id, "task", task.title, bucket), "state": task.state}


def _feature_parts(store: Store) -> tuple[list[Node], list[Edge]]:
    """The node of every Feature of the record, and its edges to the terms it is about."""
    nodes: list[Node] = []
    edges: list[Edge] = []
    for text in store.features.find_feature_ids():
        held = store.features.load_feature(parse_feature_id(text))
        states = [row.state for row in rows_under(held.id, store).values()]
        nodes.append(_node(text, "feature", held.title, feature_bucket(held, states)))
        edges += [("about", text, term) for term in held.about]
    return nodes, edges


def _item_parts(store: Store) -> tuple[list[Node], list[Edge]]:
    """The nodes of every work item and Task of the record, and the edges the items name."""
    standing = record_standing(store)
    nodes: list[Node] = []
    edges: list[Edge] = []
    for item_id, row in rows_by_id(store).items():
        nodes.append(_node(row.id, item_id.kind.noun.lower(), row.title, standing[row.id].bucket))
        named = [
            ("under", row.parent),
            *(("depends on", each) for each in row.depends_on),
            ("filed during", row.filed_during),
            ("superseded by", row.superseded_by),
            ("amends", row.amends),
            *(("about", term) for term in store.find_work_item_detail(item_id).about),
        ]
        edges += [(kind, row.id, to) for kind, to in named if to]
        for task in row.tasks:
            nodes.append(task_node(task, row.state))
            edges.append(("task of", task.id, row.id))
    return nodes, edges


def _term_parts(store: Store) -> tuple[list[Node], list[Edge]]:
    """The node of every term of the record, and its edges to the terms it is a kind or part of."""
    nodes: list[Node] = []
    edges: list[Edge] = []
    for name in store.terms.find_term_names():
        term = store.terms.load_term(name)
        nodes.append(_node(name, "term", term.meaning))
        edges += [("is a", name, each) for each in term.is_a]
        edges += [("part of", name, each) for each in term.part_of]
    return nodes, edges


def _line(entry: KnowledgeEntry) -> dict[str, str | list[str]]:
    """A knowledge line as the document writes it."""
    return {
        "item": entry.item,
        "kind": entry.kind,
        "noted": entry.noted.isoformat(),
        "text": entry.text,
        "about": entry.about,
        "governs": entry.governs,
    }


def _edges_in_order(edges: Iterable[Edge]) -> list[dict[str, str]]:
    """The edges as the document writes them, by the order of their kinds, then their ends."""
    ordered = sorted(set(edges), key=lambda edge: (EDGES.index(edge[0]), edge[1], edge[2]))
    return [{"kind": kind, "from": start, "to": end} for kind, start, end in ordered]


def nodes_and_edges(store: Store) -> tuple[list[Node], list[Edge]]:
    """Every node and every edge of the record, in no order: the plain data the views read."""
    parts = [_feature_parts(store), _item_parts(store), _term_parts(store)]
    return [node for part in parts for node in part[0]], [
        edge for part in parts for edge in part[1]
    ]


def graph_text(format_: str, store: Store) -> str:
    """The text fgraph graph gives: the nodes, the edges and the knowledge lines, as JSON.

    Raises FormatError when the format is not json. Nothing is written.
    """
    chosen_format(format_)
    nodes, edges = nodes_and_edges(store)
    lines = sorted(collected(store), key=lambda entry: (entry.item, entry.noted))
    document = {
        "nodes": sorted(nodes, key=lambda node: str(node["id"])),
        "edges": _edges_in_order(edges),
        "knowledge": [_line(entry) for entry in lines],
    }
    return json.dumps(document, indent=2) + "\n"
