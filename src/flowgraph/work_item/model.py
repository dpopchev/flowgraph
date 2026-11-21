"""A work item of any kind: its kind and id, its states, its Tasks and the moves between them.

The kind is a value the id carries, so one set of states and moves serves the Story, the
Upkeep and every kind that shares their Given / When / Then.
"""

import re
from collections.abc import Callable, Collection
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import assert_never

from flowgraph.criterion import (
    STATES,
    Commit,
    Criterion,
    CriterionError,
    Scenario,
    said,
    settled,
)
from flowgraph.task import (
    BlockedTask,
    CompletedAlreadyError,
    CompletedTask,
    NoTaskError,
    NotStartedError,
    StartedAlreadyError,
    StartedTask,
    Task,
    TaskRow,
    TaskState,
    all_completed,
)


@dataclass(frozen=True)
class Kind:
    """A kind of work item: its noun, the article before it, the prefix of its ids, and the
    form of criterion a work item of the kind takes."""

    noun: str
    article: str
    prefix: str
    takes: type[Criterion] = Scenario


@dataclass(frozen=True)
class WorkItemId:
    """The identity of a work item: its kind and its number among the items of that kind."""

    kind: Kind
    number: int


@dataclass(frozen=True)
class WorkItem:
    """A work item in Backlog: added, not yet started, with the Tasks written for it so far."""

    id: WorkItemId
    title: str
    criterion: Criterion
    description: str
    created: datetime
    tasks: tuple[Task, ...]


@dataclass(frozen=True)
class StartedWorkItem:
    """A work item in InProgress: started with at least one Task, each in any state of its own."""

    id: WorkItemId
    title: str
    criterion: Criterion
    description: str
    created: datetime
    started: datetime
    tasks: tuple[TaskState, ...]


@dataclass(frozen=True)
class CompletedWorkItem:
    """A work item in Completed: every Task of it completed, the item in its commit on `main`."""

    id: WorkItemId
    title: str
    criterion: Criterion
    description: str
    created: datetime
    started: datetime
    completed: datetime
    commit: Commit
    tasks: tuple[CompletedTask, ...]


@dataclass(frozen=True)
class RemovedWorkItem:
    """A work item in Removed: dropped out of Backlog for a reason, its Tasks kept as written."""

    id: WorkItemId
    title: str
    criterion: Criterion
    description: str
    created: datetime
    removed: datetime
    reason: str
    tasks: tuple[Task, ...]


# A work item that still takes Tasks: in Backlog or started.
OpenWorkItem = WorkItem | StartedWorkItem

# A work item in any of its states, as the record keeps it.
WorkItemState = WorkItem | StartedWorkItem | CompletedWorkItem | RemovedWorkItem


@dataclass
class WorkItemRow:
    """One work item as plain data, as a view reads it from the record.

    A commit once completed, a reason once removed. Its created time is what orders the work
    items of the Backlog nobody placed.
    """

    id: str
    title: str
    state: str
    commit: str = ""
    reason: str = ""
    created: datetime = field(kw_only=True)


@dataclass
class WorkItemDetail:
    """One work item with its criterion and its Tasks as plain data, as a view reads it whole.

    The parts of its criterion are those its kind states; the others are empty.
    """

    id: str
    title: str
    state: str
    description: str
    tasks: list[TaskRow]
    given: str = ""
    when: str = ""
    then: str = ""
    observed: str = ""
    expected: str = ""
    hypothesis: str = ""
    decision: str = ""
    commit: str = ""
    reason: str = ""


# The rows of the work items in the record; an empty list when it holds none.
FindWorkItemRows = Callable[[], list[WorkItemRow]]

# The ids of every Task in the record, as written; an empty list when it holds none.
FindTaskIds = Callable[[], list[str]]

# The work item of that id, whole; raises WorkItemNotFoundError when the record holds none.
LoadWorkItem = Callable[[WorkItemId], WorkItemState]

# Save the work item whole.
SaveWorkItem = Callable[[WorkItemState], None]


class KindError(ValueError):
    """A kind of work item without a noun, or with a prefix that is not capital letters."""


class WorkItemIdError(ValueError):
    """A number or a text that is no id of the kind asked for."""


class WorkItemNotFoundError(Exception):
    """A record that holds no work item of the id asked for; `item_id` is that id."""

    def __init__(self, item_id: WorkItemId) -> None:
        super().__init__(f"no {item_id.kind.noun} {work_item_id_text(item_id)} in the record")
        self.item_id = item_id


