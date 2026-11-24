"""The Features of a record placed in their buckets, each over its work items, by its time."""

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
from flowgraph.record.queue import queued
from flowgraph.record.store import Store
from flowgraph.status.buckets import BACKLOG_BUCKET
from flowgraph.status.rows import COMPLETED, backlog_as_added
from flowgraph.status.under import in_show_order
from flowgraph.work_item import IN_PROGRESS, WorkItemId, WorkItemRow

# The row of a Feature with the time that places it in its bucket.
type PlacedFeature = tuple[datetime, FeatureRow]


def placed_features(store: Store, rows: Collection[WorkItemRow]) -> list[PlacedFeature]:
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


def waiting_features(
    features: Iterable[PlacedFeature], rows: Mapping[WorkItemId, WorkItemRow], store: Store
) -> list[PlacedFeature]:
    """The Features given, each carrying its work items and, in Backlog, what its first waits for.

    The first work item is the one its start takes: the first in the queue among those in Backlog.
    Its work items are every one under it, in the order `fgraph show` of it lists them.
    """
    queue = store.load_queue()
    waiting: list[PlacedFeature] = []
    for at, row in features:
        under = {item_id: each for item_id, each in rows.items() if each.parent == row.id}
        in_backlog = backlog_as_added(under)
        first = min(in_backlog, key=queued(queue, in_backlog).index, default=None)
        listed = first is not None and row.bucket == BACKLOG_BUCKET
        waits_for = under[first].waits_for if listed and first is not None else []
        work_items = in_show_order(under, in_backlog, queue)
        waiting.append((at, replace(row, waits_for=waits_for, work_items=work_items)))
    return waiting


def with_features(
    rows: Iterable[WorkItemRow],
    features: Iterable[PlacedFeature],
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


def _reached(row: WorkItemRow) -> datetime:
    """The time the work item reached its state: completed, else started, else added."""
    return row.completed or row.started or row.created


def _last_first(rows: Iterable[WorkItemRow], states: Collection[str]) -> list[WorkItemRow]:
    """The work items in those states, the last to reach one first; those of one time as given."""
    return sorted((row for row in rows if row.state in states), key=_reached, reverse=True)


def _placed_feature(feature: FeatureState, under: Collection[WorkItemRow]) -> PlacedFeature:
    """The row of the Feature over its work items, with the time that places it in its bucket.

    The row holds its started work items, the last started first. A completed Feature is placed
    by its own completed time and a removed one by its removed time. For any other the time is
    that of its last started work item; with none started that of its last completed one, as
    under Completed; with neither the time it was added, as in Backlog.
    """
    started = _last_first(under, IN_PROGRESS)
    row = replace(feature_row(feature, [each.state for each in under]), started=started)
    match feature:
        case CompletedFeature():
            return feature.completed, row
        case RemovedFeature():
            return feature.removed, row
        case Feature() | StartedFeature() | BlockedFeature():
            reached = [_reached(each) for each in started or _last_first(under, (COMPLETED,))]
            return max(reached, default=feature.created), row
        case _ as unreachable:
            assert_never(unreachable)
