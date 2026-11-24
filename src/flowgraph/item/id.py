"""The id of an item of any kind: the text a command is given, read as the id of its kind."""

import re
from collections.abc import Callable
from functools import partial

from flowgraph.parent import FeatureId, FeatureIdError, parse_feature_id
from flowgraph.record.queue import Placed
from flowgraph.record.store import KINDS
from flowgraph.task import TaskId, TaskIdError, parse_task_id
from flowgraph.work_item import Kind, WorkItemId, WorkItemIdError, parse_work_item_id

# The id of an item of any kind.
ItemId = WorkItemId | TaskId


class ItemIdError(ValueError):
    """A text that is the id of no kind of item."""


def id_spelled(text: str) -> str:
    """The canonical id of a text that spells one, in any case, without its dash or zeros.

    A text is such a spelling when it is the prefix letter of a kind of work item, of a Feature or
    of a Task, an optional dash and a number of 1 or more; any other text, a number of 0 included,
    is given back unchanged, so each refusal keeps its wording.
    """
    prefixes = {*(kind.prefix for kind in KINDS), "F", "T"}
    spelled = re.fullmatch(r"([A-Za-z])-?(\d+)", text)
    if spelled is None or spelled[1].upper() not in prefixes or int(spelled[2]) < 1:
        return text
    return f"{spelled[1].upper()}-{int(spelled[2]):04d}"


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

    Raises ItemIdError naming every kind, the Task and the Feature when the text is none of them:
    fgraph start and complete, which read it, take a Feature too, read before it.
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
    raise ItemIdError(f"{text!r} is no {nouns}, Task or Feature id")


def parse_amended_id(text: str) -> WorkItemId:
    """The id of a work item of any kind, as fgraph amend and remove read the text.

    Raises ItemIdError naming every kind and the Feature when the text is none of them: amend and
    remove take a Feature too, read before it.
    """
    try:
        return parse_work_item_id_of_any_kind(text)
    except WorkItemIdError:
        nouns = ", ".join(kind.noun for kind in KINDS)
        raise ItemIdError(f"{text!r} is no {nouns} or Feature id") from None


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


def is_task_id(text: str) -> bool:
    """True when the text is written as the id of a Task: `T-` and a number.

    A number below 1 is written so too, so `T-0000` goes to the Task, whose parse refuses it.
    """
    return re.fullmatch(r"T-\d+", text) is not None


def parse_moved_id(text: str) -> ItemId | FeatureId:
    """The id of a Task, of a Feature or of a work item of any kind, as fgraph block reads it.

    Raises TaskIdError or FeatureIdError when the text is written as an id of that kind that is
    none, as `T-0000` or `F-0000`, and ItemIdError naming every kind when it is none of them.
    """
    if re.fullmatch(r"F-\d+", text) is not None:
        return parse_feature_id(text)
    if re.fullmatch(r"T-\d+", text) is not None:
        return parse_task_id(text)
    return parse_item_id(text)
