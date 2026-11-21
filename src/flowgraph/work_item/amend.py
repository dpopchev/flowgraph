"""The amendment of a work item: the wording of one in Backlog rewritten, part by part.

It is not a move: the state of the work item stays, and so do its id, its Tasks and its place.
"""

from dataclasses import dataclass, replace
from typing import assert_never

from flowgraph.criterion import make_scenario, said
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


@dataclass(frozen=True)
class Amendment:
    """The parts of a work item to rewrite: each its new text, or None where it stays as it was."""

    title: str | None = None
    description: str | None = None
    given: str | None = None
    when: str | None = None
    then: str | None = None


class NoPartError(ValueError):
    """An amendment that names no part of the work item to rewrite."""


def amended_work_item(item: WorkItemState, amendment: Amendment) -> WorkItem:
    """The work item in Backlog with the parts the amendment names rewritten, the rest as it was.

    Raises NoPartError when it names none, EmptyPartError when its title or a part of its
    criterion is blank, StartedAlreadyError when the item is started, CompletedAlreadyError
    when it is completed and RemovedAlreadyError when it is removed.
    """
    named = work_item_id_text(item.id)
    match item:
        case WorkItem():
            if amendment == Amendment():
                raise NoPartError(f"amend rewrites no part of {named}: name one")
            was = item.scenario
            scenario = make_scenario(
                was.given if amendment.given is None else amendment.given,
                was.when if amendment.when is None else amendment.when,
                was.then if amendment.then is None else amendment.then,
            )
            title = said("title", item.title if amendment.title is None else amendment.title)
            kept = amendment.description is None
            description = item.description if kept else amendment.description
            return replace(item, title=title, scenario=scenario, description=description)
        case StartedWorkItem():
            raise StartedAlreadyError(f"{named} is started already")
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{named} is completed already")
        case RemovedWorkItem():
            raise RemovedAlreadyError(item.id)
        case _ as unreachable:
            assert_never(unreachable)
