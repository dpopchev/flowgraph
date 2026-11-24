"""The status of a record: its work items and its Features listed by bucket, read from its store.

A view: it reads the rows, the queue and the Features of the record and changes nothing. A
Feature is one item of its bucket, listed in place of its work items: a started one of
InProgress, a completed one of Completed, one never started of the bucket derived from its work
items.
"""

from collections.abc import Iterable, Mapping
from datetime import datetime

from flowgraph.feature import FeatureRow
from flowgraph.parent import parse_feature_id
from flowgraph.record.queue import Entry, Inside, Line, Placed, queued
from flowgraph.record.store import Store
from flowgraph.status.buckets import (
    BACKLOG_BUCKET,
    COMPLETED_BUCKET,
    IN_PROGRESS_BUCKET,
    REMOVED_BUCKET,
)
from flowgraph.status.document import JSON, chosen_format, status_json
from flowgraph.status.next import NEXT_ONLY, StartLimit, with_start_now
from flowgraph.status.placed import PlacedFeature, placed_features, waiting_features, with_features
from flowgraph.status.rows import BACKLOG, COMPLETED, backlog_as_added, rows_by_id
from flowgraph.status.text import cut_lines, status_text
from flowgraph.status.tops import same_top
from flowgraph.status.waits import with_waits
from flowgraph.work_item import IN_PROGRESS, WorkItemId, WorkItemRow


def _backlog_lines(
    alone: Mapping[WorkItemId, WorkItemRow], features: Iterable[PlacedFeature]
) -> dict[Placed, WorkItemRow | FeatureRow]:
    """The lines of the Backlog under the id of each, in the order added.

    They are the work items standing alone given that are in Backlog, and the Features in
    Backlog. Those added at one time keep the order given, the work items before the Features.
    """
    added: list[tuple[datetime, Placed, WorkItemRow | FeatureRow]] = [
        *((alone[item_id].created, item_id, alone[item_id]) for item_id in backlog_as_added(alone)),
        *(
            (at, parse_feature_id(row.id), row)
            for at, row in features
            if row.bucket == BACKLOG_BUCKET
        ),
    ]
    return {placed: row for _, placed, row in sorted(added, key=lambda each: each[0])}


def find_backlog(store: Store) -> list[Entry]:
    """The Backlog of the record as its queue places it, read anew.

    Its lines in the order added, then the work items in Backlog under a Feature in the order
    added, each inside its Feature: the Feature may have left the Backlog.
    """
    rows = rows_by_id(store)
    features = placed_features(store, rows.values())
    alone = {item_id: row for item_id, row in rows.items() if not row.parent}
    under = {item_id: row for item_id, row in rows.items() if row.parent}
    inside = [
        Inside(item_id, parse_feature_id(under[item_id].parent))
        for item_id in backlog_as_added(under)
    ]
    return [*(Line(placed) for placed in _backlog_lines(alone, features)), *inside]


def status_rows(store: Store, limit: StartLimit = NEXT_ONLY) -> list[WorkItemRow | FeatureRow]:
    """The work items standing alone and the Features of the record, in the order of the buckets.

    The plain data every format of status writes, each fact set on its row: what an item waits
    for, the next to start, the block of a Feature. A Feature is listed in its bucket in place of
    its work items: those in Backlog and the completed ones are on no line, the started ones
    under its own. The Backlog lists the work items and the Features placed in its queue, then
    the others as they were added; InProgress the last started first and Completed the last
    completed first, a Feature by its last work item to reach it, a completed one by its own
    completed time; Removed by kind and number, a work item of a Feature too, then the removed
    Features by number. A removed Feature is listed in place of its work items as any other:
    they are on no line: removed with it or before, or completed. A work item under a Feature
    the record does not hold, as a file edited by hand names, is listed as one standing alone,
    since no line of a Feature lists it.
    """
    rows = with_waits(rows_by_id(store))
    features = waiting_features(placed_features(store, rows.values()), rows, store)
    held = {row.id for _, row in features}
    alone = {item_id: row for item_id, row in rows.items() if row.parent not in held}
    backlog = _backlog_lines(alone, features)
    in_queue = queued(store.load_queue(), backlog)
    started = [row for row in alone.values() if row.state in IN_PROGRESS]
    completed = [row for row in alone.values() if row.state == COMPLETED]
    gone = [row for _, row in features if row.bucket == REMOVED_BUCKET]
    with_them = {row.id for row in gone}
    removed = [
        row
        for row in rows.values()
        if row.state not in (BACKLOG, *IN_PROGRESS, COMPLETED) and row.parent not in with_them
    ]
    taken = sum(row.state in IN_PROGRESS for row in rows.values())
    listed = [
        *(backlog[placed] for placed in in_queue),
        *with_features(started, features, IN_PROGRESS_BUCKET, last_first=True),
        *with_features(completed, features, COMPLETED_BUCKET, last_first=True),
        *removed,
        *gone,
    ]
    return with_start_now(listed, limit, taken)


def status_item(store: Store, top: int | None = None, limit: StartLimit = NEXT_ONLY) -> str:
    """The text of the work items standing alone and of the Features of the record, by bucket.

    Under a top each heading lists that many, the first ones; the rows are those of
    `status_rows` under the limit.
    """
    return status_text(status_rows(store, limit), same_top(top))


def status_output(
    store: Store, top: int | None, format_: str, width: int | None, limit: StartLimit
) -> str:
    """The status of the record in the format asked for: text cut to the width, or the document.

    The document lists every item, whatever the top, and is never cut. Raises StatusFormatError
    when the format is neither; the record is not read then.
    """
    if chosen_format(format_) == JSON:
        return status_json(status_rows(store, limit))
    return cut_lines(status_item(store, top, limit), width)
