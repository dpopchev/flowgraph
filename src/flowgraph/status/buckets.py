"""The buckets of the flow: their names, the states of the items listed in each, and the apart one.

A bucket lists a row by its state, a Feature by the bucket of its own row.
"""

from collections.abc import Collection, Sequence
from typing import assert_never

from flowgraph.feature import FeatureRow
from flowgraph.record.listing import Bucket, WatchShows
from flowgraph.work_item import WorkItemRow

BACKLOG_BUCKET = "Backlog"
IN_PROGRESS_BUCKET = "InProgress"
COMPLETED_BUCKET = "Completed"
REMOVED_BUCKET = "Removed"

# The buckets of the flow in their order, each with the states of an item shown in it.
BUCKETS: Sequence[tuple[str, Collection[str]]] = (
    (BACKLOG_BUCKET, frozenset({"backlog"})),
    (IN_PROGRESS_BUCKET, frozenset({"started", "blocked"})),
    (COMPLETED_BUCKET, frozenset({"completed"})),
    (REMOVED_BUCKET, frozenset({"removed"})),
)

# The name each bucket of the configuration is given here.
NAMED = {
    Bucket.BACKLOG: BACKLOG_BUCKET,
    Bucket.IN_PROGRESS: IN_PROGRESS_BUCKET,
    Bucket.COMPLETED: COMPLETED_BUCKET,
    Bucket.REMOVED: REMOVED_BUCKET,
}

# The bucket that stands apart from the flow: listed by status only when it holds an item.
APART = REMOVED_BUCKET


def is_listed_in(row: WorkItemRow | FeatureRow, bucket: str, states: Collection[str]) -> bool:
    """True when the bucket of those states lists the row: a Feature by the bucket of its row."""
    match row:
        case FeatureRow():
            return row.bucket == bucket
        case WorkItemRow():
            return row.state in states
        case _ as unreachable:
            assert_never(unreachable)


def shown_buckets(shows: WatchShows) -> frozenset[str]:
    """The names of the buckets a configuration shows."""
    return frozenset(NAMED[bucket] for bucket in shows.buckets)
