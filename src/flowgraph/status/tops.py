"""How many items each bucket of status lists, the first ones: the flags of a command choose."""

from dataclasses import dataclass, replace

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

# What status lists with no flag: InProgress is listed whole, the developer's frame of
# 2026-11-23 (S-0132), each started item read with its hierarchy; the others keep their top.
SHORT = Tops(backlog=1, in_progress=None, completed=5, removed=5)


def tops_asked(*, every: bool, backlog: bool) -> Tops:
    """The tops a command asks for: every item when every, else short, the Backlog whole if so."""
    if every:
        return WHOLE
    return replace(SHORT, backlog=None) if backlog else SHORT


def top_of(tops: Tops, bucket: str) -> int | None:
    """The top of that bucket; a name that is no bucket raises KeyError."""
    by_bucket = {
        BACKLOG_BUCKET: tops.backlog,
        IN_PROGRESS_BUCKET: tops.in_progress,
        COMPLETED_BUCKET: tops.completed,
        REMOVED_BUCKET: tops.removed,
    }
    return by_bucket[bucket]
