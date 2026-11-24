"""The amend of a Task in Backlog, part by part: it is no move, the Task stays in Backlog."""

from dataclasses import dataclass
from typing import assert_never

from flowgraph.task.id import task_id_text
from flowgraph.task.model import (
    BlockedError,
    BlockedTask,
    CompletedAlreadyError,
    CompletedTask,
    RemovedTask,
    StartedAlreadyError,
    StartedTask,
    Task,
    TaskRemovedError,
    TaskState,
    make_task,
)


@dataclass(frozen=True)
class TaskAmendment:
    """The parts of a Task to rewrite, each None where it stays as it was."""

    title: str | None = None
    expected_output: str | None = None
    check: str | None = None
    description: str | None = None


def _given[T](part: T | None, was: T) -> T:
    """The part given, or the one the Task had."""
    return was if part is None else part


def amended(task: TaskState, amendment: TaskAmendment) -> Task:
    """The Task in Backlog rebuilt with the parts given, each other part as it was.

    A blank description clears it. Raises EmptyPartError when a title, an output or a check given
    is blank, StartedAlreadyError when the Task is started, BlockedError when it is blocked,
    CompletedAlreadyError when it is completed and TaskRemovedError when it is removed.
    """
    named = task_id_text(task.id)
    match task:
        case Task():
            description = _given(amendment.description, task.description)
            return make_task(
                task.id,
                _given(amendment.title, task.title),
                _given(amendment.expected_output, task.expected_output),
                description if description.strip() else "",
                task.created,
                _given(amendment.check, task.check),
            )
        case StartedTask():
            raise StartedAlreadyError(f"{named} is started already")
        case BlockedTask():
            raise BlockedError(f"{named} is blocked")
        case CompletedTask():
            raise CompletedAlreadyError(f"{named} is completed already")
        case RemovedTask():
            raise TaskRemovedError(f"{named} is removed already")
        case _ as unreachable:
            assert_never(unreachable)
