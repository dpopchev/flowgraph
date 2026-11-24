"""How many items each bucket of status lists, the first ones: the flags of a command choose."""

from dataclasses import dataclass, replace
from typing import assert_never

from flowgraph.record.listing import AllLines, Lines, Listed, StatusLists
from flowgraph.status.buckets import (
    BACKLOG_BUCKET,
    COMPLETED_BUCKET,
    IN_PROGRESS_BUCKET,
    REMOVED_BUCKET,
)


@dataclass(frozen=True)
class Tops:
    """The top of each bucket in the order of the flow; None lists every item of it."""

    backlog: int | None
    in_progress: int | None
    completed: int | None
    removed: int | None


def same_top(top: int | None) -> Tops:
    """That top for every bucket."""
    return Tops(top, top, top, top)


WHOLE = same_top(None)


def _top(listed: Listed) -> int | None:
    """The count the lines hold; None for every line."""
    match listed:
        case Lines(count):
            return count
        case AllLines():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def tops_of(lists: StatusLists) -> Tops:
    """The tops a configuration sets: the count of lines of each bucket, None for every line."""
    return Tops(
        _top(lists.backlog), _top(lists.in_progress), _top(lists.completed), _top(lists.removed)
    )


def tops_asked(configured: Tops, *, every: bool, backlog: bool) -> Tops:
    """The tops a command asks for: every item when every, else those the configuration sets.

    The Backlog is listed whole when backlog is set. A flag of a command wins over a key of the
    configuration for that run (the Decision of 2026-11-23 on S-0136).
    """
    if every:
        return WHOLE
    return replace(configured, backlog=None) if backlog else configured


def top_of(tops: Tops, bucket: str) -> int | None:
    """The top of that bucket; a name that is no bucket raises KeyError."""
    by_bucket = {
        BACKLOG_BUCKET: tops.backlog,
        IN_PROGRESS_BUCKET: tops.in_progress,
        COMPLETED_BUCKET: tops.completed,
        REMOVED_BUCKET: tops.removed,
    }
    return by_bucket[bucket]
