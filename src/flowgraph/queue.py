"""The Backlog queue: the order the developer gave the work items of the Backlog.

The queue places work items by id; a work item never placed follows the placed ones in the order
it was added, so the Backlog has an order before anyone gives one. It is kept as one file of the
record, `queue.toml`, apart from the files of the items it places.
"""

import tomllib
from collections.abc import Callable, Collection, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from flowgraph.item_file import write_checked
from flowgraph.work_item import (
    Kind,
    WorkItemId,
    WorkItemIdError,
    parse_work_item_id,
    work_item_id_text,
)

# The file of the queue inside a record.
QUEUE = "queue.toml"


@dataclass(frozen=True)
class Queue:
    """The work items the developer placed, in the order given, each once."""

    placed: tuple[WorkItemId, ...]


# The work items in Backlog, in the order they were added; an empty list when it holds none.
FindBacklog = Callable[[], list[WorkItemId]]

# The queue of the record, whole; the empty queue when no order was given yet.
LoadQueue = Callable[[], Queue]

# Save the queue whole.
SaveQueue = Callable[[Queue], None]


class QueueError(ValueError):
    """A queue that places one work item twice, or a text that is the id of no kind."""


class NotInBacklogError(Exception):
    """A work item named in a move of the queue that is not in Backlog."""

    def __init__(self, item_id: WorkItemId) -> None:
        super().__init__(f"{work_item_id_text(item_id)} is not in Backlog")


class SameItemError(Exception):
    """A work item put before itself."""

    def __init__(self, item_id: WorkItemId) -> None:
        super().__init__(f"{work_item_id_text(item_id)} cannot be put before itself")


class QueueFileError(Exception):
    """A queue file that does not hold a queue; names its path."""


class QueueMismatchError(Exception):
    """A queue read back different from the one written; its file is as it was before."""


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


def reorder(
    *,
    item: WorkItemId,
    before: WorkItemId,
    find_backlog: FindBacklog,
    load_queue: LoadQueue,
    save_queue: SaveQueue,
) -> None:
    """Put the work item right before the other in the queue of the Backlog.

    Raises NotInBacklogError when one of the two is not in Backlog and SameItemError when they
    are one work item; nothing is saved.
    """
    save_queue(moved_before(load_queue(), find_backlog(), item, before))


class _QueueFile(BaseModel):
    """What the queue file holds: the ids placed, as written, in their order."""

    model_config = ConfigDict(extra="forbid")

    backlog: list[str] = []


def _id_of_a_kind(text: str, kinds: Sequence[Kind]) -> WorkItemId:
    """The id of a work item of one of the kinds written as the text; raises QueueError."""
    for kind in kinds:
        try:
            return parse_work_item_id(kind, text)
        except WorkItemIdError:
            continue
    raise QueueError(f"{text!r} is no {' or '.join(kind.noun for kind in kinds)} id")


def _queue_held(content: str, kinds: Sequence[Kind]) -> Queue:
    """The queue the content of a queue file holds, built through its constructor.

    Raises tomllib.TOMLDecodeError, ValidationError or QueueError when it holds none.
    """
    held = _QueueFile.model_validate(tomllib.loads(content))
    return make_queue(_id_of_a_kind(text, kinds) for text in held.backlog)


def _read_file(path: Path, kinds: Sequence[Kind]) -> Queue:
    """The queue one file holds; raises QueueFileError naming it."""
    content = path.read_text(encoding="utf-8")
    try:
        return _queue_held(content, kinds)
    except (tomllib.TOMLDecodeError, ValidationError, QueueError) as error:
        raise QueueFileError(f"{path} holds no queue: {error}") from error


def read_queue(record: Path, kinds: Sequence[Kind]) -> Queue:
    """Adapter: the queue of the record, its ids those of the kinds given.

    A record without a queue file holds the empty queue. Raises QueueFileError naming the file
    when it does not hold a queue.
    """
    path = record / QUEUE
    return _read_file(path, kinds) if path.is_file() else make_queue([])


def write_queue(record: Path, kinds: Sequence[Kind], queue: Queue) -> None:
    """Adapter: write the queue as its one file in the record.

    The queue is written beside its file and read back before it replaces it. Raises
    QueueMismatchError naming the file when the queue read back differs; the file is then as it
    was before.
    """
    path = record / QUEUE
    write_checked(
        path,
        {"backlog": [work_item_id_text(item_id) for item_id in queue.placed]},
        lambda beside: _read_file(beside, kinds) == queue,
        QueueMismatchError(f"{path}: the queue written reads back different"),
    )
