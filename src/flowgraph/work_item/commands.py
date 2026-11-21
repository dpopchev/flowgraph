"""The views and the commands of a work item: each command loads it whole, moves it, saves it."""

from collections.abc import Callable, Iterable

from flowgraph.criterion import Commit, Criterion, criterion_parts
from flowgraph.record import Now
from flowgraph.task import (
    TaskId,
    TaskNotFoundError,
    make_task,
    next_task_id,
    parse_task_id,
    row_of,
)
from flowgraph.work_item.amend import Amendment, amended_work_item
from flowgraph.work_item.model import (
    FindTaskIds,
    FindWorkItemRows,
    Kind,
    LoadWorkItem,
    SaveWorkItem,
    WorkItemDetail,
    WorkItemId,
    WorkItemRow,
    WorkItemState,
    append_task,
    commit_sha,
    completed_work_item,
    make_work_item,
    next_work_item_id,
    parse_work_item_id,
    started_work_item,
    state_name,
    still_open,
    work_item_id_text,
)
from flowgraph.work_item.removal import reason_of, removed_work_item
from flowgraph.work_item.tasks import blocked_task, completed_task, started_task, unblocked_task

# The work item that holds the Task of that id, whole; raises TaskNotFoundError when none does.
LoadHolder = Callable[[TaskId], WorkItemState]


def work_item_row(item: WorkItemState) -> WorkItemRow:
    """The work item as the row a view reads."""
    return WorkItemRow(
        work_item_id_text(item.id),
        item.title,
        state_name(item),
        commit_sha(item),
        reason_of(item),
        created=item.created,
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
) -> WorkItemId:
    """Add a work item of that kind to Backlog under its next free id and return that id.

    The rows found are those of the kind. Raises EmptyPartError when the title is blank and
    CriterionError when the criterion is not of the form the kind takes; nothing is saved.
    """
    taken = [parse_work_item_id(kind, row.id) for row in find_work_item_rows()]
    item = make_work_item(next_work_item_id(kind, taken), title, criterion, description, now())
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
) -> None:
    """Remove the work item in Backlog of that id now, for the reason, and save it whole.

    Raises WorkItemNotFoundError when the record holds no such item, EmptyPartError when the
    reason is blank, StartedAlreadyError when the item is started, CompletedAlreadyError when it
    is completed and RemovedAlreadyError when it is removed; nothing is saved.
    """
    save_work_item(removed_work_item(load_work_item(item_id), reason, now()))


def amend_work_item(
    *,
    item_id: WorkItemId,
    amendment: Amendment,
    load_work_item: LoadWorkItem,
    save_work_item: SaveWorkItem,
) -> None:
    """Rewrite the parts the amendment names of the work item of that id and save it whole.

    Raises WorkItemNotFoundError when the record holds no such item, NoPartError when the
    amendment names no part, EmptyPartError when the title or a part of the criterion is blank,
    StartedAlreadyError when the item is started and CompletedAlreadyError when it is completed;
    nothing is saved.
    """
    save_work_item(amended_work_item(load_work_item(item_id), amendment))


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


def complete_work_item(
    *,
    item_id: WorkItemId,
    commit: Commit,
    load_work_item: LoadWorkItem,
    save_work_item: SaveWorkItem,
    now: Now,
    decision: str | None = None,
) -> None:
    """Complete the work item of that id now in that commit and save it whole.

    A work item that states a hypothesis takes the decision that answers it. Raises
    WorkItemNotFoundError when the record holds no such item, NotStartedError when it is in
    Backlog, OpenTaskError when a Task of it is not completed, DecisionError when a hypothesis
    has no decision or another criterion is given one, and CompletedAlreadyError when it is
    completed; nothing is saved.
    """
    save_work_item(completed_work_item(load_work_item(item_id), now(), commit, decision))


def complete_task(
    *,
    task_id: TaskId,
    commit: Commit,
    load_holder: LoadHolder,
    save_work_item: SaveWorkItem,
    now: Now,
) -> WorkItemId:
    """Complete the Task of that id now in that commit, save its work item and return its id.

    Raises TaskNotFoundError when no item holds the Task, NotStartedError when it is in Backlog
    and CompletedAlreadyError when it is completed; nothing is saved.
    """
    item = load_holder(task_id)
    save_work_item(completed_task(item, task_id, now(), commit))
    return item.id
