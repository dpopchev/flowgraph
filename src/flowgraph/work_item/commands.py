"""The views and the commands of a work item: each command loads it whole, moves it, saves it."""

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import assert_never

from flowgraph.criterion import Criterion, Evidence, criterion_parts
from flowgraph.knowledge import KnowledgeKind, knowledge_row, make_knowledge_line
from flowgraph.parent import STANDALONE, Parent, parent_text
from flowgraph.record import Now
from flowgraph.task import (
    TaskId,
    TaskNotFoundError,
    make_task,
    next_task_id,
    parse_task_id,
    row_of,
)
from flowgraph.work_item.amend import Amendment, CheckMove, amended_work_item
from flowgraph.work_item.model import (
    CompletedWorkItem,
    FindTaskIds,
    FindWorkItemRows,
    Kind,
    LoadWorkItem,
    RemovedWorkItem,
    SaveWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemId,
    WorkItemState,
    append_task,
    commit_sha,
    make_work_item,
    next_work_item_id,
    noted_work_item,
    parse_work_item_id,
    started_work_item,
    state_name,
    still_open,
    work_item_id_text,
)
from flowgraph.work_item.removal import reason_of, removed_work_item, superseded_by_of
from flowgraph.work_item.tasks import blocked_task, completed_task, started_task, unblocked_task
from flowgraph.work_item.views import DependsRow, WorkItemDetail, WorkItemRow

# The work item that holds the Task of that id, whole; raises TaskNotFoundError when none does.
LoadHolder = Callable[[TaskId], WorkItemState]


def _started_on(item: WorkItemState) -> datetime | None:
    """The started time of a started work item; none in any other state, as its file reads."""
    match item:
        case StartedWorkItem():
            return item.started
        case WorkItem() | CompletedWorkItem() | RemovedWorkItem():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def _completed_on(item: WorkItemState) -> datetime | None:
    """The completed time of a completed work item; none for one not completed."""
    match item:
        case CompletedWorkItem():
            return item.completed
        case WorkItem() | StartedWorkItem() | RemovedWorkItem():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def _named_text(named: WorkItemId | None) -> str:
    """The id of the work item another one names as written; empty for none."""
    return "" if named is None else work_item_id_text(named)


def work_item_row(item: WorkItemState) -> WorkItemRow:
    """The work item as the row a view reads, whole: the row its file is read as."""
    return WorkItemRow(
        work_item_id_text(item.id),
        item.title,
        state_name(item),
        commit_sha(item),
        reason_of(item),
        parent_text(item.parent),
        created=item.created,
        started=_started_on(item),
        completed=_completed_on(item),
        tasks=[row_of(task) for task in item.tasks],
        depends_on=[work_item_id_text(each) for each in item.relations.depends_on],
        filed_during=_named_text(item.relations.filed_during),
        superseded_by=superseded_by_of(item),
        amends=_named_text(item.relations.amends),
    )


def work_item_detail(item: WorkItemState) -> WorkItemDetail:
    """The work item with its criterion and its Tasks as the plain data a view reads."""
    return WorkItemDetail(
        id=work_item_id_text(item.id),
        title=item.title,
        state=state_name(item),
        description=item.description,
        tasks=[row_of(task) for task in item.tasks],
        commit=commit_sha(item),
        reason=reason_of(item),
        parent=parent_text(item.parent),
        knowledge=[knowledge_row(line) for line in item.knowledge],
        depends_on=[DependsRow(work_item_id_text(each)) for each in item.relations.depends_on],
        filed_during=_named_text(item.relations.filed_during),
        filed_here=[],
        superseded_by=superseded_by_of(item),
        supersedes=[],
        amends=_named_text(item.relations.amends),
        amended_by=[],
        **criterion_parts(item.criterion),
    )


def holder_of(
    task_id: TaskId, item_ids: Iterable[WorkItemId], load_work_item: LoadWorkItem
) -> WorkItemState:
    """The work item among those of the ids that holds the Task of that id.

    Raises TaskNotFoundError when none does.
    """
    for item_id in item_ids:
        item = load_work_item(item_id)
        if any(task.id == task_id for task in item.tasks):
            return item
    raise TaskNotFoundError(task_id)


def add_work_item(
    *,
    kind: Kind,
    title: str,
    criterion: Criterion,
    description: str,
    find_work_item_rows: FindWorkItemRows,
    save_work_item: SaveWorkItem,
    now: Now,
    parent: Parent = STANDALONE,
    depends_on: Iterable[WorkItemId] = (),
    filed_during: WorkItemId | None = None,
    amends: WorkItemId | None = None,
) -> WorkItemId:
    """Add a work item of that kind to Backlog under its next free id and return that id.

    It stands alone unless a Feature is named as its parent, depends on the work items given,
    is filed during the one given and amends the one given. The rows found are those of the
    kind. Raises EmptyPartError when the title is blank and CriterionError when the criterion is
    not of the form the kind takes; nothing is saved.
    """
    taken = [parse_work_item_id(kind, row.id) for row in find_work_item_rows()]
    item_id = next_work_item_id(kind, taken)
    item = make_work_item(
        item_id, title, criterion, description, now(), parent, depends_on, filed_during, amends
    )
    save_work_item(item)
    return item.id


