"""The views and the commands of an Upkeep: each loads it whole, moves it and saves it."""

from flowgraph.criterion import Commit, make_scenario
from flowgraph.record import Now
from flowgraph.task import (
    TaskId,
    TaskNotFoundError,
    TaskRow,
    make_task,
    next_task_id,
    parse_task_id,
    task_id_text,
)
from flowgraph.upkeep.model import (
    FindTaskIds,
    FindUpkeepRows,
    LoadUpkeep,
    SaveUpkeep,
    UpkeepDetail,
    UpkeepId,
    UpkeepRow,
    UpkeepState,
    append_task,
    commit_sha,
    completed_task,
    completed_upkeep,
    make_upkeep,
    next_upkeep_id,
    parse_upkeep_id,
    started_task,
    started_upkeep,
    state_name,
    still_open,
    upkeep_id_text,
)


def upkeep_row(upkeep: UpkeepState) -> UpkeepRow:
    """The Upkeep as the row a view reads."""
    return UpkeepRow(
        upkeep_id_text(upkeep.id), upkeep.title, state_name(upkeep), commit_sha(upkeep)
    )


def upkeep_detail(upkeep: UpkeepState) -> UpkeepDetail:
    """The Upkeep with its criterion and its Tasks as the plain data a view reads."""
    return UpkeepDetail(
        id=upkeep_id_text(upkeep.id),
        title=upkeep.title,
        state=state_name(upkeep),
        description=upkeep.description,
        given=upkeep.scenario.given,
        when=upkeep.scenario.when,
        then=upkeep.scenario.then,
        tasks=[
            TaskRow(
                task_id_text(task.id),
                task.title,
                task.expected_output,
                task.description,
                state_name(task),
                commit_sha(task),
            )
            for task in upkeep.tasks
        ],
        commit=commit_sha(upkeep),
    )


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
    taken = [parse_upkeep_id(row.id) for row in find_upkeep_rows()]
    upkeep = make_upkeep(
        next_upkeep_id(taken), title, make_scenario(given, when, then), description, now()
    )
    save_upkeep(upkeep)
    return upkeep.id


def add_task(
    *,
    parent: str,
    title: str,
    expected_output: str,
    description: str,
    load_upkeep: LoadUpkeep,
    find_task_ids: FindTaskIds,
    save_upkeep: SaveUpkeep,
    now: Now,
) -> TaskId:
    """Write a Task for the Upkeep named as parent, under the next free id, and return that id.

    Raises UpkeepIdError when the parent is no Upkeep id, UpkeepNotFoundError when the record holds
    no such Upkeep, CompletedAlreadyError when it is completed, and EmptyPartError when the title
    or the expected output is blank; nothing is saved.
    """
    upkeep = still_open(load_upkeep(parse_upkeep_id(parent)))
    taken = [parse_task_id(text) for text in find_task_ids()]
    task = make_task(next_task_id(taken), title, expected_output, description, now())
    save_upkeep(append_task(upkeep, task))
    return task.id


def start_upkeep(
    *, upkeep_id: UpkeepId, load_upkeep: LoadUpkeep, save_upkeep: SaveUpkeep, now: Now
) -> None:
    """Start the Upkeep of that id now and save it whole.

    Raises UpkeepNotFoundError when the record holds no such Upkeep, NoTaskError when it has no
    Task and StartedAlreadyError when it is started; nothing is saved.
    """
    save_upkeep(started_upkeep(load_upkeep(upkeep_id), now()))


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
    upkeep = _holder(task_id, find_upkeep_rows, load_upkeep)
    save_upkeep(started_task(upkeep, task_id, now()))
    return upkeep.id


def _holder(
    task_id: TaskId, find_upkeep_rows: FindUpkeepRows, load_upkeep: LoadUpkeep
) -> UpkeepState:
    """The Upkeep that holds the Task of that id; raises TaskNotFoundError when none does."""
    for row in find_upkeep_rows():
        upkeep = load_upkeep(parse_upkeep_id(row.id))
        if any(task.id == task_id for task in upkeep.tasks):
            return upkeep
    raise TaskNotFoundError(task_id)


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
    save_upkeep(completed_upkeep(load_upkeep(upkeep_id), now(), commit))


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
    upkeep = _holder(task_id, find_upkeep_rows, load_upkeep)
    save_upkeep(completed_task(upkeep, task_id, now(), commit))
    return upkeep.id
