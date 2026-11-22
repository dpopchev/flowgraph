"""The check of a Task: the command that checks it, kept by every move of the Task."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError, make_commit
from flowgraph.task import (
    Task,
    TaskState,
    blocked,
    completed,
    make_task,
    make_task_id,
    row_of,
    started,
    unblocked,
)

pytestmark = pytest.mark.model

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
CHECKED = make_task(make_task_id(1), "a task", "an output", "", CREATED, "make test")
BEGUN = started(CHECKED, ON)
STUCK = blocked(BEGUN, "a reason", "someone", ON)
MOVED: list[TaskState] = [
    CHECKED,
    BEGUN,
    STUCK,
    unblocked(STUCK),
    completed(BEGUN, ON, make_commit("abc1234")),
]


def test_a_task_made_with_no_check_holds_none() -> None:
    assert make_task(make_task_id(1), "a task", "an output", "", CREATED).check is None


@pytest.mark.parametrize("task", MOVED, ids=["backlog", "started", "blocked", "unblocked", "done"])
def test_every_move_of_a_task_carries_its_check(task: TaskState) -> None:
    assert task.check == "make test"


@pytest.mark.parametrize("check", ["", "  ", "\n"])
def test_a_blank_check_is_refused_by_name(check: str) -> None:
    with pytest.raises(EmptyPartError, match=r"^check is empty$"):
        make_task(make_task_id(1), "a task", "an output", "", CREATED, check)


def test_the_row_of_a_task_reads_its_check() -> None:
    assert row_of(BEGUN).check == "make test"


def test_the_row_of_a_task_with_no_check_reads_none() -> None:
    task: Task = make_task(make_task_id(1), "a task", "an output", "", CREATED)
    assert row_of(task).check == ""
