"""The moves of a Task inside its work item: only a started work item moves its Tasks.

No Task of a blocked work item moves: each move is refused naming the block.
"""

from dataclasses import replace
from datetime import datetime
from typing import assert_never

from flowgraph.criterion import Evidence
from flowgraph.task import (
    BlockedError,
    CompletedAlreadyError,
    ItemInBacklogError,
    NotBlockedError,
    NotStartedError,
    TaskId,
    blocked_among,
    completed_among,
    removed_among,
    started_among,
    task_id_text,
    task_of,
    unblocked_among,
)
from flowgraph.work_item.id import work_item_id_text
from flowgraph.work_item.model import (
    BlockedWorkItem,
    CompletedWorkItem,
    RemovedAlreadyError,
    RemovedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemState,
)


def _held(task: str, move: str, item: BlockedWorkItem) -> BlockedError:
    """The refusal of the move of a Task of a blocked work item, naming the block."""
    held = f"{work_item_id_text(item.id)} is blocked, waiting on {item.waiting_on}"
    return BlockedError(f"{task} {move}: {held}: unblock it first")


def started_task(item: WorkItemState, task_id: TaskId, on: datetime) -> StartedWorkItem:
    """The started work item with its Task of that id started on that time, kept to the second.

    Raises TaskNotFoundError when the item holds no such Task, ItemInBacklogError when the item
    is in Backlog, BlockedError when the item is blocked, StartedAlreadyError when the Task is
    started and CompletedAlreadyError when it is completed.
    """
    task_of(item.tasks, task_id)
    task = task_id_text(task_id)
    match item:
        case WorkItem():
            raise ItemInBacklogError(
                f"{task} cannot start: {work_item_id_text(item.id)} is in Backlog"
            )
        case StartedWorkItem():
            return replace(item, tasks=started_among(item.tasks, task_id, on))
        case BlockedWorkItem():
            raise _held(task, "cannot start", item)
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{task} is completed already")
        case RemovedWorkItem():
            raise RemovedAlreadyError(item.id)
        case _ as unreachable:
            assert_never(unreachable)


def blocked_task(
    item: WorkItemState, task_id: TaskId, reason: str, waiting_on: str, on: datetime
) -> StartedWorkItem:
    """The started work item with its started Task of that id blocked on that time.

    Raises TaskNotFoundError when the item holds no such Task, NotStartedError when the Task is
    in Backlog, BlockedError when it or its item is blocked already, CompletedAlreadyError when
    it is completed and EmptyPartError when the reason or what it waits on is blank.
    """
    task_of(item.tasks, task_id)
    task = task_id_text(task_id)
    match item:
        case WorkItem():
            raise NotStartedError(f"{task} is in Backlog: start it first")
        case StartedWorkItem():
            tasks = blocked_among(item.tasks, task_id, reason, waiting_on, on)
            return replace(item, tasks=tasks)
        case BlockedWorkItem():
            raise _held(task, "cannot be blocked", item)
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{task} is completed already")
        case RemovedWorkItem():
            raise RemovedAlreadyError(item.id)
        case _ as unreachable:
            assert_never(unreachable)


def unblocked_task(item: WorkItemState, task_id: TaskId) -> StartedWorkItem:
    """The started work item with its blocked Task of that id started again.

    Raises TaskNotFoundError when the item holds no such Task and NotBlockedError when the Task
    is not blocked, as in a work item in Backlog or completed, and BlockedError when the item is
    blocked.
    """
    task_of(item.tasks, task_id)
    match item:
        case StartedWorkItem():
            return replace(item, tasks=unblocked_among(item.tasks, task_id))
        case BlockedWorkItem():
            raise _held(task_id_text(task_id), "cannot be unblocked", item)
        case WorkItem() | CompletedWorkItem() | RemovedWorkItem():
            raise NotBlockedError(f"{task_id_text(task_id)} is not blocked")
        case _ as unreachable:
            assert_never(unreachable)


def removed_task(
    item: WorkItemState, task_id: TaskId, reason: str, on: datetime
) -> StartedWorkItem:
    """The started work item with its Task of that id removed on that time, for the reason.

    A Task in Backlog, started or blocked is removed. Raises TaskNotFoundError when the item
    holds no such Task, ItemInBacklogError when the item is in Backlog, BlockedError when it is
    blocked, CompletedAlreadyError when it or the Task is completed, RemovedAlreadyError when
    it is removed, TaskRemovedError when the Task is and EmptyPartError when the reason is blank.
    """
    task_of(item.tasks, task_id)
    task = task_id_text(task_id)
    named = work_item_id_text(item.id)
    match item:
        case WorkItem():
            raise ItemInBacklogError(f"{task} cannot be removed: {named} is in Backlog")
        case StartedWorkItem():
            return replace(item, tasks=removed_among(item.tasks, task_id, reason, on))
        case BlockedWorkItem():
            raise _held(task, "cannot be removed", item)
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{task} cannot be removed: {named} is completed already")
        case RemovedWorkItem():
            raise RemovedAlreadyError(item.id)
        case _ as unreachable:
            assert_never(unreachable)


def completed_task(
    item: WorkItemState, task_id: TaskId, on: datetime, commit: Evidence
) -> StartedWorkItem:
    """The started work item with its Task of that id completed on that time, in a commit or none.

    Raises TaskNotFoundError when the item holds no such Task, NotStartedError when the Task is
    in Backlog, BlockedError when the item is blocked and CompletedAlreadyError when it is
    completed.
    """
    task_of(item.tasks, task_id)
    task = task_id_text(task_id)
    match item:
        case WorkItem():
            raise NotStartedError(f"{task} is in Backlog: start it first")
        case StartedWorkItem():
            return replace(item, tasks=completed_among(item.tasks, task_id, on, commit))
        case BlockedWorkItem():
            raise _held(task, "cannot complete", item)
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{task} is completed already")
        case RemovedWorkItem():
            raise RemovedAlreadyError(item.id)
        case _ as unreachable:
            assert_never(unreachable)
