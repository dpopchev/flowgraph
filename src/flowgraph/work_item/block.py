"""The block of a started work item: it cannot go on for a reason, waiting on someone.

A blocked work item still takes a Task and a line, while no Task of it moves; its unblock takes
it back to started with what it held.
"""

from datetime import datetime
from typing import assert_never

from flowgraph.criterion import said
from flowgraph.record import Now
from flowgraph.task import BlockedError, CompletedAlreadyError, NotBlockedError, NotStartedError
from flowgraph.work_item.id import WorkItemId, work_item_id_text
from flowgraph.work_item.model import (
    BlockedWorkItem,
    CompletedWorkItem,
    LoadWorkItem,
    RemovedAlreadyError,
    RemovedWorkItem,
    SaveWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemState,
)


def blocked_work_item(
    item: WorkItemState, reason: str, waiting_on: str, on: datetime
) -> BlockedWorkItem:
    """The started work item blocked on that time, kept to the second, for the reason given.

    Raises NotStartedError when it is in Backlog, BlockedError when it is blocked already,
    CompletedAlreadyError when it is completed, RemovedAlreadyError when it is removed and
    EmptyPartError when the reason or what it waits on is blank.
    """
    named = work_item_id_text(item.id)
    match item:
        case WorkItem():
            raise NotStartedError(f"{named} is in Backlog: start it first")
        case StartedWorkItem():
            return BlockedWorkItem(
                item.id,
                item.title,
                item.criterion,
                item.description,
                item.created,
                item.started,
                said("reason", reason),
                on.replace(microsecond=0),
                said("waiting on", waiting_on),
                agent=item.agent,
                tasks=item.tasks,
                parent=item.parent,
                complexity=item.complexity,
                knowledge=item.knowledge,
                relations=item.relations,
                about=item.about,
            )
        case BlockedWorkItem():
            raise BlockedError(f"{named} is blocked already")
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{named} is completed already")
        case RemovedWorkItem():
            raise RemovedAlreadyError(item.id)
        case _ as unreachable:
            assert_never(unreachable)


def unblocked_work_item(item: WorkItemState) -> StartedWorkItem:
    """The blocked work item started again, with the started time, the agent and the Tasks it had.

    Its block is dropped. Raises NotBlockedError when it is in Backlog, started, completed or
    removed.
    """
    match item:
        case BlockedWorkItem():
            return StartedWorkItem(
                item.id,
                item.title,
                item.criterion,
                item.description,
                item.created,
                item.started,
                agent=item.agent,
                tasks=item.tasks,
                parent=item.parent,
                complexity=item.complexity,
                knowledge=item.knowledge,
                relations=item.relations,
                about=item.about,
            )
        case WorkItem() | StartedWorkItem() | CompletedWorkItem() | RemovedWorkItem():
            raise NotBlockedError(f"{work_item_id_text(item.id)} is not blocked")
        case _ as unreachable:
            assert_never(unreachable)


def block_of(item: WorkItemState) -> tuple[str, str]:
    """The reason a blocked work item is blocked for and what it waits on; empty for any other."""
    match item:
        case BlockedWorkItem():
            return item.reason, item.waiting_on
        case WorkItem() | StartedWorkItem() | CompletedWorkItem() | RemovedWorkItem():
            return "", ""
        case _ as unreachable:
            assert_never(unreachable)


def block_work_item(
    *,
    item_id: WorkItemId,
    reason: str,
    waiting_on: str,
    load_work_item: LoadWorkItem,
    save_work_item: SaveWorkItem,
    now: Now,
) -> None:
    """Block the started work item of that id now, for the reason, and save it whole.

    Raises WorkItemNotFoundError when the record holds no such item, or the refusal of
    blocked_work_item; nothing is saved.
    """
    save_work_item(blocked_work_item(load_work_item(item_id), reason, waiting_on, now()))


def unblock_work_item(
    *, item_id: WorkItemId, load_work_item: LoadWorkItem, save_work_item: SaveWorkItem
) -> None:
    """Unblock the blocked work item of that id and save it whole, started again.

    Raises WorkItemNotFoundError when the record holds no such item and NotBlockedError when it
    is not blocked; nothing is saved.
    """
    save_work_item(unblocked_work_item(load_work_item(item_id)))
