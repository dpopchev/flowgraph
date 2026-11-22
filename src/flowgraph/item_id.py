"""The id of an item of any kind: the text a command is given, read as the id of its kind."""

import re
from collections.abc import Callable
from functools import partial

from flowgraph.parent import FeatureId, FeatureIdError, parse_feature_id
from flowgraph.queue import Placed
from flowgraph.store import KINDS
from flowgraph.task import TaskId, TaskIdError, parse_task_id
from flowgraph.work_item import Kind, WorkItemId, WorkItemIdError, parse_work_item_id

# The id of an item of any kind.
ItemId = WorkItemId | TaskId


class ItemIdError(ValueError):
    """A text that is the id of no kind of item."""


def kind_named(name: str) -> Kind:
    """The kind whose noun, in lower case, is the name; raises KeyError when none is."""
    named = {kind.noun.lower(): kind for kind in KINDS}
    return named[name]


def parse_work_item_id_of_any_kind(text: str) -> WorkItemId:
    """The id of a work item of any kind written as the text.

    Raises WorkItemIdError naming every kind when the text is the id of none of them.
    """
    for kind in KINDS:
        try:
            return parse_work_item_id(kind, text)
        except WorkItemIdError:
            continue
    *nouns, last = (kind.noun for kind in KINDS)
    raise WorkItemIdError(f"{text!r} is no {', '.join(nouns)} or {last} id")


def parse_item_id(text: str) -> ItemId:
    """The id of a work item of any kind, or of a Task, written as the text.

    Raises ItemIdError when the text is none of them.
    """
    parsers: list[Callable[[str], ItemId]] = [
        *(partial(parse_work_item_id, kind) for kind in KINDS),
        parse_task_id,
    ]
    for parse in parsers:
        try:
            return parse(text)
        except WorkItemIdError, TaskIdError:
            continue
    nouns = ", ".join(kind.noun for kind in KINDS)
    raise ItemIdError(f"{text!r} is no {nouns} or Task id")


def parse_placed_id(text: str) -> Placed:
    """The id of a work item of any kind, or of a Feature, written as the text.

    They are what the queue of the Backlog places. Raises ItemIdError when the text is neither.
    """
    parsers: list[Callable[[str], Placed]] = [
        *(partial(parse_work_item_id, kind) for kind in KINDS),
        parse_feature_id,
    ]
    for parse in parsers:
        try:
            return parse(text)
        except WorkItemIdError, FeatureIdError:
            continue
    nouns = ", ".join(kind.noun for kind in KINDS)
    raise ItemIdError(f"{text!r} is no {nouns} or Feature id")


def parse_shown_id(text: str) -> Placed:
    """The id of a work item of any kind, or of a Feature, as fgraph show reads the text.

    Raises FeatureIdError when the text is written as a Feature id that is none, as `F-0000`, and
    ItemIdError naming every kind and the Feature when it is neither.
    """
    if re.fullmatch(r"F-\d+", text) is not None:
        return parse_feature_id(text)
    return parse_placed_id(text)


def parse_moved_id(text: str) -> TaskId | FeatureId:
    """The id of a Task, or of a Feature, as fgraph block and unblock read the text.

    Raises TaskIdError or FeatureIdError when the text is written as an id of that kind that is
    none, as `T-0000` or `F-0000`, and ItemIdError naming both kinds when it is neither.
    """
    if re.fullmatch(r"F-\d+", text) is not None:
        return parse_feature_id(text)
    if re.fullmatch(r"T-\d+", text) is not None:
        return parse_task_id(text)
    raise ItemIdError(f"{text!r} is no Task or Feature id")
