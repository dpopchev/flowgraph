"""The Backlog queue: the order the developer gave the work items of the Backlog.

The queue places work items by id; a work item never placed follows the placed ones in the order
it was added, so the Backlog has an order before anyone gives one.
"""

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass

from flowgraph.work_item import WorkItemId, work_item_id_text


@dataclass(frozen=True)
class Queue:
    """The work items the developer placed, in the order given, each once."""

    placed: tuple[WorkItemId, ...]


class QueueError(ValueError):
    """A queue that places one work item twice."""


class NotInBacklogError(Exception):
    """A work item named in a move of the queue that is not in Backlog."""

    def __init__(self, item_id: WorkItemId) -> None:
        super().__init__(f"{work_item_id_text(item_id)} is not in Backlog")


class SameItemError(Exception):
    """A work item put before itself."""

    def __init__(self, item_id: WorkItemId) -> None:
        super().__init__(f"{work_item_id_text(item_id)} cannot be put before itself")


def make_queue(placed: Iterable[WorkItemId]) -> Queue:
    """The queue placing those work items in that order.

    Raises QueueError naming the first work item placed twice.
    """
    seen: list[WorkItemId] = []
    for item_id in placed:
        if item_id in seen:
            raise QueueError(f"{work_item_id_text(item_id)} is placed twice")
        seen.append(item_id)
    return Queue(tuple(seen))


def queued(queue: Queue, added: Collection[WorkItemId]) -> list[WorkItemId]:
    """The Backlog in queue order, given its work items in the order they were added.

    The placed items still in Backlog come first, in the order given; the rest follow as added.
    """
    placed = [item_id for item_id in queue.placed if item_id in added]
    return [*placed, *(item_id for item_id in added if item_id not in placed)]


def moved_before(
    queue: Queue, added: Sequence[WorkItemId], item: WorkItemId, before: WorkItemId
) -> Queue:
    """The queue with the item put right before the other, placing the whole Backlog as listed.

    Raises NotInBacklogError naming the first of the two that is not in Backlog and SameItemError
    when they are one work item.
    """
    for item_id in (item, before):
        if item_id not in added:
            raise NotInBacklogError(item_id)
    if item == before:
        raise SameItemError(item)
    others = [item_id for item_id in queued(queue, added) if item_id != item]
    at = others.index(before)
    return make_queue([*others[:at], item, *others[at:]])
