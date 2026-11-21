"""The file of a work item: its criterion table, and the write that reads itself back."""

from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, assert_never

import tomli_w
from pydantic import BaseModel, ConfigDict, Field

from flowgraph.criterion import Scenario, make_commit, make_scenario
from flowgraph.task import (
    CompletedTask,
    StartedTask,
    Task,
    TaskRow,
    TaskState,
    completed,
    make_task,
    parse_task_id,
    started,
    task_id_text,
    task_state_name,
)


class CriterionFile(BaseModel):
    """The criterion table of a work item file: its Given / When / Then."""

    model_config = ConfigDict(extra="forbid")

    given: str
    when: str
    then: str


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


class CompletedTaskFile(BaseModel):
    """One table of the tasks of a work item file: a completed Task, with its commit."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["completed"]
    title: str
    description: str = ""
    expected_output: str
    created: datetime
    started: datetime
    completed: datetime
    commit: str


# One table of the tasks of a work item file past Backlog, told apart by its state line.
HeldTask = Annotated[TaskFile | StartedTaskFile | CompletedTaskFile, Field(discriminator="state")]


# A Task table of a work item file, in any state.
AnyTaskFile = TaskFile | StartedTaskFile | CompletedTaskFile


def criterion_primitives(scenario: Scenario) -> dict[str, object]:
    """The criterion as the primitives its table holds."""
    return {"given": scenario.given, "when": scenario.when, "then": scenario.then}


def scenario_held(held: CriterionFile) -> Scenario:
    """The criterion a validated table holds, built through its constructor."""
    return make_scenario(held.given, held.when, held.then)


def task_primitives(task: TaskState) -> dict[str, object]:
    """The Task as the primitives its table holds; a description only when there is one."""
    described = {"description": task.description} if task.description else {}
    match task:
        case Task():
            moves: dict[str, object] = {}
        case StartedTask():
            moves = {"started": task.started}
        case CompletedTask():
            moves = {
                "started": task.started,
                "completed": task.completed,
                "commit": task.commit.sha,
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
        case CompletedTaskFile():
            return completed(started(task, held.started), held.completed, make_commit(held.commit))
        case _ as unreachable:
            assert_never(unreachable)


def task_row(held: AnyTaskFile) -> TaskRow:
    """The Task a validated table holds, as the row a view reads, a commit once completed."""
    commit = held.commit if isinstance(held, CompletedTaskFile) else ""
    return TaskRow(held.id, held.title, held.expected_output, held.description, held.state, commit)


def write_checked(
    path: Path,
    primitives: Mapping[str, object],
    holds: Callable[[Path], bool],
    mismatch: Exception,
) -> None:
    """Write the primitives as the TOML file at the path, once the written file holds them.

    The file is written beside the path and replaces it only when holds says the written file
    reads back as meant. Raises mismatch otherwise; the file at the path is then as it was.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    beside = path.with_name(f"{path.name}.tmp")
    beside.write_text(tomli_w.dumps(primitives), encoding="utf-8")
    if not holds(beside):
        beside.unlink()
        raise mismatch
    beside.replace(path)
