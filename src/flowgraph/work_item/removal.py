"""The removal of a work item: it drops out of Backlog or of InProgress with its reason.

Removed stands apart from the flow: nothing is deleted, and a removed work item takes no move.
One in Backlog is kept whole; a started or a blocked one keeps its completed Tasks, and its other
Tasks are removed with it (S-0148).
"""

from collections.abc import Iterable
from datetime import datetime
from typing import assert_never

from flowgraph.criterion import said
from flowgraph.relation import RelationError
from flowgraph.task import (
    BlockedTask,
    CompletedAlreadyError,
    CompletedTask,
    RemovedTask,
    StartedTask,
    Task,
    TaskState,
    removed,
)
from flowgraph.work_item.id import WorkItemId, work_item_id_text
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


def _reason_kept(reason: str, superseded_by: WorkItemId | None) -> str:
    """The reason as kept: it says something, unless a work item supersedes the removed one."""
    return said("reason", reason) if superseded_by is None else reason.strip()


def _superseded_by_kept(item: WorkItemId, superseded_by: WorkItemId | None) -> WorkItemId | None:
    """The work item that supersedes the item; raises RelationError when it is the item itself."""
    if superseded_by == item:
        raise RelationError(f"{work_item_id_text(item)} cannot be superseded by itself")
    return superseded_by


def _removed_with(
    tasks: Iterable[TaskState], why: str, on: datetime
) -> tuple[CompletedTask | RemovedTask, ...]:
    """The Tasks of a started work item removed: each completed or removed one as it is, every
    other one removed on that time for that reason."""
    kept: list[CompletedTask | RemovedTask] = []
    for task in tasks:
        match task:
            case CompletedTask() | RemovedTask():
                kept.append(task)
            case Task() | StartedTask() | BlockedTask():
                kept.append(removed(task, why, on))
            case _ as unreachable:
                assert_never(unreachable)
    return tuple(kept)


def _why(reason: str, superseded_by: WorkItemId | None) -> str:
    """The reason the open Tasks go for: that of the work item, else what supersedes it."""
    if reason or superseded_by is None:
        return reason
    return f"superseded by {work_item_id_text(superseded_by)}"


def _gone(
    item: OpenWorkItem, reason: str, on: datetime, superseded_by: WorkItemId | None
) -> RemovedWorkItem:
    """The open work item removed, its reason and what supersedes it checked before its Tasks."""
    kept = _reason_kept(reason, superseded_by)
    by = _superseded_by_kept(item.id, superseded_by)
    match item:
        case WorkItem():
            tasks: tuple[Task | CompletedTask | RemovedTask, ...] = item.tasks
        case StartedWorkItem() | BlockedWorkItem():
            tasks = _removed_with(item.tasks, _why(kept, by), on)
        case _ as unreachable:
            assert_never(unreachable)
    return RemovedWorkItem(
        item.id,
        item.title,
        item.criterion,
        item.description,
        item.created,
        on.replace(microsecond=0),
        kept,
        tasks,
        item.parent,
        item.complexity,
        item.knowledge,
        item.relations,
        by,
        item.about,
        realizes=item.realizes,
        progress=item.progress,
    )


def removed_work_item(
    item: WorkItemState, reason: str, on: datetime, superseded_by: WorkItemId | None = None
) -> RemovedWorkItem:
    """The work item in Backlog or InProgress removed on that time, kept to the second.

    One in Backlog keeps its Tasks as written. A started or a blocked one loses its started
    time, its agent and its block; its completed Tasks and those removed before are kept, and
    each other Task is removed at that time for its reason, or as superseded by the work item
    named when the reason is blank. It may name the work item that supersedes it, and its reason
    may then be blank. The reason and what supersedes it are checked before any Task is moved.
    Raises EmptyPartError when the reason is blank with none named, CompletedAlreadyError when
    it is completed, RemovedAlreadyError when it is removed and RelationError when it names
    itself.
    """
    match item:
        case WorkItem() | StartedWorkItem() | BlockedWorkItem():
            return _gone(item, reason, on, superseded_by)
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{work_item_id_text(item.id)} is completed already")
        case RemovedWorkItem():
            raise RemovedAlreadyError(item.id)
        case _ as unreachable:
            assert_never(unreachable)


def reason_of(item: WorkItemState) -> str:
    """The reason a removed work item was removed for; empty for one that is not removed."""
    match item:
        case RemovedWorkItem():
            return item.reason
        case WorkItem() | StartedWorkItem() | BlockedWorkItem() | CompletedWorkItem():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def superseded_by_of(item: WorkItemState) -> str:
    """The id of the work item that supersedes a removed one as written; empty for none."""
    match item:
        case RemovedWorkItem():
            return "" if item.superseded_by is None else work_item_id_text(item.superseded_by)
        case WorkItem() | StartedWorkItem() | BlockedWorkItem() | CompletedWorkItem():
            return ""
        case _ as unreachable:
            assert_never(unreachable)
