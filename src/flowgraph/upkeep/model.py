"""An Upkeep: work that keeps a behavior and changes the inside, its states and moves."""

import re
from collections.abc import Callable, Collection
from dataclasses import dataclass, replace
from datetime import datetime
from typing import assert_never

from flowgraph.criterion import Commit, Scenario, said
from flowgraph.task import (
    CompletedAlreadyError,
    CompletedTask,
    ItemInBacklogError,
    NoTaskError,
    NotStartedError,
    StartedAlreadyError,
    StartedTask,
    Task,
    TaskId,
    TaskRow,
    TaskState,
    all_completed,
    completed_among,
    started_among,
    task_id_text,
    task_of,
)


@dataclass(frozen=True)
class UpkeepId:
    """The identity of an Upkeep: its number in the record, written `U-0001`."""

    number: int


@dataclass(frozen=True)
class Upkeep:
    """An Upkeep in Backlog: added, not yet started, with the Tasks written for it so far."""

    id: UpkeepId
    title: str
    scenario: Scenario
    description: str
    created: datetime
    tasks: tuple[Task, ...]


@dataclass(frozen=True)
class StartedUpkeep:
    """An Upkeep in InProgress: started with at least one Task, each in any state of its own."""

    id: UpkeepId
    title: str
    scenario: Scenario
    description: str
    created: datetime
    started: datetime
    tasks: tuple[TaskState, ...]


@dataclass(frozen=True)
class CompletedUpkeep:
    """An Upkeep in Completed: every Task of it completed, the Upkeep in its commit on `main`."""

    id: UpkeepId
    title: str
    scenario: Scenario
    description: str
    created: datetime
    started: datetime
    completed: datetime
    commit: Commit
    tasks: tuple[CompletedTask, ...]


# An Upkeep that still takes Tasks: in Backlog or started.
OpenUpkeep = Upkeep | StartedUpkeep

# An Upkeep in any of its states, as the record keeps it.
UpkeepState = Upkeep | StartedUpkeep | CompletedUpkeep


@dataclass
class UpkeepRow:
    """One Upkeep as plain data, as a view reads it from the record; a commit once completed."""

    id: str
    title: str
    state: str
    commit: str = ""


@dataclass
class UpkeepDetail:
    """One Upkeep with its criterion and its Tasks as plain data, as a view reads it whole."""

    id: str
    title: str
    state: str
    description: str
    given: str
    when: str
    then: str
    tasks: list[TaskRow]
    commit: str = ""


# The rows of the upkeeps in the record; an empty list when it holds none.
FindUpkeepRows = Callable[[], list[UpkeepRow]]

# The ids of every Task in the record, as written; an empty list when it holds none.
FindTaskIds = Callable[[], list[str]]

# The Upkeep of that id, whole; raises UpkeepNotFoundError when the record holds none.
LoadUpkeep = Callable[[UpkeepId], UpkeepState]

# Save the Upkeep whole.
SaveUpkeep = Callable[[UpkeepState], None]


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
    to_the_second = created.replace(microsecond=0)
    return Upkeep(upkeep_id, said("title", title), scenario, description, to_the_second, ())


def append_task[S: OpenUpkeep](upkeep: S, task: Task) -> S:
    """The Upkeep with the Task written for it, after the Tasks it already has."""
    return replace(upkeep, tasks=(*upkeep.tasks, task))


