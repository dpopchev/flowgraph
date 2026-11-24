"""The amendment of a work item: its wording rewritten, part by part.

One in Backlog is amended as it is; a started or blocked one with its deviation, kept on it.
It is not a move: the state of the work item stays, and so do its id, its Tasks and its place.
Its parent is a part too: the Feature it is under, or standing alone.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import assert_never

from flowgraph.criterion import (
    STATES,
    Answer,
    Criterion,
    Defect,
    Hypothesis,
    Scenario,
    make_defect,
    make_hypothesis,
    make_scenario,
    said,
)
from flowgraph.knowledge import KnowledgeLine
from flowgraph.parent import NO_CRITERION, Parent, Realizes, realizes_under
from flowgraph.relation import with_depends_on
from flowgraph.task import CompletedAlreadyError, StartedAlreadyError
from flowgraph.work_item.complexity import Complexity
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
    noted_work_item,
)


@dataclass(frozen=True)
class Amendment:
    """The parts of a work item to rewrite: each its new text, or None where it stays as it was.

    The parts of the criterion are those of every form; a work item takes the ones it states.
    Its parent is the Feature to put it under, or standing alone. The work items it depends on
    replace those it had; none given takes them all away. The terms it is about replace those it
    had too, none given as well. The complexity given replaces the one it had; none given keeps it.
    The criterion it realizes given replaces the one it had, NO_CRITERION takes it away and none
    given keeps it, unless the parent changes, which drops it. The output and the check are the
    parts of a Task, which fgraph amend takes too; a work item refuses them.
    """

    title: str | None = None
    description: str | None = None
    given: str | None = None
    when: str | None = None
    then: str | None = None
    observed: str | None = None
    expected: str | None = None
    hypothesis: str | None = None
    parent: Parent | None = None
    depends_on: tuple[WorkItemId, ...] | None = None
    about: tuple[str, ...] | None = None
    complexity: Complexity | None = None
    realizes: Realizes | None = None
    output: str | None = None
    check: str | None = None


# Check the move of the work item of that id from the parent it had to the one an amend names;
# raises the refusal of the Feature that does not take it.
CheckMove = Callable[[WorkItemId, Parent, Parent], None]

# Check that the Feature has the criterion named; raises RealizesError naming the Feature and
# the count of its criteria.
CheckRealizes = Callable[[Parent, Realizes], None]


# The parts of an amendment that belong to each form of criterion a work item in Backlog states.
PARTS: Mapping[type[Criterion], tuple[str, ...]] = {
    Scenario: ("given", "when", "then"),
    Defect: ("observed", "expected"),
    Hypothesis: ("hypothesis",),
}


# The parts of an amendment that only a Task states.
TASK_PARTS = ("output", "check")


class NoPartError(ValueError):
    """An amendment that names no part of the work item to rewrite."""


class NoSuchPartError(ValueError):
    """An amendment that names a part the criterion of the work item does not have."""


def _kept[Part](new: Part | None, was: Part) -> Part:
    """The new value of a part, or the one it had when the amendment does not name it."""
    return was if new is None else new


def _listed(parts: tuple[str, ...]) -> str:
    """The parts as a refusal lists them: `given, when or then`."""
    *first, last = parts
    return f"{', '.join(first)} or {last}" if first else last


def _amended_criterion(named: str, was: Criterion, amendment: Amendment) -> Criterion:
    """The criterion with the parts the amendment names rewritten.

    Raises NoSuchPartError when it names a part of another form of criterion and EmptyPartError
    when a part is blank.
    """
    for form, parts in PARTS.items():
        foreign = not isinstance(was, form)
        if foreign and any(getattr(amendment, part) is not None for part in parts):
            raise NoSuchPartError(f"{named} has no {_listed(parts)}: it states {STATES[type(was)]}")
    match was:
        case Scenario():
            return make_scenario(
                _kept(amendment.given, was.given),
                _kept(amendment.when, was.when),
                _kept(amendment.then, was.then),
            )
        case Defect():
            return make_defect(
                _kept(amendment.observed, was.observed), _kept(amendment.expected, was.expected)
            )
        case Hypothesis():
            return make_hypothesis(_kept(amendment.hypothesis, was.question))
        case Answer():
            raise NoSuchPartError(f"{named} is answered: its hypothesis is not amended")
        case _ as unreachable:
            assert_never(unreachable)


class DeviationError(ValueError):
    """An amend of a started item without its deviation, or of one in Backlog with one."""


def check_deviation(named: str, started: bool, deviation: KnowledgeLine | None) -> None:
    """Raise DeviationError unless a started item has its deviation and one in Backlog has none."""
    if started and deviation is None:
        needed = "amend it with --deviation TEXT, what changes in what it was agreed to do"
        raise DeviationError(f"{named} is started: {needed}")
    if not started and deviation is not None:
        none = "it has no agreed plan to deviate from -- amend it without --deviation"
        raise DeviationError(f"{named} is in Backlog: {none}")


def _check_task_parts(named: str, amendment: Amendment) -> None:
    """Raise NoSuchPartError when the amendment names a part that only a Task states."""
    given = tuple(part for part in TASK_PARTS if getattr(amendment, part) is not None)
    if given:
        raise NoSuchPartError(f"{named} has no {_listed(given)}: only a Task states them")


def _amended_started(
    item: StartedWorkItem | BlockedWorkItem, amendment: Amendment, deviation: KnowledgeLine | None
) -> StartedWorkItem | BlockedWorkItem:
    """The started or blocked work item with its title, description, criterion and terms rewritten.

    The deviation is kept after the lines it had; its state, times, agent, block and Tasks stay.
    Raises the refusals of amended_work_item for a started item.
    """
    named = work_item_id_text(item.id)
    backlog_alone = (amendment.complexity, amendment.parent, amendment.depends_on)
    if any(part is not None for part in backlog_alone):
        alone = "its complexity, its parent and what it depends on are amended in Backlog alone"
        raise StartedAlreadyError(f"{named} is started: {alone}")
    _check_task_parts(named, amendment)
    check_deviation(named, True, deviation)
    if deviation is None or amendment == Amendment():
        raise NoPartError(f"amend rewrites no part of {named}: name one")
    amended = replace(
        item,
        title=said("title", _kept(amendment.title, item.title)),
        criterion=_amended_criterion(named, item.criterion, amendment),
        description=_kept(amendment.description, item.description),
        about=_kept(amendment.about, item.about),
    )
    return noted_work_item(amended, deviation)


def amended_work_item(
    item: WorkItemState, amendment: Amendment, deviation: KnowledgeLine | None = None
) -> OpenWorkItem:
    """The work item with the parts the amendment names rewritten, the rest as it was.

    One in Backlog is amended without a deviation; a started or blocked one with its deviation,
    kept on it after the lines it had, and its title, description, criterion and terms alone.
    Raises NoPartError when it names none, NoSuchPartError when it names a part the criterion of
    the item does not have or a part of a Task, EmptyPartError when its title or a part of its
    criterion is blank, RelationError when it makes the item depend on itself, RealizesError when
    it names a criterion for an item standing alone, DeviationError when a started item has none
    or one in Backlog has one, StartedAlreadyError when a started item is given a complexity, a
    parent or what it depends on, CompletedAlreadyError when it is completed and
    RemovedAlreadyError when it is removed.
    """
    named = work_item_id_text(item.id)
    match item:
        case WorkItem():
            check_deviation(named, False, deviation)
            _check_task_parts(named, amendment)
            if amendment == Amendment():
                raise NoPartError(f"amend rewrites no part of {named}: name one")
            criterion = _amended_criterion(named, item.criterion, amendment)
            title = said("title", _kept(amendment.title, item.title))
            description = _kept(amendment.description, item.description)
            parent = _kept(amendment.parent, item.parent)
            held = item.realizes if parent == item.parent else NO_CRITERION
            realizes = realizes_under(_kept(amendment.realizes, held), parent)
            about = _kept(amendment.about, item.about)
            complexity = _kept(amendment.complexity, item.complexity)
            relations = item.relations
            if amendment.depends_on is not None:
                relations = with_depends_on(relations, item.id, amendment.depends_on)
            return replace(
                item,
                title=title,
                criterion=criterion,
                description=description,
                parent=parent,
                realizes=realizes,
                relations=relations,
                about=about,
                complexity=complexity,
            )
        case StartedWorkItem() | BlockedWorkItem():
            return _amended_started(item, amendment, deviation)
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{named} is completed already")
        case RemovedWorkItem():
            raise RemovedAlreadyError(item.id)
        case _ as unreachable:
            assert_never(unreachable)
