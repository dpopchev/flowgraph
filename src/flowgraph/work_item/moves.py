"""The moves of a work item between its states: started, then completed, while it takes Tasks."""

from dataclasses import replace
from datetime import datetime
from typing import assert_never

from flowgraph.criterion import Answer, Decision, Evidence, settled
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
    state_name,
)
from flowgraph.work_item.verification import (
    TAKES,
    NotVerifiableError,
    Verdict,
    VerifiedAlreadyError,
    make_verification,
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
    item: WorkItemState, on: datetime, commit: Evidence, decision: Decision | None = None
) -> CompletedWorkItem:
    """The work item completed on that time, kept to the second, in that commit or without one.

    A work item that states a hypothesis is completed with the decision that answers it, and
    its yes or no. Raises NotStartedError when it is in Backlog, OpenTaskError naming the Tasks
    not completed, DecisionError when a hypothesis has no decision or no answer or another
    criterion is given a decision, and
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


def verified_work_item(
    item: WorkItemState, text: str, on: datetime, answer: Verdict = "yes"
) -> CompletedWorkItem:
    """The completed work item with the answer of its closing, yes by default, the text the run
    printed and the time; it stays completed whatever the answer.

    Raises NotVerifiableError when it is not completed or is a Spike, VerifiedAlreadyError when
    it holds an answer already (a second answer is refused, never added or replaced) and
    EmptyPartError when the text is blank.
    """
    named = work_item_id_text(item.id)
    match item:
        case CompletedWorkItem(criterion=Answer()):
            raise NotVerifiableError(f"{named} is a Spike: {TAKES}")
        case CompletedWorkItem(verified=None):
            return replace(item, verified=make_verification(answer, text, on))
        case CompletedWorkItem():
            raise VerifiedAlreadyError(f"{named} is verified already")
        case WorkItem() | StartedWorkItem() | RemovedWorkItem():
            raise NotVerifiableError(f"{named} is {state_name(item)}: {TAKES}")
        case _ as unreachable:
            assert_never(unreachable)