def add_task(
    *,
    parent: WorkItemId,
    title: str,
    expected_output: str,
    description: str,
    load_work_item: LoadWorkItem,
    find_task_ids: FindTaskIds,
    save_work_item: SaveWorkItem,
    now: Now,
) -> TaskId:
    """Write a Task for the work item of the parent id, under the next free id; return that id.

    Raises WorkItemNotFoundError when the record holds no such item, CompletedAlreadyError when
    it is completed, and EmptyPartError when the title or the expected output is blank; nothing
    is saved.
    """
    item = still_open(load_work_item(parent))
    taken = [parse_task_id(text) for text in find_task_ids()]
    task = make_task(next_task_id(taken), title, expected_output, description, now())
    save_work_item(append_task(item, task))
    return task.id


def remove_work_item(
    *,
    item_id: WorkItemId,
    reason: str,
    load_work_item: LoadWorkItem,
    save_work_item: SaveWorkItem,
    now: Now,
    superseded_by: WorkItemId | None = None,
) -> None:
    """Remove the work item in Backlog of that id now, for the reason, and save it whole.

    It names the work item that supersedes it when one is given. Raises WorkItemNotFoundError
    when the record holds no such item, EmptyPartError when the reason is blank with none named,
    StartedAlreadyError when the item is started, CompletedAlreadyError when it is completed,
    RemovedAlreadyError when it is removed and RelationError when it names itself; nothing is
    saved.
    """
    save_work_item(removed_work_item(load_work_item(item_id), reason, now(), superseded_by))


def amend_work_item(
    *,
    item_id: WorkItemId,
    amendment: Amendment,
    load_work_item: LoadWorkItem,
    save_work_item: SaveWorkItem,
    check_move: CheckMove,
) -> None:
    """Rewrite the parts the amendment names of the work item of that id and save it whole.

    A parent named that is not the one it has is a move, checked through check_move before the
    save. Raises WorkItemNotFoundError when the record holds no such item, NoPartError when the
    amendment names no part, EmptyPartError when the title or a part of the criterion is blank,
    StartedAlreadyError when the item is started, CompletedAlreadyError when it is completed
    and the refusal of the check; nothing is saved.
    """
    was = load_work_item(item_id)
    amended = amended_work_item(was, amendment)
    if amended.parent != was.parent:
        check_move(item_id, was.parent, amended.parent)
    save_work_item(amended)


def start_work_item(
    *, item_id: WorkItemId, load_work_item: LoadWorkItem, save_work_item: SaveWorkItem, now: Now
) -> None:
    """Start the work item of that id now and save it whole.

    Raises WorkItemNotFoundError when the record holds no such item, NoTaskError when it has no
    Task, StartedAlreadyError when it is started and CompletedAlreadyError when it is completed;
    nothing is saved.
    """
    save_work_item(started_work_item(load_work_item(item_id), now()))


def start_task(
    *, task_id: TaskId, load_holder: LoadHolder, save_work_item: SaveWorkItem, now: Now
) -> WorkItemId:
    """Start the Task of that id now, save its work item whole and return the id of that item.

    Raises TaskNotFoundError when no item holds the Task, ItemInBacklogError when its item is in
    Backlog, StartedAlreadyError when it is started and CompletedAlreadyError when it is
    completed; nothing is saved.
    """
    item = load_holder(task_id)
    save_work_item(started_task(item, task_id, now()))
    return item.id


def block_task(
    *,
    task_id: TaskId,
    reason: str,
    waiting_on: str,
    load_holder: LoadHolder,
    save_work_item: SaveWorkItem,
    now: Now,
) -> WorkItemId:
    """Block the started Task of that id now, save its work item whole and return its id.

    Raises TaskNotFoundError when no item holds the Task, NotStartedError when it is in Backlog,
    BlockedError when it is blocked already, CompletedAlreadyError when it is completed and
    EmptyPartError when the reason or what it waits on is blank; nothing is saved.
    """
    item = load_holder(task_id)
    save_work_item(blocked_task(item, task_id, reason, waiting_on, now()))
    return item.id


def unblock_task(
    *, task_id: TaskId, load_holder: LoadHolder, save_work_item: SaveWorkItem
) -> WorkItemId:
    """Unblock the blocked Task of that id, save its work item whole and return its id.

    Raises TaskNotFoundError when no item holds the Task and NotBlockedError when it is not
    blocked; nothing is saved.
    """
    item = load_holder(task_id)
    save_work_item(unblocked_task(item, task_id))
    return item.id


def complete_task(
    *,
    task_id: TaskId,
    commit: Evidence,
    load_holder: LoadHolder,
    save_work_item: SaveWorkItem,
    now: Now,
) -> WorkItemId:
    """Complete the Task of that id now, in that commit or none, save its item and return its id.

    Raises TaskNotFoundError when no item holds the Task, NotStartedError when it is in Backlog
    and CompletedAlreadyError when it is completed; nothing is saved.
    """
    item = load_holder(task_id)
    save_work_item(completed_task(item, task_id, now(), commit))
    return item.id


def note_work_item(
    *,
    item_id: WorkItemId,
    kind: KnowledgeKind,
    text: str,
    load_work_item: LoadWorkItem,
    save_work_item: SaveWorkItem,
    now: Now,
) -> None:
    """Keep a line of that kind and text on the work item of that id, in any state, and save it.

    The line goes after the lines the item keeps. Raises WorkItemNotFoundError when the record
    holds no such item and EmptyPartError when the text is blank; nothing is saved.
    """
    line = make_knowledge_line(kind, text, now())
    save_work_item(noted_work_item(load_work_item(item_id), line))
