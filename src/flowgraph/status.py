"""The status of a record: its work items and its Features listed by bucket, read from its store.

A view: it reads the rows, the queue and the Features of the record and changes nothing. A
Feature is one item of its bucket, listed in place of its work items: a started one of
InProgress, a completed one of Completed, one never started of the bucket derived from its work
items.
"""

from collections.abc import Collection, Iterable, Mapping
from dataclasses import replace
from datetime import datetime
from typing import assert_never

from flowgraph.feature import (
    BlockedFeature,
    CompletedFeature,
    Feature,
    FeatureRow,
    FeatureState,
    RemovedFeature,
    StartedFeature,
    feature_row,
)
from flowgraph.parent import feature_id_text, parse_feature_id
from flowgraph.queue import Entry, Inside, Line, Placed, queued
from flowgraph.store import KINDS, Store
from flowgraph.text import status_text
from flowgraph.work_item import WorkItemId, WorkItemRow, parse_work_item_id

# The state of a row in Backlog, as the record writes it.
BACKLOG = "backlog"

# The states of a started and of a completed row, as the record writes them.
STARTED = "started"
COMPLETED = "completed"

# The row of a Feature with the time that places it in its bucket.
type _PlacedFeature = tuple[datetime, FeatureRow]


def rows_by_id(store: Store) -> dict[WorkItemId, WorkItemRow]:
    """The row of every work item in the record under its id, by kind and then by number."""
    return {
        parse_work_item_id(kind, row.id): row
        for kind in KINDS
        for row in store.find_work_item_rows(kind)
    }


def backlog_as_added(rows: Mapping[WorkItemId, WorkItemRow]) -> list[WorkItemId]:
    """The work items in Backlog in the order added; those added at one time as the rows list."""
    backlog = [item_id for item_id, row in rows.items() if row.state == BACKLOG]
    return sorted(backlog, key=lambda item_id: rows[item_id].created)


def _reached(row: WorkItemRow) -> datetime:
    """The time the work item reached its state: completed, else started, else added."""
    return row.completed or row.started or row.created


def _last_first(rows: Iterable[WorkItemRow], state: str) -> list[WorkItemRow]:
    """The work items in that state, the last to reach it first; those of one time as given."""
    return sorted((row for row in rows if row.state == state), key=_reached, reverse=True)


def _placed_feature(feature: FeatureState, under: Collection[WorkItemRow]) -> _PlacedFeature:
    """The row of the Feature over its work items, with the time that places it in its bucket.

    The row holds its started work items, the last started first. A completed Feature is placed
    by its own completed time and a removed one by its removed time. For any other the time is
    that of its last started work item; with none started that of its last completed one, as
    under Completed; with neither the time it was added, as in Backlog.
    """
    started = _last_first(under, STARTED)
    row = replace(feature_row(feature, [each.state for each in under]), started=started)
    match feature:
        case CompletedFeature():
            return feature.completed, row
        case RemovedFeature():
            return feature.removed, row
        case Feature() | StartedFeature() | BlockedFeature():
            reached = [_reached(each) for each in started or _last_first(under, COMPLETED)]
            return max(reached, default=feature.created), row
        case _ as unreachable:
            assert_never(unreachable)


def _placed_features(store: Store, rows: Collection[WorkItemRow]) -> list[_PlacedFeature]:
    """The Features of the record by number, each placed over the work items under it."""
    held = sorted(
        (parse_feature_id(text) for text in store.features.find_feature_ids()),
        key=lambda feature_id: feature_id.number,
    )
    return [
        _placed_feature(
            store.features.load_feature(feature_id),
            [row for row in rows if row.parent == feature_id_text(feature_id)],
        )
        for feature_id in held
    ]


def _with_features(
    rows: Iterable[WorkItemRow],
    features: Iterable[_PlacedFeature],
    bucket: str,
    *,
    last_first: bool,
) -> list[WorkItemRow | FeatureRow]:
    """The work items given and the Features of that bucket in one list, by the time of each.

    A work item is placed by the time it reached its state. Those of one time keep the order
    given, the work items before the Features.
    """
    placed: list[tuple[datetime, WorkItemRow | FeatureRow]] = [
        *((_reached(row), row) for row in rows),
        *((at, row) for at, row in features if row.bucket == bucket),
    ]
    return [row for _, row in sorted(placed, key=lambda each: each[0], reverse=last_first)]


def _backlog_lines(
    alone: Mapping[WorkItemId, WorkItemRow], features: Iterable[_PlacedFeature]
) -> dict[Placed, WorkItemRow | FeatureRow]:
    """The lines of the Backlog under the id of each, in the order added.

    They are the work items standing alone given that are in Backlog, and the Features in
    Backlog. Those added at one time keep the order given, the work items before the Features.
    """
    added: list[tuple[datetime, Placed, WorkItemRow | FeatureRow]] = [
        *((alone[item_id].created, item_id, alone[item_id]) for item_id in backlog_as_added(alone)),
        *((at, parse_feature_id(row.id), row) for at, row in features if row.bucket == "Backlog"),
    ]
    return {placed: row for _, placed, row in sorted(added, key=lambda each: each[0])}


def find_backlog(store: Store) -> list[Entry]:
    """The Backlog of the record as its queue places it, read anew.

    Its lines in the order added, then the work items in Backlog under a Feature in the order
    added, each inside its Feature: the Feature may have left the Backlog.
    """
    rows = rows_by_id(store)
    features = _placed_features(store, rows.values())
    alone = {item_id: row for item_id, row in rows.items() if not row.parent}
    under = {item_id: row for item_id, row in rows.items() if row.parent}
    inside = [
        Inside(item_id, parse_feature_id(under[item_id].parent))
        for item_id in backlog_as_added(under)
    ]
    return [*(Line(placed) for placed in _backlog_lines(alone, features)), *inside]


def status_item(store: Store, top: int | None = None) -> str:
    """The text of the work items standing alone and of the Features of the record, by bucket.

    A Feature is listed in its bucket in place of its work items: those in Backlog and
    the completed ones are on no line, the started ones under its own. The Backlog lists the
    work items and the Features placed in its queue, then the others as they were added;
    InProgress the last started first and Completed the last completed first, a Feature by its
    last work item to reach it, a completed one by its own completed time; Removed by kind and
    number, a work item of a Feature too, then the removed Features by number. A removed
    Feature is listed in place of its work items as any other: they were removed with it, or
    before it, and are on no line. Under a top each heading lists that many, the first ones.
    """
    rows = rows_by_id(store)
    features = _placed_features(store, rows.values())
    alone = {item_id: row for item_id, row in rows.items() if not row.parent}
    backlog = _backlog_lines(alone, features)
    started = [row for row in alone.values() if row.state == STARTED]
    completed = [row for row in alone.values() if row.state == COMPLETED]
    gone = [row for _, row in features if row.bucket == "Removed"]
    with_them = {row.id for row in gone}
    removed = [
        row
        for row in rows.values()
        if row.state not in (BACKLOG, STARTED, COMPLETED) and row.parent not in with_them
    ]
    listed = [
        *(backlog[placed] for placed in queued(store.load_queue(), backlog)),
        *_with_features(started, features, "InProgress", last_first=True),
        *_with_features(completed, features, "Completed", last_first=True),
        *removed,
        *gone,
    ]
    return status_text(listed, top)
