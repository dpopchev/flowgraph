"""The moves of a work item between its states: started, then completed, while it takes Tasks."""

from datetime import datetime
from typing import assert_never

from flowgraph.criterion import Evidence, settled
from flowgraph.task import (
    CompletedAlreadyError,
    NoTaskError,
    NotStartedError,
    StartedAlreadyError,
    all_completed,
)
from flowgraph.work_item.id import work_item_id_text
from flowgraph.work_item.model import (
    CompletedWorkItem,
    OpenWorkItem,
    RemovedAlreadyError,
    RemovedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemState,
)


def still_open(item: WorkItemState) -> OpenWorkItem:
    """The work item, which still takes Tasks; raises CompletedAlreadyError when it is completed."""
    match item:
        case WorkItem() | StartedWorkItem():
            return item
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{work_item_id_text(item.id)} is completed already")
        case RemovedWorkItem():
            raise RemovedAlreadyError(item.id)
        case _ as unreachable:
            assert_never(unreachable)


def started_work_item(item: WorkItemState, on: datetime) -> StartedWorkItem:
    """The work item started on that time, kept to the second, its Tasks still in Backlog.

    Raises NoTaskError when it has no Task, StartedAlreadyError when it is started and
    CompletedAlreadyError when it is completed.
    """
    match item:
        case WorkItem(tasks=()):
            raise NoTaskError(f"{work_item_id_text(item.id)} has no Task to start with")
        case WorkItem():
            to_the_second = on.replace(microsecond=0)
            return StartedWorkItem(
                item.id,
                item.title,
                item.criterion,
                item.description,
                item.created,
                to_the_second,
                item.tasks,
                item.parent,
                item.knowledge,
                item.relations,
                item.about,
            )
        case StartedWorkItem():
            raise StartedAlreadyError(f"{work_item_id_text(item.id)} is started already")
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{work_item_id_text(item.id)} is completed already")
        case RemovedWorkItem():
            raise RemovedAlreadyError(item.id)
        case _ as unreachable:
            assert_never(unreachable)


def completed_work_item(
    item: WorkItemState, on: datetime, commit: Evidence, decision: str | None = None
) -> CompletedWorkItem:
    """The work item completed on that time, kept to the second, in that commit or without one.

    A work item that states a hypothesis is completed with the decision that answers it. Raises
    NotStartedError when it is in Backlog, OpenTaskError naming the Tasks not completed,
    DecisionError when a hypothesis has no decision or another criterion is given one, and
    CompletedAlreadyError when it is completed.
    """
    match item:
        case WorkItem():
            raise NotStartedError(f"{work_item_id_text(item.id)} is in Backlog: start it first")
        case StartedWorkItem():
            done = all_completed(item.tasks, work_item_id_text(item.id))
            return CompletedWorkItem(
                item.id,
                item.title,
                settled(item.criterion, decision, work_item_id_text(item.id)),
                item.description,
                item.created,
                item.started,
                on.replace(microsecond=0),
                commit,
                done,
                item.parent,
                item.knowledge,
                item.relations,
                about=item.about,
            )
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{work_item_id_text(item.id)} is completed already")
        case RemovedWorkItem():
            raise RemovedAlreadyError(item.id)
        case _ as unreachable:
            assert_never(unreachable)
