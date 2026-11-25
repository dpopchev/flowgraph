"""The links of an item, listed: each relation that holds of it, under a heading of its own.

A view: it reads the record as plain data and changes nothing. A work item lists its Feature, the
work items it depends on and those that depend on it, the one it was filed during and those filed
during it, what it supersedes and what supersedes it, what it amends and what amends it, its terms
and its knowledge lines; a Feature lists its work items, its terms and its knowledge lines. Every
other side of a relation is derived from the record, as `fgraph show` derives it. A term lists its
meaning and relations as `fgraph show` does, then what is about it and about every term under it:
each term that is part of it or is a kind of it, and those under them, to any depth.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import assert_never

from flowgraph.about.document import TEXT, about_json, chosen_about_format
from flowgraph.about.file import file_links, is_file_here, is_governed, is_touched
from flowgraph.about.links import (
    About,
    FileLinks,
    ItemLinks,
    Linked,
    Reached,
    ReachedLine,
    TermLinks,
)
from flowgraph.about.text import file_text, item_text, term_about_text
from flowgraph.brief.model import TermLine
from flowgraph.development.commit import OpenGit
from flowgraph.feature import FeatureDetail, feature_bucket, feature_detail
from flowgraph.item.id import ItemIdError, parse_shown_id
from flowgraph.knowledge.list import collected, newest_first
from flowgraph.parent import FeatureId, feature_id_text, parse_feature_id
from flowgraph.record.store import Store
from flowgraph.relation import Standing, depended_on_by
from flowgraph.relation.depends import bucketed, record_standing
from flowgraph.status import rows_by_id, rows_under
from flowgraph.term import TermNotFoundError, is_term_name
from flowgraph.term.item import items_about, term_head
from flowgraph.work_item import WorkItemDetail, WorkItemId


def _listed(
    ids: Sequence[str], titles: dict[str, str], record: dict[str, Standing]
) -> list[Linked]:
    """The work items of those ids, each linked: its id, its bucket and its title."""
    return [Linked(each, record[each].bucket, titles[each]) for each in ids]


def _terms(names: Sequence[str], store: Store) -> list[TermLine]:
    """The terms of those names, each with its meaning."""
    return [TermLine(name, store.terms.load_term(name).meaning) for name in names]


def _feature_line(text: str, store: Store) -> Linked:
    """The Feature of that id linked: its id, its bucket over its work items and its title."""
    feature_id = parse_feature_id(text)
    held = store.features.load_feature(feature_id)
    states = [row.state for row in rows_under(feature_id, store).values()]
    return Linked(text, feature_bucket(held, states), held.title)


def _item_links(detail: WorkItemDetail, store: Store) -> ItemLinks:
    """The relations of a work item, in the order the view lists them, each with its links."""
    detail = bucketed(detail, store)
    record = record_standing(store)
    titles = {row.id: row.title for row in rows_by_id(store).values()}
    own = [detail.superseded_by] if detail.superseded_by else []
    amends = [detail.amends] if detail.amends else []
    during = [detail.filed_during] if detail.filed_during else []
    links = {
        "feature": [_feature_line(detail.parent, store)] if detail.parent else [],
        "depends on": _listed([row.id for row in detail.depends_on], titles, record),
        "depended on by": _listed(depended_on_by(detail.id, record), titles, record),
        "filed during": _listed(during, titles, record),
        "filed here": _listed(detail.filed_here, titles, record),
        "supersedes": _listed(detail.supersedes, titles, record),
        "superseded by": _listed(own, titles, record),
        "amends": _listed(amends, titles, record),
        "amended by": _listed(detail.amended_by, titles, record),
    }
    return ItemLinks(detail.id, detail.title, links, _terms(detail.about, store), detail.knowledge)


def _feature_links(detail: FeatureDetail, feature: FeatureId, store: Store) -> ItemLinks:
    """The links of a Feature: its work items, its terms and its knowledge lines."""
    record = record_standing(store)
    held = rows_under(feature, store).values()
    titles = {row.id: row.title for row in held}
    links = {"work items": _listed([row.id for row in held], titles, record)}
    return ItemLinks(
        feature_id_text(feature), detail.title, links, _terms(detail.about, store), detail.knowledge
    )


def terms_under(name: str, over: Mapping[str, tuple[str, ...]]) -> list[str]:
    """The terms under that term, nearest first: each that names it, then those that name those.

    `over` gives each term the names it is part of or a kind of. A term is listed once, and the
    walk ends on a term already reached, so a cycle ends it.
    """
    reached = [name]
    for each in reached:
        reached.extend(
            under for under, names in over.items() if each in names and under not in reached
        )
    return reached[1:]


def _term_links(name: str, store: Store) -> TermLinks:
    """A term: its head, then the items and knowledge lines about it and under it.

    The head is read as `term_head` reads it. Raises TermNotFoundError for a term the record
    holds none of.
    """
    term = store.terms.load_term(name)
    held = {each: store.terms.load_term(each) for each in store.terms.find_term_names()}
    under = terms_under(name, {each: (*one.is_a, *one.part_of) for each, one in held.items()})
    lines = collected(store)
    seen_items: set[str] = set()
    seen_lines: set[int] = set()
    items: list[Reached] = []
    knowledge: list[ReachedLine] = []
    for each in [name, *under]:
        via = "" if each == name else each
        for id_ in items_about(each, store):
            if id_ not in seen_items:
                seen_items.add(id_)
                items.append(Reached(id_, via))
        for line in newest_first(lines, None, each):
            if id(line) not in seen_lines:
                seen_lines.add(id(line))
                knowledge.append(ReachedLine(line, via))
    return TermLinks(
        term.name,
        term.meaning,
        term.added,
        term.is_a,
        term.part_of,
        sorted(each for each, one in held.items() if name in one.is_a),
        sorted(each for each, one in held.items() if name in one.part_of),
        items,
        knowledge,
    )


def _is_path(text: str, directory: Path, store: Store, open_git: OpenGit) -> bool:
    """True when the text is a file on the disk, one a commit changed or one a line governs.

    A file a commit of the history of HEAD changed is one deleted since or not; the git read goes
    before the governed one, which loads every item of the record.
    """
    return (
        is_file_here(text, directory)
        or is_touched(text, directory, open_git)
        or is_governed(text, directory, store, open_git)
    )


def about_links(item: str, store: Store, directory: Path, open_git: OpenGit) -> About:
    """The links of what is named: a work item, a Feature, a term or a file.

    The text is read as an id, then as a term, then as the path of a file from the directory
    fgraph runs in, read from the git work tree of the directory: a file on the disk, one a commit
    of the history of HEAD changed, a deleted file too, or one a line of the record governs.
    Raises FeatureIdError for a Feature id below 1, ItemIdError for a text that is none of them
    or a path git cannot answer for and no line governs, and the refusal of `fgraph show` for an
    id the record holds no item of. Nothing is written.
    """
    if is_term_name(item):
        try:
            return _term_links(item, store)
        except TermNotFoundError as error:
            if _is_path(item, directory, store, open_git):
                return file_links(item, directory, store, open_git)
            raise ItemIdError(
                f"{item!r} is no Story, Upkeep, Bug, Spike or Feature id, no term in the record"
                " and no file"
            ) from error
    try:
        placed = parse_shown_id(item)
    except ItemIdError:
        if _is_path(item, directory, store, open_git):
            return file_links(item, directory, store, open_git)
        raise
    match placed:
        case FeatureId() as feature:
            detail = feature_detail(store.features.load_feature(feature))
            return _feature_links(detail, feature, store)
        case WorkItemId() as work_item:
            return _item_links(store.find_work_item_detail(work_item), store)
        case _ as unreachable:
            assert_never(unreachable)


def about_item(
    item: str, store: Store, directory: Path, open_git: OpenGit, format_: str = TEXT
) -> str:
    """What fgraph about gives of what is named: a work item, a Feature, a term or a file.

    The links of `about_links`, as JSON or worded as text, a term after its head, the words of
    `fgraph show`. The format is text or json, chosen first: raises AboutFormatError naming both
    for another, before anything is read. Raises what `about_links` raises.
    """
    chosen = chosen_about_format(format_)
    links = about_links(item, store, directory, open_git)
    if chosen != TEXT:
        return about_json(links)
    match links:
        case ItemLinks():
            return item_text(links)
        case TermLinks():
            return term_head(links.name, store) + term_about_text(links)
        case FileLinks():
            return file_text(links)
        case _ as unreachable:
            assert_never(unreachable)
