"""The evidence of a completed Task: its commit, or none when it is completed without one."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import NO_COMMIT, make_commit
from flowgraph.task import (
    CompletedTask,
    TaskRow,
    all_completed,
    completed,
    completed_among,
    make_task,
    make_task_id,
    row_of,
    started,
)

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 1, 3, 9, 0, 0, 500, tzinfo=UTC)
COMMIT = make_commit("abc1234")
FIRST = make_task(make_task_id(1), "a task", "an output", "", CREATED)
SECOND = make_task(make_task_id(2), "another task", "another output", "", CREATED)
BEGUN = started(FIRST, ON)
DONE = completed(BEGUN, LATER, NO_COMMIT)


@pytest.mark.model
def test_a_started_task_is_completed_on_the_second_without_a_commit() -> None:
    assert completed(BEGUN, LATER, NO_COMMIT) == CompletedTask(
        make_task_id(1),
        "a task",
        "an output",
        "",
        CREATED,
        ON,
        LATER.replace(microsecond=0),
        NO_COMMIT,
    )


@pytest.mark.model
def test_one_task_among_them_is_completed_without_a_commit_and_the_rest_stay() -> None:
    assert completed_among((BEGUN, SECOND), make_task_id(1), LATER, NO_COMMIT) == (DONE, SECOND)


@pytest.mark.model
def test_the_tasks_completed_with_a_commit_or_without_one_are_all_completed() -> None:
    done = (DONE, completed(started(SECOND, ON), LATER, COMMIT))
    assert all_completed(done, "S-0001") == done


@pytest.mark.view
def test_the_row_of_a_task_completed_without_a_commit_carries_none() -> None:
    assert row_of(DONE) == TaskRow("T-0001", "a task", "an output", "", "completed")
