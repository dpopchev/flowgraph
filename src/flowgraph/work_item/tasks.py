"""The moves of a Task inside its work item: only a started work item moves its Tasks.

No Task of a blocked work item moves: each move is refused naming the block. The amend of a Task
in Backlog is here too, though it is no move: it takes the work items that take a new Task.
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
    Task,
    TaskAmendment,
    TaskId,
    TaskState,
    amended,
    blocked_among,
    completed_among,
    removed_among,
    started_among,
    task_id_text,
    task_of,
    unblocked_among,
)
from flowgraph.work_item.amend import NoPartError
from flowgraph.work_item.id import work_item_id_text
from flowgraph.work_item.model import (
    BlockedWorkItem,
    CompletedWorkItem,
    OpenWorkItem,
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


def _amended_named(task: TaskState, amendment: TaskAmendment) -> Task:
    """The Task amended, once its state has passed; NoPartError when the amendment is empty."""
    new = amended(task, amendment)
    if amendment == TaskAmendment():
        raise NoPartError(f"amend rewrites no part of {task_id_text(task.id)}: name one")
    return new


def amended_task(item: WorkItemState, task_id: TaskId, amendment: TaskAmendment) -> OpenWorkItem:
    """The work item with its Task in Backlog of that id amended, in the place it had.

    A work item in Backlog, started or blocked takes it, as it takes a new Task. Raises
    TaskNotFoundError when the item holds no such Task, the refusal of `amended` for a Task that
    is not in Backlog, CompletedAlreadyError when the item is completed, RemovedAlreadyError
    when it is removed and NoPartError when the amendment names no part.
    """
    task = task_of(item.tasks, task_id)
    named = task_id_text(task_id)
    match item:
        case WorkItem():
            new = _amended_named(task, amendment)
            return replace(item, tasks=tuple(new if t.id == task_id else t for t in item.tasks))
        case StartedWorkItem() | BlockedWorkItem():
            new = _amended_named(task, amendment)
            return replace(item, tasks=tuple(new if t.id == task_id else t for t in item.tasks))
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{named} is completed already")
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
