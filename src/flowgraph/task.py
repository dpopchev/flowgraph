"""A Task: one deliverable of a work item, with its expected output, its moves and its commit."""

import re
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import assert_never

from flowgraph.criterion import Commit, said


@dataclass(frozen=True)
class TaskId:
    """The identity of a Task: its number in the record, written `T-0001`."""

    number: int


@dataclass(frozen=True)
class Task:
    """A Task in Backlog: written, not yet started."""

    id: TaskId
    title: str
    expected_output: str
    description: str
    created: datetime


@dataclass(frozen=True)
class StartedTask:
    """A Task in InProgress: started under its started Story, not yet completed."""

    id: TaskId
    title: str
    expected_output: str
    description: str
    created: datetime
    started: datetime


@dataclass(frozen=True)
class CompletedTask:
    """A Task in Completed: its work is in its commit."""

    id: TaskId
    title: str
    expected_output: str
    description: str
    created: datetime
    started: datetime
    completed: datetime
    commit: Commit


# A Task in any of its states, as the file of its Story keeps it.
TaskState = Task | StartedTask | CompletedTask


@dataclass
class TaskRow:
    """One Task as plain data, as a view reads it from the record; a commit once completed."""

    id: str
    title: str
    expected_output: str
    description: str
    state: str
    commit: str = ""


class TaskIdError(ValueError):
    """A number or a text that is no Task id."""


class TaskNotFoundError(Exception):
    """A Task id that no Story holds; `task_id` is that id."""

    def __init__(self, task_id: TaskId) -> None:
        super().__init__(f"no Task {task_id_text(task_id)} in the record")
        self.task_id = task_id


class StartedAlreadyError(ValueError):
    """A Story or a Task started once more."""


class CompletedAlreadyError(ValueError):
    """A completed Story or Task moved once more, or a Task written for a completed Story."""


class NotStartedError(ValueError):
    """A Story or a Task completed while it is still in Backlog."""


class NoTaskError(ValueError):
    """A work item started without a Task written for it."""


class ItemInBacklogError(ValueError):
    """A Task started while its work item is still in Backlog."""


class OpenTaskError(ValueError):
    """A work item completed while some of its Tasks are not."""


def make_task_id(number: int) -> TaskId:
    """The id of the Task with that number in the record.

    Raises TaskIdError when the number is below 1.
    """
    if number < 1:
        raise TaskIdError(f"a Task id counts from 1: {number} is below 1")
    return TaskId(number)


def task_id_text(task_id: TaskId) -> str:
    """The id as it is written: `T-` and the number, at least four digits."""
    return f"T-{task_id.number:04d}"


def parse_task_id(text: str) -> TaskId:
    """The id written as the text.

    Raises TaskIdError when the text is not `T-` and a number.
    """
    written = re.fullmatch(r"T-(\d+)", text)
    if written is None:
        raise TaskIdError(f"{text!r} is no Task id: it is T- and a number")
    return make_task_id(int(written.group(1)))


def next_task_id(taken: Collection[TaskId]) -> TaskId:
    """The next free id: one above the highest taken, the first when none is."""
    return make_task_id(max((task_id.number for task_id in taken), default=0) + 1)


def make_task(
    task_id: TaskId, title: str, expected_output: str, description: str, created: datetime
) -> Task:
    """A Task in Backlog, its created time kept to the second.

    Raises EmptyPartError when the title or the expected output is blank.
    """
    parts = said("title", title), said("output", expected_output)
    return Task(task_id, *parts, description, created.replace(microsecond=0))


def started(task: TaskState, on: datetime) -> StartedTask:
    """The Task started on that time.

    Raises StartedAlreadyError when it is started and CompletedAlreadyError when it is completed.
    """
    match task:
        case Task():
            return StartedTask(
                task.id,
                task.title,
                task.expected_output,
                task.description,
                task.created,
                on.replace(microsecond=0),
            )
        case StartedTask():
            raise StartedAlreadyError(f"{task_id_text(task.id)} is started already")
        case CompletedTask():
            raise CompletedAlreadyError(f"{task_id_text(task.id)} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def completed(task: TaskState, on: datetime, commit: Commit) -> CompletedTask:
    """The Task completed on that time in that commit.

    Raises NotStartedError when it is in Backlog and CompletedAlreadyError when it is completed.
    """
    match task:
        case Task():
            raise NotStartedError(f"{task_id_text(task.id)} is in Backlog: start it first")
        case StartedTask():
            return CompletedTask(
                task.id,
                task.title,
                task.expected_output,
                task.description,
                task.created,
                task.started,
                on.replace(microsecond=0),
                commit,
            )
        case CompletedTask():
            raise CompletedAlreadyError(f"{task_id_text(task.id)} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def task_of(tasks: Iterable[TaskState], task_id: TaskId) -> TaskState:
    """The Task of that id among the Tasks; raises TaskNotFoundError when none has it."""
    held = [task for task in tasks if task.id == task_id]
    if not held:
        raise TaskNotFoundError(task_id)
    return held[0]


def started_among(
    tasks: tuple[TaskState, ...], task_id: TaskId, on: datetime
) -> tuple[TaskState, ...]:
    """The Tasks with the one of that id started on that time, the rest as they are.

    Raises TaskNotFoundError when none has the id, StartedAlreadyError when it is started and
    CompletedAlreadyError when it is completed.
    """
    task_of(tasks, task_id)
    return tuple(started(task, on) if task.id == task_id else task for task in tasks)


def completed_among(
    tasks: tuple[TaskState, ...], task_id: TaskId, on: datetime, commit: Commit
) -> tuple[TaskState, ...]:
    """The Tasks with the one of that id completed in that commit, the rest as they are.

    Raises TaskNotFoundError when none has the id, NotStartedError when it is in Backlog and
    CompletedAlreadyError when it is completed.
    """
    task_of(tasks, task_id)
    return tuple(completed(task, on, commit) if task.id == task_id else task for task in tasks)


def all_completed(tasks: Iterable[TaskState], holder: str) -> tuple[CompletedTask, ...]:
    """The Tasks, every one of them completed.

    Raises OpenTaskError naming the holder and the Tasks not completed.
    """
    listed = list(tasks)
    done = tuple(task for task in listed if isinstance(task, CompletedTask))
    left = [task_id_text(task.id) for task in listed if not isinstance(task, CompletedTask)]
    if left:
        raise OpenTaskError(f"{holder} has Tasks to complete first: {', '.join(left)}")
    return done


def task_state_name(task: TaskState) -> str:
    """The state of the Task as the record writes it."""
    match task:
        case Task():
            return "backlog"
        case StartedTask():
            return "started"
        case CompletedTask():
            return "completed"
        case _ as unreachable:
            assert_never(unreachable)
