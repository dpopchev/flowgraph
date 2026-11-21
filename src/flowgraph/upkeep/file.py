"""The file of an Upkeep in the record: one TOML file per Upkeep, its Tasks inside it."""

import tomllib
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, assert_never

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from flowgraph.criterion import make_commit
from flowgraph.item_file import (
    CompletedTaskFile,
    CriterionFile,
    HeldTask,
    TaskFile,
    backlog_task,
    criterion_primitives,
    scenario_held,
    task_held,
    task_primitives,
    task_row,
    write_checked,
)
from flowgraph.record import ITEMS
from flowgraph.upkeep.model import (
    CompletedUpkeep,
    StartedUpkeep,
    Upkeep,
    UpkeepDetail,
    UpkeepFileError,
    UpkeepId,
    UpkeepMismatchError,
    UpkeepNotFoundError,
    UpkeepRow,
    UpkeepState,
    append_task,
    completed_upkeep,
    make_upkeep,
    parse_upkeep_id,
    started_upkeep,
    state_name,
    upkeep_id_text,
)

# The rows of the upkeeps in the record at the path; an empty list when it holds none.
ReadUpkeepRows = Callable[[Path], list[UpkeepRow]]

# The Upkeep of that id in the record at the path, whole; raises UpkeepNotFoundError when the
# record holds none.
ReadUpkeep = Callable[[Path, UpkeepId], UpkeepState]

# The Upkeep of that id in the record at the path, with its Tasks, as plain data; raises
# UpkeepNotFoundError when the record holds none.
ReadUpkeepDetail = Callable[[Path, UpkeepId], UpkeepDetail]

# The ids of every Task in the record at the path, as written; an empty list when it holds none.
ReadTaskIds = Callable[[Path], list[str]]

# Save the Upkeep whole into the record at the path.
WriteUpkeep = Callable[[Path, UpkeepState], None]


class _UpkeepFile(BaseModel):
    """What the file of an Upkeep in Backlog holds: its Tasks are all in Backlog."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["backlog"]
    title: str
    description: str = ""
    created: datetime
    criterion: CriterionFile
    tasks: list[TaskFile] = []


class _StartedUpkeepFile(BaseModel):
    """What the file of a started Upkeep holds: its started time, its Tasks in any state."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["started"]
    title: str
    description: str = ""
    created: datetime
    started: datetime
    criterion: CriterionFile
    tasks: list[HeldTask] = []


