"""The Backlog queue: the order the developer gave the work items and the Features of the Backlog.

The queue places work items and Features by id; one never placed follows the placed ones in the
order it was added, so the Backlog has an order before anyone gives one. A work item under a
Feature is ordered among the work items of its Feature alone: the order they start in. The queue
is kept as one file of the record, `queue.toml`, apart from the files of the items it places
(`flowgraph.record.queue_file`).
"""

from collections.abc import Callable, Collection, Iterable, Sequence
from dataclasses import dataclass
from typing import assert_never

from flowgraph.parent import FeatureId, feature_id_text
from flowgraph.work_item import WorkItemId, work_item_id_text

# What the queue places: a work item or a Feature, named by its id.
Placed = WorkItemId | FeatureId


@dataclass(frozen=True)
class Queue:
    """The work items and the Features the developer placed, in the order given, each once."""

    placed: tuple[Placed, ...]


@dataclass(frozen=True)
class Line:
    """An item listed as a line of the Backlog: a work item standing alone, or a Feature."""

    id: Placed


@dataclass(frozen=True)
class Inside:
    """A work item in Backlog under a Feature: on no line, ordered among those of its Feature."""

    id: WorkItemId
    feature: FeatureId


# One item of the Backlog the queue places, with where it is ordered.
Entry = Line | Inside

# The Backlog as the queue places it, in the order added; an empty list when it holds nothing.
FindBacklog = Callable[[], list[Entry]]

# The queue of the record, whole; the empty queue when no order was given yet.
LoadQueue = Callable[[], Queue]

# Save the queue whole.
SaveQueue = Callable[[Queue], None]


def placed_text(placed: Placed) -> str:
    """The id of what the queue places, as it is written."""
    match placed:
        case WorkItemId():
            return work_item_id_text(placed)
        case FeatureId():
            return feature_id_text(placed)
        case _ as unreachable:
            assert_never(unreachable)


class QueueError(ValueError):
    """A queue that places one item twice, or a text that is the id of nothing it places."""


class NotInBacklogError(Exception):
    """A work item or a Feature named in a move of the queue that is not in Backlog."""

    def __init__(self, placed: Placed) -> None:
        super().__init__(f"{placed_text(placed)} is not in Backlog")


class SameItemError(Exception):
    """A work item or a Feature put before itself."""

    def __init__(self, placed: Placed) -> None:
        super().__init__(f"{placed_text(placed)} cannot be put before itself")


class UnderFeatureError(Exception):
    """A work item under a Feature and an item outside that Feature, one put before the other."""

    def __init__(self, item_id: WorkItemId, feature: FeatureId) -> None:
        named = feature_id_text(feature)
        among = f"it is reordered among the work items of {named} alone"
        super().__init__(f"{work_item_id_text(item_id)} is under {named}: {among}")


def make_queue(placed: Iterable[Placed]) -> Queue:
    """The queue placing those work items and Features in that order.

    Raises QueueError naming the first one placed twice.
    """
    seen: list[Placed] = []
    for each in placed:
        if each in seen:
            raise QueueError(f"{placed_text(each)} is placed twice")
        seen.append(each)
    return Queue(tuple(seen))


def queued(queue: Queue, added: Collection[Placed]) -> list[Placed]:
    """Those items of the Backlog in queue order, given in the order they were added.

    The placed ones still in Backlog come first, in the order given; the rest follow as added.
    Given the work items of one Feature, it is the order they start in.
    """
    placed = [each for each in queue.placed if each in added]
    return [*placed, *(each for each in added if each not in placed)]


def _check_ordered_together(item: Entry, before: Entry) -> None:
    """Check that the two are lines of the Backlog, or work items under one Feature.

    Raises UnderFeatureError naming the first of the two that is under a Feature, and it.
    """
    match item, before:
        case Line(), Line():
            return
        case Inside(feature=one), Inside(feature=other) if one == other:
            return
        case Inside(), _:
            raise UnderFeatureError(item.id, item.feature)
        case Line(), Inside():
            raise UnderFeatureError(before.id, before.feature)
        case _ as unreachable:
            assert_never(unreachable)


def moved_before(queue: Queue, added: Sequence[Entry], item: Placed, before: Placed) -> Queue:
    """The queue with the item put right before the other, placing the whole Backlog as listed.

    The one list holds the lines of the Backlog and the work items under the Features; the item
    alone changes place in it, so the order of the lines and the order inside each Feature are
    those it had, but for the item. Raises NotInBacklogError naming the first of the two that is
    not in Backlog, SameItemError when they are one item and UnderFeatureError when one is under
    a Feature the other is not under.
    """
    entries = {entry.id: entry for entry in added}
    for placed in (item, before):
        if placed not in entries:
            raise NotInBacklogError(placed)
    if item == before:
        raise SameItemError(item)
    _check_ordered_together(entries[item], entries[before])
    others = [placed for placed in queued(queue, list(entries)) if placed != item]
    at = others.index(before)
    return make_queue([*others[:at], item, *others[at:]])


def reorder(
    *,
    item: Placed,
    before: Placed,
    find_backlog: FindBacklog,
    load_queue: LoadQueue,
    save_queue: SaveQueue,
) -> None:
    """Put the work item or the Feature right before the other in the queue of the Backlog.

    Raises NotInBacklogError when one of the two is not in Backlog, SameItemError when they are
    one item and UnderFeatureError when one is under a Feature the other is not under; nothing
    is saved.
    """
    save_queue(moved_before(load_queue(), find_backlog(), item, before))
