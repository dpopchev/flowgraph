"""The kind of a work item and its id: the prefix of the kind, `-` and its number among them."""

import re
from collections.abc import Collection
from dataclasses import dataclass

from flowgraph.criterion import Criterion, Scenario


@dataclass(frozen=True)
class Kind:
    """A kind of work item: its noun, the article before it, the prefix of its ids, and the
    form of criterion a work item of the kind takes."""

    noun: str
    article: str
    prefix: str
    takes: type[Criterion] = Scenario


@dataclass(frozen=True)
class WorkItemId:
    """The identity of a work item: its kind and its number among the items of that kind."""

    kind: Kind
    number: int

    def __str__(self) -> str:
        """The id as it is written, so a relation names it in a message."""
        return work_item_id_text(self)


class KindError(ValueError):
    """A kind of work item without a noun, or with a prefix that is not capital letters."""


class WorkItemIdError(ValueError):
    """A number or a text that is no id of the kind asked for."""


def make_kind(noun: str, article: str, prefix: str, takes: type[Criterion] = Scenario) -> Kind:
    """The kind of work item of that noun, written with that article and prefix.

    It takes a Given / When / Then unless another form of criterion is named. Raises KindError
    when the noun is blank or the prefix is not capital letters.
    """
    if not noun.strip():
        raise KindError("a kind names its noun")
    if re.fullmatch(r"[A-Z]+", prefix) is None:
        raise KindError(f"{prefix!r} is no prefix: it is capital letters")
    return Kind(noun, article, prefix, takes)


def make_work_item_id(kind: Kind, number: int) -> WorkItemId:
    """The id of the work item of that kind with that number in the record.

    Raises WorkItemIdError naming the kind when the number is below 1.
    """
    if number < 1:
        raise WorkItemIdError(f"{kind.article} {kind.noun} id counts from 1: {number} is below 1")
    return WorkItemId(kind, number)


def work_item_id_text(item_id: WorkItemId) -> str:
    """The id as it is written: the prefix of its kind, `-` and the number, four digits at least."""
    return f"{item_id.kind.prefix}-{item_id.number:04d}"


def parse_work_item_id(kind: Kind, text: str) -> WorkItemId:
    """The id of that kind written as the text.

    Raises WorkItemIdError when the text is not the prefix of the kind, `-` and a number.
    """
    written = re.fullmatch(rf"{kind.prefix}-(\d+)", text)
    if written is None:
        raise WorkItemIdError(f"{text!r} is no {kind.noun} id: it is {kind.prefix}- and a number")
    return make_work_item_id(kind, int(written.group(1)))


def next_work_item_id(kind: Kind, taken: Collection[WorkItemId]) -> WorkItemId:
    """The next free id of the kind: one above the highest taken, the first when none is."""
    return make_work_item_id(kind, max((item_id.number for item_id in taken), default=0) + 1)
