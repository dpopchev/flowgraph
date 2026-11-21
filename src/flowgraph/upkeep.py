"""An Upkeep: work that keeps a behavior and changes the inside, kept in the record.

Its criterion is a Given / When / Then whose When already runs and whose Then says it still holds.
An Upkeep is added and listed; it holds no Task and does not move yet.
"""

import re
import tomllib
from collections.abc import Callable, Collection
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from flowgraph.criterion import EmptyPartError, Scenario, make_scenario
from flowgraph.item_file import (
    CriterionFile,
    criterion_primitives,
    scenario_held,
    write_checked,
)
from flowgraph.record import ITEMS, Now


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


@dataclass
class UpkeepDetail:
    """One Upkeep with its criterion as plain data, as a view reads it whole."""

    id: str
    title: str
    state: str
    description: str
    given: str
    when: str
    then: str


# The rows of the upkeeps in the record; an empty list when it holds none.
FindUpkeepRows = Callable[[], list[UpkeepRow]]

# Save the Upkeep whole.
SaveUpkeep = Callable[[Upkeep], None]

# The rows of the upkeeps in the record at the path; an empty list when it holds none.
ReadUpkeepRows = Callable[[Path], list[UpkeepRow]]

# The Upkeep of that id in the record at the path as plain data; raises UpkeepNotFoundError when
# the record holds none.
ReadUpkeepDetail = Callable[[Path, UpkeepId], UpkeepDetail]

# Save the Upkeep whole into the record at the path.
WriteUpkeep = Callable[[Path, Upkeep], None]


class UpkeepIdError(ValueError):
    """A number or a text that is no Upkeep id."""


class UpkeepNotFoundError(Exception):
    """A record that holds no Upkeep of the id asked for; `upkeep_id` is that id."""

    def __init__(self, upkeep_id: UpkeepId) -> None:
        super().__init__(f"no Upkeep {upkeep_id_text(upkeep_id)} in the record")
        self.upkeep_id = upkeep_id


class UpkeepFileError(Exception):
    """A file named as an Upkeep in a record that does not hold one; names its path."""


class UpkeepMismatchError(Exception):
    """An Upkeep read back different from the one written; its file is as it was before."""


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


class _UpkeepFile(BaseModel):
    """What the file of an Upkeep in Backlog holds, validated as it is read."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["backlog"]
    title: str
    description: str = ""
    created: datetime
    criterion: CriterionFile


def _read_upkeep_file(path: Path) -> _UpkeepFile:
    """The content of one Upkeep file; raises UpkeepFileError naming the path."""
    try:
        return _UpkeepFile.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
    except (tomllib.TOMLDecodeError, ValidationError) as error:
        raise UpkeepFileError(f"{path} holds no Upkeep: {error}") from error


def _upkeep_path(record: Path, upkeep_id: UpkeepId) -> Path:
    """The path of the file of the Upkeep of that id in the record."""
    return record / ITEMS / f"{upkeep_id_text(upkeep_id)}.toml"


def read_upkeep_rows(record: Path) -> list[UpkeepRow]:
    """Adapter: the rows of the upkeeps in the record, by id.

    An Upkeep is a file of the items named `U-`; a file of another kind is left alone. Raises
    UpkeepFileError naming the first such file that does not hold an Upkeep.
    """
    held = [_read_upkeep_file(path) for path in (record / ITEMS).glob("U-*.toml")]
    rows = [UpkeepRow(upkeep.id, upkeep.title, upkeep.state) for upkeep in held]
    return sorted(rows, key=lambda row: parse_upkeep_id(row.id).number)


def read_upkeep_detail(record: Path, upkeep_id: UpkeepId) -> UpkeepDetail:
    """Adapter: the Upkeep of that id in the record, as plain data.

    Raises UpkeepNotFoundError when the record holds no such Upkeep and UpkeepFileError when its
    file does not hold one.
    """
    path = _upkeep_path(record, upkeep_id)
    if not path.is_file():
        raise UpkeepNotFoundError(upkeep_id)
    held = _read_upkeep_file(path)
    return UpkeepDetail(
        id=held.id,
        title=held.title,
        state=held.state,
        description=held.description,
        given=held.criterion.given,
        when=held.criterion.when,
        then=held.criterion.then,
    )


def _upkeep_primitives(upkeep: Upkeep) -> dict[str, object]:
    """The Upkeep as the primitives its file holds; a description only when there is one."""
    described = {"description": upkeep.description} if upkeep.description else {}
    return {
        "id": upkeep_id_text(upkeep.id),
        "state": "backlog",
        "title": upkeep.title,
        **described,
        "created": upkeep.created,
        "criterion": criterion_primitives(upkeep.scenario),
    }


def _upkeep_held(held: _UpkeepFile) -> Upkeep:
    """The Upkeep a validated file holds, built through its constructors."""
    scenario = scenario_held(held.criterion)
    return make_upkeep(
        parse_upkeep_id(held.id), held.title, scenario, held.description, held.created
    )


def write_upkeep(record: Path, upkeep: Upkeep) -> None:
    """Adapter: write the Upkeep as its one file in the record.

    The Upkeep is written beside its file and read back before it replaces it. Raises
    UpkeepMismatchError naming the file when the Upkeep read back differs; the file is then as it
    was before.
    """
    path = _upkeep_path(record, upkeep.id)
    write_checked(
        path,
        _upkeep_primitives(upkeep),
        lambda beside: _upkeep_held(_read_upkeep_file(beside)) == upkeep,
        UpkeepMismatchError(f"{path}: the Upkeep written reads back different"),
    )
