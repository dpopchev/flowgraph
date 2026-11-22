"""The Task tables of a work item file: one per Task, told apart by its state line."""

from datetime import datetime
from typing import Annotated, Literal, assert_never

from pydantic import BaseModel, ConfigDict, Field

from flowgraph.criterion import evidence_written
from flowgraph.item.file import evidence_primitives
from flowgraph.task import (
    BlockedTask,
    CompletedTask,
    StartedTask,
    Task,
    TaskRow,
    TaskState,
    blocked,
    completed,
    make_task,
    parse_task_id,
    started,
    task_id_text,
    task_state_name,
)


class TaskFile(BaseModel):
    """One table of the tasks of a work item file: a Task in Backlog."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["backlog"]
    title: str
    description: str = ""
    expected_output: str
    created: datetime


class StartedTaskFile(BaseModel):
    """One table of the tasks of a started work item file: a started Task."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["started"]
    title: str
    description: str = ""
    expected_output: str
    created: datetime
    started: datetime


class BlockedTaskFile(BaseModel):
    """One table of the tasks of a started work item file: a blocked Task, with its block."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["blocked"]
    title: str
    description: str = ""
    expected_output: str
    created: datetime
    started: datetime
    since: datetime
    reason: str
    waiting_on: str


class CompletedTaskFile(BaseModel):
    """One table of the tasks of a work item file: a completed Task, with the commit it has."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["completed"]
    title: str
    description: str = ""
    expected_output: str
    created: datetime
    started: datetime
    completed: datetime
    commit: str = ""


# One table of the tasks of a work item file past Backlog, told apart by its state line.
HeldTask = Annotated[
    TaskFile | StartedTaskFile | BlockedTaskFile | CompletedTaskFile, Field(discriminator="state")
]


# A Task table of a work item file, in any state.
AnyTaskFile = TaskFile | StartedTaskFile | BlockedTaskFile | CompletedTaskFile


def task_primitives(task: TaskState) -> dict[str, object]:
    """The Task as the primitives its table holds; a description only when there is one."""
    described = {"description": task.description} if task.description else {}
    match task:
        case Task():
            moves: dict[str, object] = {}
        case StartedTask():
            moves = {"started": task.started}
        case BlockedTask():
            moves = {
                "started": task.started,
                "since": task.since,
                "reason": task.reason,
                "waiting_on": task.waiting_on,
            }
        case CompletedTask():
            moves = {
                "started": task.started,
                "completed": task.completed,
                **evidence_primitives(task.commit),
            }
        case _ as unreachable:
            assert_never(unreachable)
    return {
        "id": task_id_text(task.id),
        "state": task_state_name(task),
        "title": task.title,
        **described,
        "expected_output": task.expected_output,
        "created": task.created,
        **moves,
    }


def backlog_task(held: AnyTaskFile) -> Task:
    """The Task a validated table holds, as it was in Backlog, built through its constructor."""
    return make_task(
        parse_task_id(held.id), held.title, held.expected_output, held.description, held.created
    )


def task_held(held: AnyTaskFile) -> TaskState:
    """The Task a validated table holds, built through the moves that took it to its state."""
    task = backlog_task(held)
    match held:
        case TaskFile():
            return task
        case StartedTaskFile():
            return started(task, held.started)
        case BlockedTaskFile():
            begun = started(task, held.started)
            return blocked(begun, held.reason, held.waiting_on, held.since)
        case CompletedTaskFile():
            evidence = evidence_written(held.commit)
            return completed(started(task, held.started), held.completed, evidence)
        case _ as unreachable:
            assert_never(unreachable)


def task_row(held: AnyTaskFile) -> TaskRow:
    """The Task a validated table holds, as the row a view reads.

    The commit it has once completed; its reason and what it waits on while blocked.
    """
    row = TaskRow(held.id, held.title, held.expected_output, held.description, held.state)
    match held:
        case TaskFile() | StartedTaskFile():
            return row
        case BlockedTaskFile():
            row.reason, row.waiting_on = held.reason, held.waiting_on
            return row
        case CompletedTaskFile():
            row.commit = held.commit
            return row
        case _ as unreachable:
            assert_never(unreachable)
