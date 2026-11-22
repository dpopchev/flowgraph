"""The links of an item, listed: each relation that holds of it, under a heading of its own.

A view: it reads the record as plain data and changes nothing. A work item lists its Feature, the
work items it depends on and those that depend on it, the one it was filed during and those filed
during it, what it supersedes and what supersedes it, what it amends and what amends it, its terms
and its knowledge lines; a Feature lists its work items, its terms and its knowledge lines. Every
other side of a relation is derived from the record, as `fgraph show` derives it.
"""

from collections.abc import Sequence
from typing import assert_never

from flowgraph.feature import FeatureDetail, feature_bucket, feature_detail
from flowgraph.item_depends import bucketed, record_standing
from flowgraph.item_id import parse_shown_id
from flowgraph.knowledge import KnowledgeRow, about_text
from flowgraph.parent import FeatureId, feature_id_text, parse_feature_id
from flowgraph.relation import Standing, depended_on_by
from flowgraph.status import rows_by_id, rows_under
from flowgraph.store import Store
from flowgraph.work_item import WorkItemDetail, WorkItemId

# A heading with the lines under it, the lines already worded.
type Section = tuple[str, list[str]]


def _listed(ids: Sequence[str], titles: dict[str, str], record: dict[str, Standing]) -> list[str]:
    """The work items of those ids, each as a line: its id, its bucket and its title."""
    return [f"{each}  {record[each].bucket}  {titles[each]}" for each in ids]


def _terms(names: Sequence[str], store: Store) -> list[str]:
    """The terms of those names, each as a line: its name and its meaning."""
    return [f"{name}  {store.terms.load_term(name).meaning}" for name in names]


def _knowledge(rows: Sequence[KnowledgeRow]) -> list[str]:
    """The knowledge lines, each as a line: its kind, its day and its text, then its terms."""
    return [
        f"{row.kind}  {row.noted.date().isoformat()}  {row.text}{about_text(row.about)}"
        for row in rows
    ]


def _feature_line(text: str, store: Store) -> str:
    """The Feature of that id as a line: its id, its bucket over its work items and its title."""
    feature_id = parse_feature_id(text)
    held = store.features.load_feature(feature_id)
    states = [row.state for row in rows_under(feature_id, store).values()]
    return f"{text}  {feature_bucket(held, states)}  {held.title}"


def _item_sections(detail: WorkItemDetail, store: Store) -> list[Section]:
    """The relations of a work item, in the order the view lists them, each with its lines."""
    detail = bucketed(detail, store)
    record = record_standing(store)
    titles = {row.id: row.title for row in rows_by_id(store).values()}
    own = [detail.superseded_by] if detail.superseded_by else []
    amends = [detail.amends] if detail.amends else []
    during = [detail.filed_during] if detail.filed_during else []
    return [
        ("feature", [_feature_line(detail.parent, store)] if detail.parent else []),
        ("depends on", _listed([row.id for row in detail.depends_on], titles, record)),
        ("depended on by", _listed(depended_on_by(detail.id, record), titles, record)),
        ("filed during", _listed(during, titles, record)),
        ("filed here", _listed(detail.filed_here, titles, record)),
        ("supersedes", _listed(detail.supersedes, titles, record)),
        ("superseded by", _listed(own, titles, record)),
        ("amends", _listed(amends, titles, record)),
        ("amended by", _listed(detail.amended_by, titles, record)),
        ("terms", _terms(detail.about, store)),
        ("knowledge", _knowledge(detail.knowledge)),
    ]


def _feature_sections(detail: FeatureDetail, feature: FeatureId, store: Store) -> list[Section]:
    """The links of a Feature: its work items, its terms and its knowledge lines."""
    record = record_standing(store)
    held = rows_under(feature, store).values()
    return [
        (
            "work items",
            _listed([row.id for row in held], {row.id: row.title for row in held}, record),
        ),
        ("terms", _terms(detail.about, store)),
        ("knowledge", _knowledge(detail.knowledge)),
    ]


def _text(head: str, sections: Sequence[Section]) -> str:
    """The head line, then each section that holds a line under its heading with its count."""
    return head + "".join(
        f"  {heading} ({len(lines)})\n" + "".join(f"    {line}\n" for line in lines)
        for heading, lines in sections
        if lines
    )


def about_item(item: str, store: Store) -> str:
    """The text fgraph about gives of the work item or Feature of that id: its links by relation.

    Raises FeatureIdError for a Feature id below 1, ItemIdError for a text that is neither id, and
    the refusal of `fgraph show` for an id the record holds no item of. Nothing is written.
    """
    match parse_shown_id(item):
        case FeatureId() as feature:
            detail = feature_detail(store.features.load_feature(feature))
            head = f"{feature_id_text(feature)}  {detail.title}\n"
            return _text(head, _feature_sections(detail, feature, store))
        case WorkItemId() as work_item:
            detail = store.find_work_item_detail(work_item)
            return _text(f"{detail.id}  {detail.title}\n", _item_sections(detail, store))
        case _ as unreachable:
            assert_never(unreachable)
