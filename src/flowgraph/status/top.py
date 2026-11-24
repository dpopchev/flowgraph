"""The top of the Backlog: the id fgraph start takes when given none, the first that can start.

The decision of the developer of 2026-11-23 (S-0121): the rule is the one status counts
`can_start` by, read here and never written a second time; src/flowgraph/status/next.py holds it.
"""

from collections.abc import Sequence

from flowgraph.record.store import Store
from flowgraph.status.buckets import BACKLOG_BUCKET
from flowgraph.status.next import Line, StartLimit, start_now_ids
from flowgraph.status.text import BUCKETS, is_listed_in
from flowgraph.status.view import status_rows

# The message when no line is listed in the Backlog.
EMPTY = "nothing to start: the Backlog is empty"

# The message when the Backlog holds lines and none can start; {first} is its first line.
NONE_MARKED = (
    "nothing to start: no line of the Backlog can start now -- "
    "fgraph start {first} says why its first line cannot"
)


class NothingToStartError(Exception):
    """A start given no id while no line of the Backlog can start."""


def _in_backlog(row: Line) -> bool:
    """True when status lists the row in the Backlog."""
    states = next(states for name, states in BUCKETS if name == BACKLOG_BUCKET)
    return is_listed_in(row, BACKLOG_BUCKET, states)


def top_of(rows: Sequence[Line]) -> str:
    """The id of the first line that can start, of the rows status lists.

    Raises NothingToStartError with EMPTY or NONE_MARKED when none can start.
    """
    ids = start_now_ids(rows)
    if ids:
        return ids[0]
    backlog = [row for row in rows if _in_backlog(row)]
    if not backlog:
        raise NothingToStartError(EMPTY)
    raise NothingToStartError(NONE_MARKED.format(first=backlog[0].id))


def top_to_start(store: Store, limit: StartLimit) -> str:
    """The id of the top of the Backlog, read from the record under the limit of the development."""
    return top_of(status_rows(store, limit))
