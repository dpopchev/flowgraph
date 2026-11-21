"""The amendment of a work item: the wording of one in Backlog rewritten, part by part.

It is not a move: the state of the work item stays, and so do its id, its Tasks and its place.
"""

from dataclasses import dataclass, replace
from typing import assert_never

from flowgraph.criterion import (
    STATES,
    Criterion,
    Defect,
    Scenario,
    make_defect,
    make_scenario,
    said,
)
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
    """The parts of a work item to rewrite: each its new text, or None where it stays as it was.

    The parts of the criterion are those of every form; a work item takes the ones it states.
    """

    title: str | None = None
    description: str | None = None
    given: str | None = None
    when: str | None = None
    then: str | None = None
    observed: str | None = None
    expected: str | None = None


class NoPartError(ValueError):
    """An amendment that names no part of the work item to rewrite."""


class NoSuchPartError(ValueError):
    """An amendment that names a part the criterion of the work item does not have."""


def _kept(new: str | None, was: str) -> str:
    """The new text of a part, or the one it had when the amendment does not name it."""
    return was if new is None else new


def _amended_criterion(named: str, was: Criterion, amendment: Amendment) -> Criterion:
    """The criterion with the parts the amendment names rewritten.

    Raises NoSuchPartError when it names a part of another form of criterion and EmptyPartError
    when a part is blank.
    """
    of_scenario = (amendment.given, amendment.when, amendment.then)
    of_defect = (amendment.observed, amendment.expected)
    match was:
        case Scenario():
            if any(part is not None for part in of_defect):
                raise NoSuchPartError(
                    f"{named} has no observed or expected: it states {STATES[Scenario]}"
                )
            given, when, then = of_scenario
            return make_scenario(
                _kept(given, was.given), _kept(when, was.when), _kept(then, was.then)
            )
        case Defect():
            if any(part is not None for part in of_scenario):
                raise NoSuchPartError(
                    f"{named} has no given, when or then: it states {STATES[Defect]}"
                )
            observed, expected = of_defect
            return make_defect(_kept(observed, was.observed), _kept(expected, was.expected))
        case _ as unreachable:
            assert_never(unreachable)


def amended_work_item(item: WorkItemState, amendment: Amendment) -> WorkItem:
    """The work item in Backlog with the parts the amendment names rewritten, the rest as it was.

    Raises NoPartError when it names none, NoSuchPartError when it names a part the criterion of
    the item does not have, EmptyPartError when its title or a part of its criterion is blank,
    StartedAlreadyError when the item is started, CompletedAlreadyError when it is completed and
    RemovedAlreadyError when it is removed.
    """
    named = work_item_id_text(item.id)
    match item:
        case WorkItem():
            if amendment == Amendment():
                raise NoPartError(f"amend rewrites no part of {named}: name one")
            criterion = _amended_criterion(named, item.criterion, amendment)
            title = said("title", _kept(amendment.title, item.title))
            description = _kept(amendment.description, item.description)
            return replace(item, title=title, criterion=criterion, description=description)
        case StartedWorkItem():
            raise StartedAlreadyError(f"{named} is started already")
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{named} is completed already")
        case RemovedWorkItem():
            raise RemovedAlreadyError(item.id)
        case _ as unreachable:
            assert_never(unreachable)