def still_open(upkeep: UpkeepState) -> OpenUpkeep:
    """The Upkeep, which still takes Tasks; raises CompletedAlreadyError when it is completed."""
    match upkeep:
        case Upkeep() | StartedUpkeep():
            return upkeep
        case CompletedUpkeep():
            raise CompletedAlreadyError(f"{upkeep_id_text(upkeep.id)} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def started_upkeep(upkeep: UpkeepState, on: datetime) -> StartedUpkeep:
    """The Upkeep started on that time, kept to the second, its Tasks still in Backlog.

    Raises NoTaskError when the Upkeep has no Task, StartedAlreadyError when it is started and
    CompletedAlreadyError when it is completed.
    """
    match upkeep:
        case Upkeep(tasks=()):
            raise NoTaskError(f"{upkeep_id_text(upkeep.id)} has no Task to start with")
        case Upkeep():
            to_the_second = on.replace(microsecond=0)
            return StartedUpkeep(
                upkeep.id,
                upkeep.title,
                upkeep.scenario,
                upkeep.description,
                upkeep.created,
                to_the_second,
                upkeep.tasks,
            )
        case StartedUpkeep():
            raise StartedAlreadyError(f"{upkeep_id_text(upkeep.id)} is started already")
        case CompletedUpkeep():
            raise CompletedAlreadyError(f"{upkeep_id_text(upkeep.id)} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def started_task(upkeep: UpkeepState, task_id: TaskId, on: datetime) -> StartedUpkeep:
    """The started Upkeep with its Task of that id started on that time, kept to the second.

    Raises TaskNotFoundError when the Upkeep holds no such Task, ItemInBacklogError when the
    Upkeep is in Backlog, StartedAlreadyError when the Task is started and CompletedAlreadyError
    when it is completed.
    """
    task_of(upkeep.tasks, task_id)
    task = task_id_text(task_id)
    match upkeep:
        case Upkeep():
            raise ItemInBacklogError(
                f"{task} cannot start: {upkeep_id_text(upkeep.id)} is in Backlog"
            )
        case StartedUpkeep():
            return replace(upkeep, tasks=started_among(upkeep.tasks, task_id, on))
        case CompletedUpkeep():
            raise CompletedAlreadyError(f"{task} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def completed_task(
    upkeep: UpkeepState, task_id: TaskId, on: datetime, commit: Commit
) -> StartedUpkeep:
    """The started Upkeep with its Task of that id completed on that time, in that commit.

    Raises TaskNotFoundError when the Upkeep holds no such Task, NotStartedError when the Task is
    in Backlog and CompletedAlreadyError when it is completed.
    """
    task_of(upkeep.tasks, task_id)
    task = task_id_text(task_id)
    match upkeep:
        case Upkeep():
            raise NotStartedError(f"{task} is in Backlog: start it first")
        case StartedUpkeep():
            return replace(upkeep, tasks=completed_among(upkeep.tasks, task_id, on, commit))
        case CompletedUpkeep():
            raise CompletedAlreadyError(f"{task} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def completed_upkeep(upkeep: UpkeepState, on: datetime, commit: Commit) -> CompletedUpkeep:
    """The Upkeep completed on that time, kept to the second, in that commit.

    Raises NotStartedError when it is in Backlog, OpenTaskError naming the Tasks not completed,
    and CompletedAlreadyError when it is completed.
    """
    match upkeep:
        case Upkeep():
            raise NotStartedError(f"{upkeep_id_text(upkeep.id)} is in Backlog: start it first")
        case StartedUpkeep():
            done = all_completed(upkeep.tasks, upkeep_id_text(upkeep.id))
            return CompletedUpkeep(
                upkeep.id,
                upkeep.title,
                upkeep.scenario,
                upkeep.description,
                upkeep.created,
                upkeep.started,
                on.replace(microsecond=0),
                commit,
                done,
            )
        case CompletedUpkeep():
            raise CompletedAlreadyError(f"{upkeep_id_text(upkeep.id)} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def state_name(item: UpkeepState | TaskState) -> str:
    """The state of an Upkeep or a Task as the record writes it."""
    match item:
        case Upkeep() | Task():
            return "backlog"
        case StartedUpkeep() | StartedTask():
            return "started"
        case CompletedUpkeep() | CompletedTask():
            return "completed"
        case _ as unreachable:
            assert_never(unreachable)


def commit_sha(item: UpkeepState | TaskState) -> str:
    """The sha of the commit of a completed Upkeep or Task; empty for one not completed."""
    match item:
        case CompletedUpkeep() | CompletedTask():
            return item.commit.sha
        case Upkeep() | Task() | StartedUpkeep() | StartedTask():
            return ""
        case _ as unreachable:
            assert_never(unreachable)
