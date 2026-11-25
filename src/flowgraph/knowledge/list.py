"""The knowledge of a record, listed: every line of every work item and Feature, newest first.

A view: it reads the record as plain data and changes nothing. Each line is listed under its ref,
the id of its item and its place there. The list is every line, or the live ones alone: those no
later line supersedes. The decision of a completed Spike is listed among the decisions at the
time the Spike was completed, under the id of the Spike and with no ref; it stays kept on the
Spike. A search keeps the lines whose text holds the text searched for, whatever the case of
either.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

from flowgraph.criterion import said
from flowgraph.feature import feature_detail
from flowgraph.knowledge.model import (
    DECISION,
    DEVIATION,
    FINDING,
    KnowledgeRow,
    about_text,
    kind_name,
    line_ref,
    mark_text,
)
from flowgraph.parent import parse_feature_id
from flowgraph.record.store import KINDS, Store
from flowgraph.term.about import term_asked
from flowgraph.work_item import WorkItemDetail, parse_work_item_id

# The kinds a list can be narrowed to, as the record writes them.
KINDS_LISTED = tuple(kind_name(kind) for kind in (FINDING, DECISION, DEVIATION))


class KindListedError(ValueError):
    """A kind to narrow the list to that is none of the three kinds of knowledge."""


@dataclass(frozen=True)
class KnowledgeEntry:
    """One line of knowledge as the list shows it: the id of its item, its kind, time and text.

    The terms it is about follow, then the files it governs, its mark, its ref (empty for the
    decision of a Spike) and the refs of the lines it supersedes.
    """

    item: str
    kind: str
    noted: datetime
    text: str
    about: list[str] = field(default_factory=list[str])
    governs: list[str] = field(default_factory=list[str])
    mark: str = ""
    ref: str = ""
    supersedes: list[str] = field(default_factory=list[str])


def chosen_kind(kind: str | None) -> str | None:
    """The kind the list is narrowed to; None for no narrowing.

    Raises KindListedError naming the three kinds when it is any other word.
    """
    if kind is not None and kind not in KINDS_LISTED:
        raise KindListedError(f"--kind {kind!r} is none of {', '.join(KINDS_LISTED)}")
    return kind


def sought(text: str | None) -> str | None:
    """The text the list is searched for as it is given; None for no search.

    Raises EmptyPartError naming the search when the text is blank.
    """
    return None if text is None else said("search", text)


def entries_of(item: str, rows: Iterable[KnowledgeRow]) -> list[KnowledgeEntry]:
    """The lines of the item of that id as entries, in the order they were noted.

    Each is under its ref, its place counted from 1 among the lines of the item.
    """
    return [
        KnowledgeEntry(
            item,
            row.kind,
            row.noted,
            row.text,
            row.about,
            row.governs,
            row.mark,
            line_ref(item, place),
            row.supersedes,
        )
        for place, row in enumerate(rows, start=1)
    ]


def decision_entries(detail: WorkItemDetail, completed: datetime | None) -> list[KnowledgeEntry]:
    """The decision of a completed Spike as an entry at its completed time; none for any other.

    The text names its answer when it holds one.
    """
    if not detail.decision or completed is None:
        return []
    text = f"{detail.decision} (answer {detail.answer})" if detail.answer else detail.decision
    return [KnowledgeEntry(detail.id, kind_name(DECISION), completed, text)]


def holding(entries: Iterable[KnowledgeEntry], text: str | None) -> list[KnowledgeEntry]:
    """The entries whose text holds the text, whatever the case; every entry for None.

    It reads the text of the line as the list writes it, the decision of a Spike with its answer,
    and nothing else of the entry: not its item, its kind, its terms or its files. It keeps the
    order given, so it composes before or after any other filter of the entries.
    """
    return [entry for entry in entries if text is None or text.casefold() in entry.text.casefold()]


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


def live_entries(entries: Iterable[KnowledgeEntry]) -> list[KnowledgeEntry]:
    """The entries no entry among them supersedes, in the order given.

    A line is live until a later line supersedes it, whatever its mark, as the developer decided
    on 2026-11-23: a line stays superseded when the line that supersedes it is superseded too.
    An entry with no ref, the decision of a Spike, is always kept.
    """
    read = list(entries)
    named = superseded_by(read)
    return [entry for entry in read if not entry.ref or entry.ref not in named]


def knowledge_text(
    entries: list[KnowledgeEntry],
    kind: str | None,
    about: str | None,
    search: str | None = None,
    live: bool = False,
) -> str:
    """The entries as the lines fgraph knowledge writes, or one line saying there are none.

    Each line is under its ref, or under the id of its item when it has none.
    """
    if not entries:
        about_it = "" if about is None else f" about {about}"
        held = "" if search is None else f" holding {search!r}"
        only = "live " if live else ""
        return f"no {only}{kind or 'knowledge'} lines{about_it}{held} in the record\n"
    return "".join(
        f"{entry.noted.date().isoformat()}  {entry.kind}  {entry.ref or entry.item}  {entry.text}"
        f"{mark_text(entry.mark)}{about_text(entry.about)}\n"
        for entry in entries
    )


def superseded_by(entries: Iterable[KnowledgeEntry]) -> dict[str, list[str]]:
    """Each ref some entry names as superseded, under the refs of the entries that name it.

    The refs that name one are in the order the entries are given.
    """
    named: dict[str, list[str]] = {}
    for entry in entries:
        for ref in entry.supersedes:
            named.setdefault(ref, []).append(entry.ref)
    return named


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


def listed_knowledge(
    kind: str | None,
    about: str | None,
    store: Store,
    search: str | None = None,
    live: bool = False,
) -> list[KnowledgeEntry]:
    """The entries fgraph knowledge lists for the options, newest first: both formats read them.

    The lines about that term alone when one is named, and those whose text holds the search when
    one is given. With live the live lines alone: the supersede is read over every line of the
    record before the kind and the term narrow the list. Raises KindListedError when the kind is
    none of the three, TermError when the record holds no term of that name and EmptyPartError
    when the search is blank. Nothing is written.
    """
    narrowed = chosen_kind(kind)
    term = None if about is None else term_asked(about, store)
    text = sought(search)
    lines = collected(store)
    if live:
        lines = live_entries(lines)
    return newest_first(holding(lines, text), narrowed, term)


def show_knowledge(
    kind: str | None,
    about: str | None,
    store: Store,
    search: str | None = None,
    live: bool = False,
) -> str:
    """The text fgraph knowledge gives: the lines of the record, of that kind when one is named.

    It is the text of listed_knowledge for the same options; the refusals are listed_knowledge's.
    """
    return knowledge_text(
        listed_knowledge(kind, about, store, search, live), kind, about, search, live
    )
