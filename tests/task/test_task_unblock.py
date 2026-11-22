"""The unblock of a Task: a blocked Task is started again with the started time it had."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_commit
from flowgraph.task import (
    NotBlockedError,
    TaskNotFoundError,
    TaskState,
    blocked,
    completed,
    make_task,
    make_task_id,
    started,
    unblocked,
    unblocked_among,
)

pytestmark = pytest.mark.model

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 1, 3, 9, 0, 0, tzinfo=UTC)
FIRST = make_task(make_task_id(1), "a task", "an output", "", CREATED)
SECOND = make_task(make_task_id(2), "another task", "another output", "", CREATED)
BEGUN = started(FIRST, ON)
STUCK = blocked(BEGUN, "a reason", "someone", LATER)


def test_a_blocked_task_is_started_again_with_the_started_time_it_had() -> None:
    assert unblocked(STUCK) == BEGUN


@pytest.mark.parametrize(
    "task",
    [FIRST, BEGUN, completed(BEGUN, LATER, make_commit("abc1234"))],
    ids=["backlog", "started", "completed"],
)
def test_a_task_that_is_not_blocked_is_not_unblocked(task: TaskState) -> None:
    with pytest.raises(NotBlockedError, match=r"^T-0001 is not blocked$"):
        unblocked(task)


def test_one_task_among_them_is_unblocked_and_the_rest_stay() -> None:
    assert unblocked_among((STUCK, SECOND), make_task_id(1)) == (BEGUN, SECOND)


def test_a_task_they_do_not_hold_is_not_unblocked() -> None:
    with pytest.raises(TaskNotFoundError, match=r"^no Task T-0003 in the record$"):
        unblocked_among((STUCK, SECOND), make_task_id(3))
