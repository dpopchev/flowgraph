"""The work items under a Feature in the order `fgraph show` of it lists them.

Plain data read from the rows of the record, kept in one place for every view that lists them.
"""

from collections.abc import Mapping, Sequence

from flowgraph.record.queue import Queue, queued
from flowgraph.work_item import WorkItemId, WorkItemRow

# The state of a row in Backlog, as the record writes it.
_BACKLOG = "backlog"


def in_show_order(
    held: Mapping[WorkItemId, WorkItemRow], in_backlog: Sequence[WorkItemId], queue: Queue
) -> list[WorkItemRow]:
    """The rows held by kind and number, those in Backlog among them in the order the queue gives.

    The work items in Backlog take the places of the rows in Backlog in the order their start
    takes them: the first in the queue first. In Backlog are those given.
    """
    start_order = queued(queue, in_backlog)
    next_started = iter(sorted(in_backlog, key=start_order.index))
    return [held[next(next_started)] if row.state == _BACKLOG else row for row in held.values()]
