"""An Upkeep: work that keeps a behavior and changes the inside, kept in the record.

Its criterion is a Given / When / Then whose When already runs and whose Then says it still holds.
An Upkeep is added and listed; it holds no Task and does not move yet.
"""

import re
from collections.abc import Callable, Collection
from dataclasses import dataclass
from datetime import datetime

from flowgraph.story import EmptyPartError, Now, Scenario, make_scenario


@dataclass(frozen=True)
class UpkeepId:
    """The identity of an Upkeep: its number in the record, written `U-0001`."""

    number: int


@dataclass(frozen=True)
class Upkeep:
    """An Upkeep in Backlog: added, not yet started."""

    id: UpkeepId
    title: str
    scenario: Scenario
    description: str
    created: datetime


@dataclass
class UpkeepRow:
    """One Upkeep as plain data, as a view reads it from the record."""

    id: str
    title: str
    state: str
    commit: str = ""


# The rows of the upkeeps in the record; an empty list when it holds none.
FindUpkeepRows = Callable[[], list[UpkeepRow]]

# Save the Upkeep whole.
SaveUpkeep = Callable[[Upkeep], None]


class UpkeepIdError(ValueError):
    """A number or a text that is no Upkeep id."""


def make_upkeep_id(number: int) -> UpkeepId:
    """The id of the Upkeep with that number in the record.

    Raises UpkeepIdError when the number is below 1.
    """
    if number < 1:
        raise UpkeepIdError(f"an Upkeep id counts from 1: {number} is below 1")
    return UpkeepId(number)


def upkeep_id_text(upkeep_id: UpkeepId) -> str:
    """The id as it is written: `U-` and the number, at least four digits."""
    return f"U-{upkeep_id.number:04d}"


def parse_upkeep_id(text: str) -> UpkeepId:
    """The id written as the text.

    Raises UpkeepIdError when the text is not `U-` and a number.
    """
    written = re.fullmatch(r"U-(\d+)", text)
    if written is None:
        raise UpkeepIdError(f"{text!r} is no Upkeep id: it is U- and a number")
    return make_upkeep_id(int(written.group(1)))


def next_upkeep_id(taken: Collection[UpkeepId]) -> UpkeepId:
    """The next free id: one above the highest taken, the first when none is."""
    return make_upkeep_id(max((upkeep_id.number for upkeep_id in taken), default=0) + 1)


def make_upkeep(
    upkeep_id: UpkeepId, title: str, scenario: Scenario, description: str, created: datetime
) -> Upkeep:
    """An Upkeep in Backlog, its created time kept to the second.

    Raises EmptyPartError when the title is blank.
    """
    if not title.strip():
        raise EmptyPartError("title")
    return Upkeep(upkeep_id, title, scenario, description, created.replace(microsecond=0))


def add_upkeep(
    *,
    title: str,
    given: str,
    when: str,
    then: str,
    description: str,
    find_upkeep_rows: FindUpkeepRows,
    save_upkeep: SaveUpkeep,
    now: Now,
) -> UpkeepId:
    """Add an Upkeep to Backlog under the next free Upkeep id and return that id.

    Raises EmptyPartError when the title or a part of the criterion is blank; nothing is saved.
    """
    taken = [parse_upkeep_id(row.id) for row in find_upkeep_rows()]
    scenario = make_scenario(given, when, then)
    upkeep = make_upkeep(next_upkeep_id(taken), title, scenario, description, now())
    save_upkeep(upkeep)
    return upkeep.id
