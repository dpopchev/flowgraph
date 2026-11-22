"""The knowledge of a record, listed: every line of every work item and Feature, newest first.

A view: it reads the record as plain data and changes nothing. The decision of a completed Spike
is listed among the decisions at the time the Spike was completed; it stays kept on the Spike.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

from flowgraph.about import term_asked
from flowgraph.feature import feature_detail
from flowgraph.knowledge import (
    DECISION,
    DEVIATION,
    FINDING,
    KnowledgeRow,
    about_text,
    kind_name,
)
from flowgraph.parent import parse_feature_id
from flowgraph.store import KINDS, Store
from flowgraph.work_item import WorkItemDetail, parse_work_item_id

# The kinds a list can be narrowed to, as the record writes them.
KINDS_LISTED = tuple(kind_name(kind) for kind in (FINDING, DECISION, DEVIATION))


class KindListedError(ValueError):
    """A kind to narrow the list to that is none of the three kinds of knowledge."""


@dataclass(frozen=True)
class KnowledgeEntry:
    """One line of knowledge as the list shows it: the id of its item, its kind, time and text.

    The terms it is about follow.
    """

    item: str
    kind: str
    noted: datetime
    text: str
    about: list[str] = field(default_factory=list[str])


def chosen_kind(kind: str | None) -> str | None:
    """The kind the list is narrowed to; None for no narrowing.

    Raises KindListedError naming the three kinds when it is any other word.
    """
    if kind is not None and kind not in KINDS_LISTED:
        raise KindListedError(f"--kind {kind!r} is none of {', '.join(KINDS_LISTED)}")
    return kind


def entries_of(item: str, rows: Iterable[KnowledgeRow]) -> list[KnowledgeEntry]:
    """The lines of the item of that id as entries, in the order they were noted."""
    return [KnowledgeEntry(item, row.kind, row.noted, row.text, row.about) for row in rows]


def decision_entries(detail: WorkItemDetail, completed: datetime | None) -> list[KnowledgeEntry]:
    """The decision of a completed Spike as an entry at its completed time; none for any other."""
    if not detail.decision or completed is None:
        return []
    return [KnowledgeEntry(detail.id, kind_name(DECISION), completed, detail.decision)]


def newest_first(
    entries: Iterable[KnowledgeEntry], kind: str | None, about: str | None = None
) -> list[KnowledgeEntry]:
    """The entries of that kind and about that term, every kind and term for none, last noted first.

    Of lines noted at one time the one collected last comes first, so an item's lines noted in
    one second keep their order reversed too.
    """
    kept = [
        entry
        for entry in entries
        if (kind is None or entry.kind == kind) and (about is None or about in entry.about)
    ]
    return sorted(reversed(kept), key=lambda entry: entry.noted, reverse=True)


def knowledge_text(entries: list[KnowledgeEntry], kind: str | None, about: str | None) -> str:
    """The entries as the lines fgraph knowledge writes, or one line saying there are none."""
    if not entries:
        about_it = "" if about is None else f" about {about}"
        return f"no {kind or 'knowledge'} lines{about_it} in the record\n"
    return "".join(
        f"{entry.noted.date().isoformat()}  {entry.kind}  {entry.item}  {entry.text}"
        f"{about_text(entry.about)}\n"
        for entry in entries
    )


def collected(store: Store) -> list[KnowledgeEntry]:
    """The entries of every work item and Feature of the record, the work items first."""
    entries: list[KnowledgeEntry] = []
    for kind in KINDS:
        for row in store.find_work_item_rows(kind):
            detail = store.find_work_item_detail(parse_work_item_id(kind, row.id))
            entries += entries_of(detail.id, detail.knowledge)
            entries += decision_entries(detail, row.completed)
    for text in store.features.find_feature_ids():
        detail = feature_detail(store.features.load_feature(parse_feature_id(text)))
        entries += entries_of(detail.id, detail.knowledge)
    return entries


def show_knowledge(kind: str | None, about: str | None, store: Store) -> str:
    """The text fgraph knowledge gives: the lines of the record, of that kind when one is named.

    The lines about that term alone when one is named. Raises KindListedError when the kind is
    none of the three and TermError when the record holds no term of that name. Nothing is
    written.
    """
    narrowed = chosen_kind(kind)
    term = None if about is None else term_asked(about, store)
    return knowledge_text(newest_first(collected(store), narrowed, term), narrowed, term)
