"""The Backlog queue: the order the developer gave the work items and the Features of the Backlog.

The queue places work items and Features by id; one never placed follows the placed ones in the
order it was added, so the Backlog has an order before anyone gives one. A work item under a
Feature is ordered among the work items of its Feature alone: the order they start in. The queue
is kept as one file of the record, `queue.toml`, apart from the files of the items it places.
"""

import tomllib
from collections.abc import Callable, Collection, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import assert_never

from pydantic import BaseModel, ConfigDict, ValidationError

from flowgraph.item_file import write_checked
from flowgraph.parent import (
    STANDALONE,
    FeatureId,
    FeatureIdError,
    Parent,
    feature_id_text,
    parse_feature_id,
)
from flowgraph.work_item import (
    Kind,
    WorkItemId,
    WorkItemIdError,
    parse_work_item_id,
    work_item_id_text,
)

# The file of the queue inside a record.
QUEUE = "queue.toml"

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


class QueueFileError(Exception):
    """A queue file that does not hold a queue; names its path."""


class QueueMismatchError(Exception):
    """A queue read back different from the one written; its file is as it was before."""


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


def _ordered_in(entry: Entry) -> Parent:
    """Where the entry is ordered: inside its Feature, or standing alone as a line."""
    match entry:
        case Line():
            return STANDALONE
        case Inside():
            return entry.feature
        case _ as unreachable:
            assert_never(unreachable)


def _check_ordered_together(item: Entry, before: Entry) -> None:
    """Check that the two are lines of the Backlog, or work items under one Feature.

    Raises UnderFeatureError naming the first of the two that is under a Feature, and it.
    """
    if _ordered_in(item) == _ordered_in(before):
        return
    for entry in (item, before):
        match entry:
            case Inside():
                raise UnderFeatureError(entry.id, entry.feature)
            case Line():
                continue
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


class _QueueFile(BaseModel):
    """What the queue file holds: the ids placed, as written, in their order."""

    model_config = ConfigDict(extra="forbid")

    backlog: list[str] = []


def _id_placed(text: str, kinds: Sequence[Kind]) -> Placed:
    """The id of a work item of one of the kinds, or of a Feature, written as the text.

    Raises QueueError when the text is neither.
    """
    for kind in kinds:
        try:
            return parse_work_item_id(kind, text)
        except WorkItemIdError:
            continue
    try:
        return parse_feature_id(text)
    except FeatureIdError:
        nouns = ", ".join(kind.noun for kind in kinds)
        raise QueueError(f"{text!r} is no {nouns} or Feature id") from None


def _queue_held(content: str, kinds: Sequence[Kind]) -> Queue:
    """The queue the content of a queue file holds, built through its constructor.

    Raises tomllib.TOMLDecodeError, ValidationError or QueueError when it holds none.
    """
    held = _QueueFile.model_validate(tomllib.loads(content))
    return make_queue(_id_placed(text, kinds) for text in held.backlog)


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
        {"backlog": [placed_text(placed) for placed in queue.placed]},
        lambda beside: _read_file(beside, kinds) == queue,
        QueueMismatchError(f"{path}: the queue written reads back different"),
    )
