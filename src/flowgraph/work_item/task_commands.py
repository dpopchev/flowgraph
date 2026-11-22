"""The commands on a Task of a work item: each loads the item that holds it, moves it, saves it."""

from collections.abc import Callable, Iterable

from flowgraph.criterion import Evidence
from flowgraph.record import Now
from flowgraph.task import (
    TaskId,
    TaskNotFoundError,
    make_task,
    next_task_id,
    parse_task_id,
)
from flowgraph.work_item.id import WorkItemId
from flowgraph.work_item.model import (
    FindTaskIds,
    LoadWorkItem,
    SaveWorkItem,
    WorkItemState,
    append_task,
)
from flowgraph.work_item.moves import still_open
from flowgraph.work_item.tasks import blocked_task, completed_task, started_task, unblocked_task

# The work item that holds the Task of that id, whole; raises TaskNotFoundError when none does.
LoadHolder = Callable[[TaskId], WorkItemState]


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
    check: str | None = None,
) -> TaskId:
    """Write a Task for the work item of the parent id, under the next free id; return that id.

    Raises WorkItemNotFoundError when the record holds no such item, CompletedAlreadyError when
    it is completed, and EmptyPartError when the title, the expected output or a check given is
    blank; nothing is saved.
    """
    item = still_open(load_work_item(parent))
    taken = [parse_task_id(text) for text in find_task_ids()]
    task = make_task(next_task_id(taken), title, expected_output, description, now(), check)
    save_work_item(append_task(item, task))
    return task.id


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
