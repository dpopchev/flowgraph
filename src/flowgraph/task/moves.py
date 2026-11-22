"""The moves of a Task between its states: started, blocked and unblocked, then completed."""

from datetime import datetime
from typing import assert_never

from flowgraph.criterion import Evidence, said
from flowgraph.task.model import (
    BlockedError,
    BlockedTask,
    CompletedAlreadyError,
    CompletedTask,
    NotBlockedError,
    NotStartedError,
    StartedAlreadyError,
    StartedTask,
    Task,
    TaskState,
    task_id_text,
)


def started(task: TaskState, on: datetime) -> StartedTask:
    """The Task started on that time.

    Raises StartedAlreadyError when it is started, BlockedError when it is blocked and
    CompletedAlreadyError when it is completed.
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
        case BlockedTask():
            raise BlockedError(f"{task_id_text(task.id)} is blocked: unblock it first")
        case CompletedTask():
            raise CompletedAlreadyError(f"{task_id_text(task.id)} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def blocked(task: TaskState, reason: str, waiting_on: str, on: datetime) -> BlockedTask:
    """The started Task blocked on that time, kept to the second, for the reason given.

    Raises NotStartedError when it is in Backlog, BlockedError when it is blocked already,
    CompletedAlreadyError when it is completed and EmptyPartError when the reason or what it
    waits on is blank.
    """
    match task:
        case Task():
            raise NotStartedError(f"{task_id_text(task.id)} is in Backlog: start it first")
        case StartedTask():
            return BlockedTask(
                task.id,
                task.title,
                task.expected_output,
                task.description,
                task.created,
                task.started,
                said("reason", reason),
                on.replace(microsecond=0),
                said("waiting on", waiting_on),
            )
        case BlockedTask():
            raise BlockedError(f"{task_id_text(task.id)} is blocked already")
        case CompletedTask():
            raise CompletedAlreadyError(f"{task_id_text(task.id)} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def unblocked(task: TaskState) -> StartedTask:
    """The blocked Task started again, with the started time it had; its block is dropped.

    Raises NotBlockedError when it is in Backlog, started or completed.
    """
    match task:
        case BlockedTask():
            return StartedTask(
                task.id,
                task.title,
                task.expected_output,
                task.description,
                task.created,
                task.started,
            )
        case Task() | StartedTask() | CompletedTask():
            raise NotBlockedError(f"{task_id_text(task.id)} is not blocked")
        case _ as unreachable:
            assert_never(unreachable)


def completed(task: TaskState, on: datetime, commit: Evidence) -> CompletedTask:
    """The Task completed on that time in that commit, or without one.

    Raises NotStartedError when it is in Backlog, BlockedError when it is blocked and
    CompletedAlreadyError when it is completed.
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
        case BlockedTask():
            raise BlockedError(f"{task_id_text(task.id)} is blocked: unblock it first")
        case CompletedTask():
            raise CompletedAlreadyError(f"{task_id_text(task.id)} is completed already")
        case _ as unreachable:
            assert_never(unreachable)
