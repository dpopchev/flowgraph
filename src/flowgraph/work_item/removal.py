"""The removal of a work item: one in Backlog drops out of the flow with its reason, kept whole.

Removed stands apart from the flow: nothing is deleted, and a removed work item takes no move.
"""

from datetime import datetime
from typing import assert_never

from flowgraph.criterion import said
from flowgraph.relation import RelationError
from flowgraph.task import BlockedError, CompletedAlreadyError, StartedAlreadyError
from flowgraph.work_item.id import WorkItemId, work_item_id_text
from flowgraph.work_item.model import (
    BlockedWorkItem,
    CompletedWorkItem,
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


def removed_work_item(
    item: WorkItemState, reason: str, on: datetime, superseded_by: WorkItemId | None = None
) -> RemovedWorkItem:
    """The work item in Backlog removed on that time, kept to the second, for the reason given.

    Its Tasks stay as written. It may name the work item that supersedes it, and its reason may
    then be blank. Raises EmptyPartError when the reason is blank with none named,
    StartedAlreadyError when the item is started, BlockedError when it is blocked,
    CompletedAlreadyError when it is completed, RemovedAlreadyError when it is removed and
    RelationError when it names itself.
    """
    match item:
        case WorkItem():
            return RemovedWorkItem(
                item.id,
                item.title,
                item.criterion,
                item.description,
                item.created,
                on.replace(microsecond=0),
                _reason_kept(reason, superseded_by),
                item.tasks,
                item.parent,
                item.complexity,
                item.knowledge,
                item.relations,
                _superseded_by_kept(item.id, superseded_by),
                item.about,
                progress=item.progress,
            )
        case StartedWorkItem():
            raise StartedAlreadyError(f"{work_item_id_text(item.id)} is started already")
        case BlockedWorkItem():
            raise BlockedError(f"{work_item_id_text(item.id)} is blocked")
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