class _CompletedUpkeepFile(BaseModel):
    """What the file of a completed Upkeep holds: its commit, its Tasks all completed."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["completed"]
    title: str
    description: str = ""
    created: datetime
    started: datetime
    completed: datetime
    commit: str
    criterion: CriterionFile
    tasks: list[CompletedTaskFile] = []


# The file of an Upkeep in any of its states.
_HeldUpkeepFile = _UpkeepFile | _StartedUpkeepFile | _CompletedUpkeepFile

# The validator of an Upkeep file, which tells the states apart by the state line.
_HELD_STORY: TypeAdapter[_HeldUpkeepFile] = TypeAdapter(
    Annotated[_HeldUpkeepFile, Field(discriminator="state")]
)


def _commit_held(held: _HeldUpkeepFile) -> str:
    """The commit a validated file or table holds; empty for an item not completed."""
    match held:
        case _CompletedUpkeepFile():
            return held.commit
        case _UpkeepFile() | _StartedUpkeepFile():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def _read_upkeep_file(path: Path) -> _HeldUpkeepFile:
    """The content of one Upkeep file; raises UpkeepFileError naming the path."""
    try:
        return _HELD_STORY.validate_python(tomllib.loads(path.read_text(encoding="utf-8")))
    except (tomllib.TOMLDecodeError, ValidationError) as error:
        raise UpkeepFileError(f"{path} holds no Upkeep: {error}") from error


def read_upkeep_rows(record: Path) -> list[UpkeepRow]:
    """Adapter: the rows of the upkeeps in the record, by id.

    An Upkeep is a file of the items named `U-`; a file of another kind is left alone. Raises
    UpkeepFileError naming the first such file that does not hold an Upkeep.
    """
    held = [_read_upkeep_file(path) for path in (record / ITEMS).glob("U-*.toml")]
    rows = [
        UpkeepRow(upkeep.id, upkeep.title, upkeep.state, _commit_held(upkeep)) for upkeep in held
    ]
    return sorted(rows, key=lambda row: parse_upkeep_id(row.id).number)


def _held_path(record: Path, upkeep_id: UpkeepId) -> Path:
    """The file of the Upkeep of that id in the record; raises UpkeepNotFoundError without one."""
    path = record / ITEMS / f"{upkeep_id_text(upkeep_id)}.toml"
    if not path.is_file():
        raise UpkeepNotFoundError(upkeep_id)
    return path


def read_upkeep(record: Path, upkeep_id: UpkeepId) -> UpkeepState:
    """Adapter: the Upkeep of that id in the record, whole.

    Raises UpkeepNotFoundError when the record holds no such Upkeep and UpkeepFileError when its
    file does not hold one.
    """
    return _upkeep_held(_read_upkeep_file(_held_path(record, upkeep_id)))


def read_upkeep_detail(record: Path, upkeep_id: UpkeepId) -> UpkeepDetail:
    """Adapter: the Upkeep of that id in the record, with its Tasks, as plain data.

    Raises UpkeepNotFoundError when the record holds no such Upkeep and UpkeepFileError when its
    file does not hold one.
    """
    held = _read_upkeep_file(_held_path(record, upkeep_id))
    return UpkeepDetail(
        id=held.id,
        title=held.title,
        state=held.state,
        description=held.description,
        given=held.criterion.given,
        when=held.criterion.when,
        then=held.criterion.then,
        tasks=[task_row(task) for task in held.tasks],
        commit=_commit_held(held),
    )


def read_task_ids(record: Path) -> list[str]:
    """Adapter: the ids of every Task in the record, as written, in no order.

    Raises UpkeepFileError naming the first file of an Upkeep that does not hold one.
    """
    held = [_read_upkeep_file(path) for path in (record / ITEMS).glob("U-*.toml")]
    return [task.id for upkeep in held for task in upkeep.tasks]


def _moves_primitives(item: UpkeepState) -> dict[str, object]:
    """The times and the commit of the moves an item has made, as its file holds them."""
    match item:
        case Upkeep():
            return {}
        case StartedUpkeep():
            return {"started": item.started}
        case CompletedUpkeep():
            return {"started": item.started, "completed": item.completed, "commit": item.commit.sha}
        case _ as unreachable:
            assert_never(unreachable)


def _upkeep_primitives(upkeep: UpkeepState) -> dict[str, object]:
    """The Upkeep as the primitives its file holds; a description and tasks only when it has any."""
    described = {"description": upkeep.description} if upkeep.description else {}
    tasks = {"tasks": [task_primitives(task) for task in upkeep.tasks]} if upkeep.tasks else {}
    return {
        "id": upkeep_id_text(upkeep.id),
        "state": state_name(upkeep),
        "title": upkeep.title,
        **described,
        "created": upkeep.created,
        **_moves_primitives(upkeep),
        "criterion": criterion_primitives(upkeep.scenario),
        **tasks,
    }


def _upkeep_held(held: _HeldUpkeepFile) -> UpkeepState:
    """The Upkeep a validated file holds, with its Tasks, built through its constructors.

    An Upkeep and its Tasks past Backlog are built by the moves that took them there, so a file
    holds no state those moves could not reach.
    """
    scenario = scenario_held(held.criterion)
    upkeep = make_upkeep(
        parse_upkeep_id(held.id), held.title, scenario, held.description, held.created
    )
    for task in held.tasks:
        upkeep = append_task(upkeep, backlog_task(task))
    match held:
        case _UpkeepFile():
            return upkeep
        case _StartedUpkeepFile() | _CompletedUpkeepFile():
            tasks = tuple(task_held(task) for task in held.tasks)
            begun = replace(started_upkeep(upkeep, held.started), tasks=tasks)
            match held:
                case _CompletedUpkeepFile():
                    return completed_upkeep(begun, held.completed, make_commit(held.commit))
                case _StartedUpkeepFile():
                    return begun
                case _ as unreachable:
                    assert_never(unreachable)
        case _ as unreachable:
            assert_never(unreachable)


def write_upkeep(record: Path, upkeep: UpkeepState) -> None:
    """Adapter: write the Upkeep as its one file in the record.

    The Upkeep is written beside its file and read back before it replaces it. Raises
    UpkeepMismatchError naming the file when the Upkeep read back differs; the file is then as
    it was before.
    """
    path = record / ITEMS / f"{upkeep_id_text(upkeep.id)}.toml"
    write_checked(
        path,
        _upkeep_primitives(upkeep),
        lambda beside: _upkeep_held(_read_upkeep_file(beside)) == upkeep,
        UpkeepMismatchError(f"{path}: the Upkeep written reads back different"),
    )
