"""A work item of any kind: its states, its Tasks and the lines it keeps.

The kind is a value the id carries, so one set of states and moves serves the Story, the
Upkeep and every kind that shares their Given / When / Then. The kind and the id are in
flowgraph.work_item.id, the moves between the states in flowgraph.work_item.moves and the
names the record writes them by in flowgraph.work_item.state.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime

from flowgraph.criterion import (
    STATES,
    Criterion,
    CriterionError,
    Evidence,
    said,
)
from flowgraph.knowledge import KnowledgeLine
from flowgraph.parent import NO_CRITERION, STANDALONE, Parent, Realizes, realizes_under
from flowgraph.relation import Relations, make_relations
from flowgraph.task import CompletedTask, RemovedTask, Task, TaskState, task_of
from flowgraph.work_item.agent import Agent
from flowgraph.work_item.complexity import Complexity
from flowgraph.work_item.errors import (
    RemovedAlreadyError as RemovedAlreadyError,
)
from flowgraph.work_item.errors import (
    WorkItemFileError as WorkItemFileError,
)
from flowgraph.work_item.errors import (
    WorkItemMismatchError as WorkItemMismatchError,
)
from flowgraph.work_item.errors import (
    WorkItemNotFoundError as WorkItemNotFoundError,
)
from flowgraph.work_item.id import WorkItemId
from flowgraph.work_item.progress import ProgressLine
from flowgraph.work_item.verification import Verification
from flowgraph.work_item.views import WorkItemRow

# The relations of a work item that names none.
NO_RELATIONS: Relations[WorkItemId] = Relations()


@dataclass(frozen=True)
class WorkItem:
    """A work item in Backlog: added, not yet started, with the Tasks written for it so far."""

    id: WorkItemId
    title: str
    criterion: Criterion
    description: str
    created: datetime
    tasks: tuple[Task, ...]
    parent: Parent = STANDALONE
    realizes: Realizes = field(default=NO_CRITERION, kw_only=True)
    complexity: Complexity | None = None
    knowledge: tuple[KnowledgeLine, ...] = ()
    relations: Relations[WorkItemId] = NO_RELATIONS
    about: tuple[str, ...] = ()
    progress: tuple[ProgressLine, ...] = ()


@dataclass(frozen=True)
class StartedWorkItem:
    """A work item in InProgress: started with at least one Task, each in any state of its own."""

    id: WorkItemId
    title: str
    criterion: Criterion
    description: str
    created: datetime
    started: datetime
    agent: Agent | None = field(default=None, kw_only=True)
    tasks: tuple[TaskState, ...]
    parent: Parent = STANDALONE
    realizes: Realizes = field(default=NO_CRITERION, kw_only=True)
    complexity: Complexity | None = None
    knowledge: tuple[KnowledgeLine, ...] = ()
    relations: Relations[WorkItemId] = NO_RELATIONS
    about: tuple[str, ...] = ()
    progress: tuple[ProgressLine, ...] = ()


@dataclass(frozen=True)
class BlockedWorkItem:
    """A started work item that cannot go on: its reason, the time since and what it waits on."""

    id: WorkItemId
    title: str
    criterion: Criterion
    description: str
    created: datetime
    started: datetime
    reason: str
    since: datetime
    waiting_on: str
    agent: Agent | None = field(default=None, kw_only=True)
    tasks: tuple[TaskState, ...]
    parent: Parent = STANDALONE
    realizes: Realizes = field(default=NO_CRITERION, kw_only=True)
    complexity: Complexity | None = None
    knowledge: tuple[KnowledgeLine, ...] = ()
    relations: Relations[WorkItemId] = NO_RELATIONS
    about: tuple[str, ...] = ()
    progress: tuple[ProgressLine, ...] = ()


@dataclass(frozen=True)
class CompletedWorkItem:
    """A work item in Completed: each Task completed or removed, its commit on `main` or none.

    It holds the answer of its closing once verified, none before.
    """

    id: WorkItemId
    title: str
    criterion: Criterion
    description: str
    created: datetime
    started: datetime
    completed: datetime
    agent: Agent | None = field(default=None, kw_only=True)
    commit: Evidence
    tasks: tuple[CompletedTask | RemovedTask, ...]
    parent: Parent = STANDALONE
    realizes: Realizes = field(default=NO_CRITERION, kw_only=True)
    complexity: Complexity | None = None
    knowledge: tuple[KnowledgeLine, ...] = ()
    relations: Relations[WorkItemId] = NO_RELATIONS
    about: tuple[str, ...] = ()
    verified: Verification | None = None
    progress: tuple[ProgressLine, ...] = ()


@dataclass(frozen=True)
class RemovedWorkItem:
    """A work item in Removed: dropped out of Backlog or of InProgress for a reason.

    Its Tasks in Backlog are kept as written, its completed ones kept, the others removed with
    it. It names the work item that supersedes it when there is one; its reason may then be empty.
    """

    id: WorkItemId
    title: str
    criterion: Criterion
    description: str
    created: datetime
    removed: datetime
    reason: str
    tasks: tuple[Task | CompletedTask | RemovedTask, ...]
    parent: Parent = STANDALONE
    realizes: Realizes = field(default=NO_CRITERION, kw_only=True)
    complexity: Complexity | None = None
    knowledge: tuple[KnowledgeLine, ...] = ()
    relations: Relations[WorkItemId] = NO_RELATIONS
    superseded_by: WorkItemId | None = None
    about: tuple[str, ...] = ()
    progress: tuple[ProgressLine, ...] = ()


# A work item that still takes Tasks: in Backlog, started or blocked.
OpenWorkItem = WorkItem | StartedWorkItem | BlockedWorkItem

# A work item in any of its states, as the record keeps it.
WorkItemState = WorkItem | StartedWorkItem | BlockedWorkItem | CompletedWorkItem | RemovedWorkItem

# The rows of the work items in the record; an empty list when it holds none.
FindWorkItemRows = Callable[[], list[WorkItemRow]]

# The ids of every Task in the record, as written; an empty list when it holds none.
FindTaskIds = Callable[[], list[str]]

# The work item of that id, whole; raises WorkItemNotFoundError when the record holds none.
LoadWorkItem = Callable[[WorkItemId], WorkItemState]

# Save the work item whole.
SaveWorkItem = Callable[[WorkItemState], None]


def make_work_item(
    item_id: WorkItemId,
    title: str,
    criterion: Criterion,
    description: str,
    created: datetime,
    parent: Parent = STANDALONE,
    depends_on: Iterable[WorkItemId] = (),
    filed_during: WorkItemId | None = None,
    amends: WorkItemId | None = None,
    about: tuple[str, ...] = (),
    complexity: Complexity | None = None,
    realizes: Realizes = NO_CRITERION,
) -> WorkItem:
    """A work item in Backlog, its created time kept to the second; it stands alone unless a
    Feature is named as its parent, depends on the work items given, is filed during the one given
    and amends the one given, none by default. It is about the terms given, in order, none by
    default, carries the complexity given, none by default, and realizes the criterion of its
    Feature given, none by default.

    Raises EmptyPartError when the title is blank, CriterionError when the criterion is not of
    the form the kind of the item takes, RelationError when it names itself and RealizesError
    when it names a criterion and stands alone.
    """
    kind = item_id.kind
    if not isinstance(criterion, kind.takes):
        stated = f"{STATES[kind.takes]}, not {STATES[type(criterion)]}"
        raise CriterionError(f"{kind.article} {kind.noun} states {stated}")
    to_the_second = created.replace(microsecond=0)
    titled = said("title", title)
    relations = make_relations(item_id, depends_on, filed_during, amends)
    return WorkItem(
        item_id,
        titled,
        criterion,
        description,
        to_the_second,
        (),
        parent,
        complexity,
        (),
        relations,
        about,
        realizes=realizes_under(realizes, parent),
    )


def append_task[W: OpenWorkItem](item: W, task: Task) -> W:
    """The work item with the Task written for it, after the Tasks it already has."""
    return replace(item, tasks=(*item.tasks, task))


def noted_work_item[W: WorkItemState](item: W, line: KnowledgeLine) -> W:
    """The work item, in whatever state, with the line after the lines it already keeps."""
    return replace(item, knowledge=(*item.knowledge, line))


def progressed_work_item[W: WorkItemState](item: W, line: ProgressLine) -> W:
    """The work item, in whatever state, with the progress line after those it already keeps.

    A line records, it moves nothing. Raises TaskNotFoundError when the line names a Task the
    work item does not hold.
    """
    if line.task is not None:
        task_of(item.tasks, line.task)
    return replace(item, progress=(*item.progress, line))
