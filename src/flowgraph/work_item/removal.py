"""The removal of a work item: one in Backlog drops out of the flow with its reason, kept whole.

Removed stands apart from the flow: nothing is deleted, and a removed work item takes no move.
"""

from datetime import datetime
from typing import assert_never

from flowgraph.criterion import said
from flowgraph.task import CompletedAlreadyError, StartedAlreadyError
from flowgraph.work_item.model import (
    CompletedWorkItem,
    RemovedAlreadyError,
    RemovedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemState,
    work_item_id_text,
)


def removed_work_item(item: WorkItemState, reason: str, on: datetime) -> RemovedWorkItem:
    """The work item in Backlog removed on that time, kept to the second, for the reason given.

    Its Tasks stay as written. Raises EmptyPartError when the reason is blank,
    StartedAlreadyError when the item is started, CompletedAlreadyError when it is completed
    and RemovedAlreadyError when it is removed.
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
                said("reason", reason),
                item.tasks,
                item.parent,
                item.knowledge,
            )
        case StartedWorkItem():
            raise StartedAlreadyError(f"{work_item_id_text(item.id)} is started already")
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
        case WorkItem() | StartedWorkItem() | CompletedWorkItem():
            return ""
        case _ as unreachable:
            assert_never(unreachable)
