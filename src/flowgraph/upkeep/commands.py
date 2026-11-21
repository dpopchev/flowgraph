"""The views and the commands of an Upkeep: the work item commands, on the upkeeps of the record."""

from flowgraph import work_item
from flowgraph.criterion import Commit
from flowgraph.record import Now
from flowgraph.task import TaskId
from flowgraph.upkeep.model import (
    UPKEEP,
    FindUpkeepRows,
    LoadUpkeep,
    SaveUpkeep,
    UpkeepId,
    parse_upkeep_id,
)

upkeep_row = work_item.work_item_row
upkeep_detail = work_item.work_item_detail


def add_upkeep(
    *,
    title: str,
    given: str,
    when: str,
    then: str,
    description: str,
    find_upkeep_rows: FindUpkeepRows,
    save_upkeep: SaveUpkeep,
    now: Now,
) -> UpkeepId:
    """Add an Upkeep to Backlog under the next free id and return that id.

    Raises EmptyPartError when the title or a part of the criterion is blank; nothing is saved.
    """
    return work_item.add_work_item(
        kind=UPKEEP,
        title=title,
        given=given,
        when=when,
        then=then,
        description=description,
        find_work_item_rows=find_upkeep_rows,
        save_work_item=save_upkeep,
        now=now,
    )


def add_task(
    *,
    parent: str,
    title: str,
    expected_output: str,
    description: str,
    load_upkeep: LoadUpkeep,
    find_task_ids: work_item.FindTaskIds,
    save_upkeep: SaveUpkeep,
    now: Now,
) -> TaskId:
    """Write a Task for the Upkeep named as parent, under the next free id, and return that id.

    Raises UpkeepIdError when the parent is no Upkeep id, UpkeepNotFoundError when the record holds
    no such Upkeep, CompletedAlreadyError when it is completed, and EmptyPartError when the title
    or the expected output is blank; nothing is saved.
    """
    return work_item.add_task(
        parent=parse_upkeep_id(parent),
        title=title,
        expected_output=expected_output,
        description=description,
        load_work_item=load_upkeep,
        find_task_ids=find_task_ids,
        save_work_item=save_upkeep,
        now=now,
    )


def start_upkeep(
    *, upkeep_id: UpkeepId, load_upkeep: LoadUpkeep, save_upkeep: SaveUpkeep, now: Now
) -> None:
    """Start the Upkeep of that id now and save it whole.

    Raises UpkeepNotFoundError when the record holds no such Upkeep, NoTaskError when it has no
    Task and StartedAlreadyError when it is started; nothing is saved.
    """
    work_item.start_work_item(
        item_id=upkeep_id, load_work_item=load_upkeep, save_work_item=save_upkeep, now=now
    )


def _load_holder(find_upkeep_rows: FindUpkeepRows, load_upkeep: LoadUpkeep) -> work_item.LoadHolder:
    """The load of the Upkeep that holds a Task, among the upkeeps of the record."""
    return lambda task_id: work_item.holder_of(
        task_id, [parse_upkeep_id(row.id) for row in find_upkeep_rows()], load_upkeep
    )


def start_task(
    *,
    task_id: TaskId,
    find_upkeep_rows: FindUpkeepRows,
    load_upkeep: LoadUpkeep,
    save_upkeep: SaveUpkeep,
    now: Now,
) -> UpkeepId:
    """Start the Task of that id now, save its Upkeep whole and return the id of that Upkeep.

    Raises TaskNotFoundError when no Upkeep holds the Task, ItemInBacklogError when its Upkeep is
    in Backlog, StartedAlreadyError when it is started and CompletedAlreadyError when it is
    completed; nothing is saved.
    """
    return work_item.start_task(
        task_id=task_id,
        load_holder=_load_holder(find_upkeep_rows, load_upkeep),
        save_work_item=save_upkeep,
        now=now,
    )


def complete_upkeep(
    *,
    upkeep_id: UpkeepId,
    commit: Commit,
    load_upkeep: LoadUpkeep,
    save_upkeep: SaveUpkeep,
    now: Now,
) -> None:
    """Complete the Upkeep of that id now in that commit and save it whole.

    Raises UpkeepNotFoundError when the record holds no such Upkeep, NotStartedError when it is in
    Backlog, OpenTaskError when a Task of it is not completed and CompletedAlreadyError when it
    is completed; nothing is saved.
    """
    work_item.complete_work_item(
        item_id=upkeep_id,
        commit=commit,
        load_work_item=load_upkeep,
        save_work_item=save_upkeep,
        now=now,
    )


def complete_task(
    *,
    task_id: TaskId,
    commit: Commit,
    find_upkeep_rows: FindUpkeepRows,
    load_upkeep: LoadUpkeep,
    save_upkeep: SaveUpkeep,
    now: Now,
) -> UpkeepId:
    """Complete the Task of that id now in that commit, save its Upkeep whole and return its id.

    Raises TaskNotFoundError when no Upkeep holds the Task, NotStartedError when it is in Backlog
    and CompletedAlreadyError when it is completed; nothing is saved.
    """
    return work_item.complete_task(
        task_id=task_id,
        commit=commit,
        load_holder=_load_holder(find_upkeep_rows, load_upkeep),
        save_work_item=save_upkeep,
        now=now,
    )
