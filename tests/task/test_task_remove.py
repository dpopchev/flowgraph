"""The remove of a Task: one in Backlog, started or blocked is removed with its reason."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError, make_commit
from flowgraph.task import (
    CompletedAlreadyError,
    NotBlockedError,
    RemovedTask,
    TaskRemovedError,
    TaskRow,
    TaskState,
    blocked,
    completed,
    make_task,
    make_task_id,
    removed,
    row_of,
    started,
    task_state_name,
    unblocked,
)

pytestmark = pytest.mark.model

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 1, 3, 9, 0, 0, 500, tzinfo=UTC)
COMMIT = make_commit("abc1234")
FIRST = make_task(make_task_id(1), "a task", "an output", "", CREATED, "make test")
BEGUN = started(FIRST, ON)
STUCK = blocked(BEGUN, "no key", "someone", ON)


def test_a_task_in_backlog_is_removed_with_its_reason_its_check_and_its_time_to_the_second() -> (
    None
):
    assert removed(FIRST, "a reason", LATER) == RemovedTask(
        make_task_id(1),
        "a task",
        "an output",
        "",
        CREATED,
        LATER.replace(microsecond=0),
        "a reason",
        "make test",
    )


@pytest.mark.parametrize("task", [BEGUN, STUCK], ids=["started", "blocked"])
def test_a_started_or_blocked_task_is_removed_as_the_one_in_backlog(task: TaskState) -> None:
    assert removed(task, "a reason", LATER) == removed(FIRST, "a reason", LATER)


def test_a_remove_with_a_blank_reason_is_refused() -> None:
    with pytest.raises(EmptyPartError, match=r"^reason is empty$"):
        removed(FIRST, " ", LATER)


def test_a_completed_task_is_not_removed() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^T-0001 is completed already$"):
        removed(completed(BEGUN, LATER, COMMIT), "a reason", LATER)


def test_a_removed_task_is_not_removed_once_more() -> None:
    with pytest.raises(TaskRemovedError, match=r"^T-0001 is removed already$"):
        removed(removed(FIRST, "a reason", LATER), "a reason", LATER)


def test_a_removed_task_is_not_started() -> None:
    with pytest.raises(TaskRemovedError, match=r"^T-0001 is removed already$"):
        started(removed(FIRST, "a reason", LATER), LATER)


def test_a_removed_task_is_not_blocked() -> None:
    with pytest.raises(TaskRemovedError, match=r"^T-0001 is removed already$"):
        blocked(removed(FIRST, "a reason", LATER), "no key", "someone", LATER)


def test_a_removed_task_is_not_completed() -> None:
    with pytest.raises(TaskRemovedError, match=r"^T-0001 is removed already$"):
        completed(removed(FIRST, "a reason", LATER), LATER, COMMIT)


def test_a_removed_task_is_not_unblocked() -> None:
    with pytest.raises(NotBlockedError, match=r"^T-0001 is not blocked$"):
        unblocked(removed(FIRST, "a reason", LATER))


def test_a_removed_task_is_written_as_removed() -> None:
    assert task_state_name(removed(FIRST, "a reason", LATER)) == "removed"


def test_the_row_of_a_removed_task_names_its_reason() -> None:
    assert row_of(removed(FIRST, "a reason", LATER)) == TaskRow(
        "T-0001", "a task", "an output", "", "removed", reason="a reason", check="make test"
    )
