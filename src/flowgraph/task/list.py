"""The Tasks of one work item: the one of an id, one moved among them, at most one started."""

from collections.abc import Iterable
from datetime import datetime

from flowgraph.criterion import Evidence
from flowgraph.task.model import (
    CompletedTask,
    OpenTaskError,
    StartedTask,
    TaskId,
    TaskInProgressError,
    TaskNotFoundError,
    TaskState,
    blocked,
    completed,
    started,
    task_id_text,
    unblocked,
)


def task_of(tasks: Iterable[TaskState], task_id: TaskId) -> TaskState:
    """The Task of that id among the Tasks; raises TaskNotFoundError when none has it."""
    held = [task for task in tasks if task.id == task_id]
    if not held:
        raise TaskNotFoundError(task_id)
    return held[0]


def at_most_one_started(tasks: tuple[TaskState, ...]) -> tuple[TaskState, ...]:
    """The Tasks of one work item, at most one of them started; a blocked Task does not count.

    Raises TaskInProgressError naming the started Tasks when there are several.
    """
    begun = [task_id_text(task.id) for task in tasks if isinstance(task, StartedTask)]
    if len(begun) > 1:
        raise TaskInProgressError(f"more than one Task is started: {', '.join(begun)}")
    return tasks


def _none_started_beside(tasks: Iterable[TaskState], task_id: TaskId, move: str) -> None:
    """Raise TaskInProgressError naming a started Task other than the one that takes the move."""
    for task in tasks:
        if task.id != task_id and isinstance(task, StartedTask):
            beside = f"{task_id_text(task.id)} is started -- complete or block it first"
            raise TaskInProgressError(f"{task_id_text(task_id)} cannot {move}: {beside}")


def started_among(
    tasks: tuple[TaskState, ...], task_id: TaskId, on: datetime
) -> tuple[TaskState, ...]:
    """The Tasks with the one of that id started on that time, the rest as they are.

    Raises TaskNotFoundError when none has the id, the refusal of its start, or
    TaskInProgressError when another of the Tasks is started.
    """
    moved = started(task_of(tasks, task_id), on)
    _none_started_beside(tasks, task_id, "start")
    return tuple(moved if task.id == task_id else task for task in tasks)


def blocked_among(
    tasks: tuple[TaskState, ...], task_id: TaskId, reason: str, waiting_on: str, on: datetime
) -> tuple[TaskState, ...]:
    """The Tasks with the one of that id blocked on that time, the rest as they are.

    Raises TaskNotFoundError when none has the id, or the refusal of its block.
    """
    task_of(tasks, task_id)
    return tuple(
        blocked(task, reason, waiting_on, on) if task.id == task_id else task for task in tasks
    )


def unblocked_among(tasks: tuple[TaskState, ...], task_id: TaskId) -> tuple[TaskState, ...]:
    """The Tasks with the one of that id unblocked, the rest as they are.

    Raises TaskNotFoundError when none has the id, NotBlockedError when it is not blocked and
    TaskInProgressError when another of the Tasks is started.
    """
    moved = unblocked(task_of(tasks, task_id))
    _none_started_beside(tasks, task_id, "be unblocked")
    return tuple(moved if task.id == task_id else task for task in tasks)


def completed_among(
    tasks: tuple[TaskState, ...], task_id: TaskId, on: datetime, commit: Evidence
) -> tuple[TaskState, ...]:
    """The Tasks with the one of that id completed in that commit or none, the rest as they are.

    Raises TaskNotFoundError when none has the id, or the refusal of its complete.
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