class RemovedAlreadyError(ValueError):
    """A removed work item moved, amended or given a Task; the message names it."""

    def __init__(self, item_id: WorkItemId) -> None:
        super().__init__(f"{work_item_id_text(item_id)} is removed already")


class WorkItemFileError(Exception):
    """A file named as a work item in a record that does not hold one; names its path."""


class WorkItemMismatchError(Exception):
    """A work item read back different from the one written; its file is as it was before."""


def make_kind(noun: str, article: str, prefix: str, takes: type[Criterion] = Scenario) -> Kind:
    """The kind of work item of that noun, written with that article and prefix.

    It takes a Given / When / Then unless another form of criterion is named. Raises KindError
    when the noun is blank or the prefix is not capital letters.
    """
    if not noun.strip():
        raise KindError("a kind names its noun")
    if re.fullmatch(r"[A-Z]+", prefix) is None:
        raise KindError(f"{prefix!r} is no prefix: it is capital letters")
    return Kind(noun, article, prefix, takes)


def make_work_item_id(kind: Kind, number: int) -> WorkItemId:
    """The id of the work item of that kind with that number in the record.

    Raises WorkItemIdError naming the kind when the number is below 1.
    """
    if number < 1:
        raise WorkItemIdError(f"{kind.article} {kind.noun} id counts from 1: {number} is below 1")
    return WorkItemId(kind, number)


def work_item_id_text(item_id: WorkItemId) -> str:
    """The id as it is written: the prefix of its kind, `-` and the number, four digits at least."""
    return f"{item_id.kind.prefix}-{item_id.number:04d}"


def parse_work_item_id(kind: Kind, text: str) -> WorkItemId:
    """The id of that kind written as the text.

    Raises WorkItemIdError when the text is not the prefix of the kind, `-` and a number.
    """
    written = re.fullmatch(rf"{kind.prefix}-(\d+)", text)
    if written is None:
        raise WorkItemIdError(f"{text!r} is no {kind.noun} id: it is {kind.prefix}- and a number")
    return make_work_item_id(kind, int(written.group(1)))


def next_work_item_id(kind: Kind, taken: Collection[WorkItemId]) -> WorkItemId:
    """The next free id of the kind: one above the highest taken, the first when none is."""
    return make_work_item_id(kind, max((item_id.number for item_id in taken), default=0) + 1)


def make_work_item(
    item_id: WorkItemId, title: str, criterion: Criterion, description: str, created: datetime
) -> WorkItem:
    """A work item in Backlog, its created time kept to the second.

    Raises EmptyPartError when the title is blank and CriterionError when the criterion is not
    of the form the kind of the item takes.
    """
    kind = item_id.kind
    if not isinstance(criterion, kind.takes):
        stated = f"{STATES[kind.takes]}, not {STATES[type(criterion)]}"
        raise CriterionError(f"{kind.article} {kind.noun} states {stated}")
    to_the_second = created.replace(microsecond=0)
    return WorkItem(item_id, said("title", title), criterion, description, to_the_second, ())


def append_task[W: OpenWorkItem](item: W, task: Task) -> W:
    """The work item with the Task written for it, after the Tasks it already has."""
    return replace(item, tasks=(*item.tasks, task))


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
    item: WorkItemState, on: datetime, commit: Commit, decision: str | None = None
) -> CompletedWorkItem:
    """The work item completed on that time, kept to the second, in that commit.

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
            )
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{work_item_id_text(item.id)} is completed already")
        case RemovedWorkItem():
            raise RemovedAlreadyError(item.id)
        case _ as unreachable:
            assert_never(unreachable)


def state_name(item: WorkItemState | TaskState) -> str:
    """The state of a work item or a Task as the record writes it."""
    match item:
        case WorkItem() | Task():
            return "backlog"
        case StartedWorkItem() | StartedTask():
            return "started"
        case BlockedTask():
            return "blocked"
        case CompletedWorkItem() | CompletedTask():
            return "completed"
        case RemovedWorkItem():
            return "removed"
        case _ as unreachable:
            assert_never(unreachable)


def commit_sha(item: WorkItemState | TaskState) -> str:
    """The sha of the commit of a completed work item or Task; empty for one not completed."""
    match item:
        case CompletedWorkItem() | CompletedTask():
            return item.commit.sha
        case WorkItem() | StartedWorkItem() | RemovedWorkItem():
            return ""
        case Task() | StartedTask() | BlockedTask():
            return ""
        case _ as unreachable:
            assert_never(unreachable)
