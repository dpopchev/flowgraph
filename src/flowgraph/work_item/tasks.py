"""The moves of a Task inside its work item: only a started work item moves its Tasks."""

from dataclasses import replace
from datetime import datetime
from typing import assert_never

from flowgraph.criterion import Commit
from flowgraph.task import (
    CompletedAlreadyError,
    ItemInBacklogError,
    NotStartedError,
    TaskId,
    completed_among,
    started_among,
    task_id_text,
    task_of,
)
from flowgraph.work_item.model import (
    CompletedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemState,
    work_item_id_text,
)


def started_task(item: WorkItemState, task_id: TaskId, on: datetime) -> StartedWorkItem:
    """The started work item with its Task of that id started on that time, kept to the second.

    Raises TaskNotFoundError when the item holds no such Task, ItemInBacklogError when the item
    is in Backlog, StartedAlreadyError when the Task is started and CompletedAlreadyError when it
    is completed.
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
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{task} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def completed_task(
    item: WorkItemState, task_id: TaskId, on: datetime, commit: Commit
) -> StartedWorkItem:
    """The started work item with its Task of that id completed on that time, in that commit.

    Raises TaskNotFoundError when the item holds no such Task, NotStartedError when the Task is
    in Backlog and CompletedAlreadyError when it is completed.
    """
    task_of(item.tasks, task_id)
    task = task_id_text(task_id)
    match item:
        case WorkItem():
            raise NotStartedError(f"{task} is in Backlog: start it first")
        case StartedWorkItem():
            return replace(item, tasks=completed_among(item.tasks, task_id, on, commit))
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{task} is completed already")
        case _ as unreachable:
            assert_never(unreachable)
