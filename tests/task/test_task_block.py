"""The block of a Task: a started Task is blocked with its reason and what it waits on."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError, make_commit
from flowgraph.task import (
    BlockedError,
    BlockedTask,
    CompletedAlreadyError,
    NotStartedError,
    OpenTaskError,
    TaskNotFoundError,
    TaskRow,
    TaskState,
    all_completed,
    blocked,
    blocked_among,
    completed,
    make_task,
    make_task_id,
    row_of,
    started,
    task_state_name,
)

pytestmark = pytest.mark.model

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 1, 3, 9, 0, 0, 500, tzinfo=UTC)
COMMIT = make_commit("abc1234")
FIRST = make_task(make_task_id(1), "a task", "an output", "", CREATED)
SECOND = make_task(make_task_id(2), "another task", "another output", "", CREATED)
BEGUN = started(FIRST, ON)
STUCK = blocked(BEGUN, "a reason", "someone", LATER)


def test_a_started_task_is_blocked_with_its_reason_since_and_what_it_waits_on() -> None:
    assert blocked(BEGUN, "a reason", "someone", LATER) == BlockedTask(
        make_task_id(1),
        "a task",
        "an output",
        "",
        CREATED,
        ON,
        "a reason",
        LATER.replace(microsecond=0),
        "someone",
    )


def test_a_task_in_backlog_is_not_blocked() -> None:
    with pytest.raises(NotStartedError, match=r"^T-0001 is in Backlog: start it first$"):
        blocked(FIRST, "a reason", "someone", LATER)


def test_a_blocked_task_is_not_blocked_once_more() -> None:
    with pytest.raises(BlockedError, match=r"^T-0001 is blocked already$"):
        blocked(STUCK, "a reason", "someone", LATER)


def test_a_completed_task_is_not_blocked() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^T-0001 is completed already$"):
        blocked(completed(BEGUN, LATER, COMMIT), "a reason", "someone", LATER)


@pytest.mark.parametrize(
    ("reason", "waiting_on", "part"),
    [(" ", "someone", "reason"), ("a reason", "", "waiting on")],
    ids=["reason", "waiting-on"],
)
def test_a_block_with_a_blank_part_is_refused_naming_it(
    reason: str, waiting_on: str, part: str
) -> None:
    with pytest.raises(EmptyPartError, match=rf"^{part} is empty$"):
        blocked(BEGUN, reason, waiting_on, LATER)


def test_a_blocked_task_is_not_started() -> None:
    with pytest.raises(BlockedError, match=r"^T-0001 is blocked: unblock it first$"):
        started(STUCK, LATER)


def test_a_blocked_task_is_not_completed() -> None:
    with pytest.raises(BlockedError, match=r"^T-0001 is blocked: unblock it first$"):
        completed(STUCK, LATER, COMMIT)


def test_one_task_among_them_is_blocked_and_the_rest_stay() -> None:
    tasks: tuple[TaskState, ...] = (BEGUN, SECOND)
    assert blocked_among(tasks, make_task_id(1), "a reason", "someone", LATER) == (STUCK, SECOND)


def test_a_task_they_do_not_hold_is_not_blocked() -> None:
    with pytest.raises(TaskNotFoundError, match=r"^no Task T-0003 in the record$"):
        blocked_among((BEGUN, SECOND), make_task_id(3), "a reason", "someone", LATER)


def test_a_blocked_task_is_written_as_blocked() -> None:
    assert task_state_name(STUCK) == "blocked"


def test_a_blocked_task_is_one_still_to_complete() -> None:
    with pytest.raises(OpenTaskError, match=r"^CH-0001 has Tasks to complete first: T-0001$"):
        all_completed((STUCK,), "CH-0001")


def test_the_row_of_a_blocked_task_names_its_reason_and_what_it_waits_on() -> None:
    assert row_of(STUCK) == TaskRow(
        "T-0001", "a task", "an output", "", "blocked", reason="a reason", waiting_on="someone"
    )


def test_the_row_of_a_completed_task_names_its_commit() -> None:
    assert row_of(completed(BEGUN, LATER, COMMIT)) == TaskRow(
        "T-0001", "a task", "an output", "", "completed", "abc1234"
    )
