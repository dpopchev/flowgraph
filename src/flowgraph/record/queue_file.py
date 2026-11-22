"""The file of the Backlog queue: `queue.toml` in the record, the ids placed in their order."""

import tomllib
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from flowgraph.item import write_checked
from flowgraph.parent import FeatureIdError, parse_feature_id
from flowgraph.record.queue import Placed, Queue, QueueError, make_queue, placed_text
from flowgraph.work_item import Kind, WorkItemIdError, parse_work_item_id

# The file of the queue inside a record.
QUEUE = "queue.toml"


class QueueFileError(Exception):
    """A queue file that does not hold a queue; names its path."""


class QueueMismatchError(Exception):
    """A queue read back different from the one written; its file is as it was before."""


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
