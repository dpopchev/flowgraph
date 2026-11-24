"""A Task: one deliverable of a work item, with its expected output, its states and its commit.

The moves between its states are in flowgraph.task.moves.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import assert_never

from flowgraph.criterion import Evidence, evidence_text, said
from flowgraph.task.id import TaskId, task_id_text


@dataclass(frozen=True)
class Task:
    """A Task in Backlog: written, not yet started."""

    id: TaskId
    title: str
    expected_output: str
    description: str
    created: datetime
    check: str | None = None


@dataclass(frozen=True)
class StartedTask:
    """A Task in InProgress: started under its started Story, not yet completed."""

    id: TaskId
    title: str
    expected_output: str
    description: str
    created: datetime
    started: datetime
    check: str | None = None


@dataclass(frozen=True)
class BlockedTask:
    """A Task in InProgress that cannot go on: its reason, since when, and what it waits on."""

    id: TaskId
    title: str
    expected_output: str
    description: str
    created: datetime
    started: datetime
    reason: str
    since: datetime
    waiting_on: str
    check: str | None = None


@dataclass(frozen=True)
class CompletedTask:
    """A Task in Completed: its work is in its commit, or it is completed without one."""

    id: TaskId
    title: str
    expected_output: str
    description: str
    created: datetime
    started: datetime
    completed: datetime
    commit: Evidence
    check: str | None = None


@dataclass(frozen=True)
class RemovedTask:
    """A Task in Removed: taken out of its started work item, with the reason it was."""

    id: TaskId
    title: str
    expected_output: str
    description: str
    created: datetime
    removed: datetime
    reason: str
    check: str | None = None


# A Task in any of its states, as the file of its Story keeps it.
TaskState = Task | StartedTask | BlockedTask | CompletedTask | RemovedTask


@dataclass
class TaskRow:
    """One Task as plain data, as a view reads it from the record.

    A commit once completed in one; a reason and what it waits on while blocked, a reason once
    removed too.
    """

    id: str
    title: str
    expected_output: str
    description: str
    state: str
    commit: str = ""
    reason: str = ""
    waiting_on: str = ""
    check: str = ""


class TaskNotFoundError(Exception):
    """A Task id that no Story holds; `task_id` is that id."""

    def __init__(self, task_id: TaskId) -> None:
        super().__init__(f"no Task {task_id_text(task_id)} in the record")
        self.task_id = task_id


class StartedAlreadyError(ValueError):
    """A Story or a Task started once more."""


class BlockedError(ValueError):
    """A blocked Task moved before it is unblocked, or blocked once more."""


class NotBlockedError(ValueError):
    """A Task unblocked while it is not blocked."""


class TaskInProgressError(ValueError):
    """A second Task of one work item started: a work item holds at most one started Task."""


class CompletedAlreadyError(ValueError):
    """A completed Story or Task moved once more, or a Task written for a completed Story."""


class TaskRemovedError(ValueError):
    """A removed Task moved once more."""


class NotStartedError(ValueError):
    """A Story or a Task completed, or a Task blocked, while it is still in Backlog."""


class NoTaskError(ValueError):
    """A work item started without a Task written for it."""


class ItemInBacklogError(ValueError):
    """A Task started while its work item is still in Backlog."""


class OpenTaskError(ValueError):
    """A work item completed while some of its Tasks are not."""


def make_task(
    task_id: TaskId,
    title: str,
    expected_output: str,
    description: str,
    created: datetime,
    check: str | None = None,
) -> Task:
    """A Task in Backlog, its created time kept to the second, with the command that checks it.

    Raises EmptyPartError when the title or the expected output is blank, or the check is given
    and blank.
    """
    parts = said("title", title), said("output", expected_output)
    kept = None if check is None else said("check", check)
    return Task(task_id, *parts, description, created.replace(microsecond=0), kept)


def task_state_name(task: TaskState) -> str:
    """The state of the Task as the record writes it."""
    match task:
        case Task():
            return "backlog"
        case StartedTask():
            return "started"
        case BlockedTask():
            return "blocked"
        case CompletedTask():
            return "completed"
        case RemovedTask():
            return "removed"
        case _ as unreachable:
            assert_never(unreachable)


def row_of(task: TaskState) -> TaskRow:
    """The Task as the row a view reads: its commit once completed, its block while blocked.

    A Task completed without a commit reads with none; a removed one reads with its reason.
    """
    row = TaskRow(
        task_id_text(task.id),
        task.title,
        task.expected_output,
        task.description,
        task_state_name(task),
        check=task.check or "",
    )
    match task:
        case Task() | StartedTask():
            return row
        case BlockedTask():
            row.reason, row.waiting_on = task.reason, task.waiting_on
            return row
        case CompletedTask():
            row.commit = evidence_text(task.commit)
            return row
        case RemovedTask():
            row.reason = task.reason
            return row
        case _ as unreachable:
            assert_never(unreachable)
