"""The Tasks of a work item: one of them starts or completes by its id, the rest stay."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_commit
from flowgraph.task import (
    CompletedAlreadyError,
    NotStartedError,
    OpenTaskError,
    StartedAlreadyError,
    TaskNotFoundError,
    TaskState,
    completed,
    make_task,
    make_task_id,
    started,
)
from flowgraph.task_list import all_completed, completed_among, started_among, task_of

pytestmark = pytest.mark.model

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, 500, tzinfo=UTC)
COMMIT = make_commit("abc1234")
FIRST = make_task(make_task_id(1), "a task", "an output", "", CREATED)
SECOND = make_task(make_task_id(2), "another task", "another output", "", CREATED)
TASKS: tuple[TaskState, ...] = (FIRST, SECOND)


def test_the_task_of_an_id_is_found_among_them() -> None:
    assert task_of(TASKS, make_task_id(2)) == SECOND


def test_a_task_they_do_not_hold_is_refused_by_its_id() -> None:
    with pytest.raises(TaskNotFoundError, match=r"^no Task T-0003 in the record$"):
        task_of(TASKS, make_task_id(3))


def test_one_task_starts_and_the_rest_stay() -> None:
    assert started_among(TASKS, make_task_id(2), ON) == (FIRST, started(SECOND, ON))


def test_a_started_task_does_not_start_again() -> None:
    begun = started_among(TASKS, make_task_id(1), ON)
    with pytest.raises(StartedAlreadyError, match=r"^T-0001 is started already$"):
        started_among(begun, make_task_id(1), ON)


def test_a_task_they_do_not_hold_does_not_start() -> None:
    with pytest.raises(TaskNotFoundError, match=r"^no Task T-0003 in the record$"):
        started_among(TASKS, make_task_id(3), ON)


def test_one_started_task_completes_and_the_rest_stay() -> None:
    begun = started_among(TASKS, make_task_id(1), ON)
    assert completed_among(begun, make_task_id(1), ON, COMMIT) == (
        completed(started(FIRST, ON), ON, COMMIT),
        SECOND,
    )


def test_a_task_in_backlog_does_not_complete() -> None:
    with pytest.raises(NotStartedError, match=r"^T-0002 is in Backlog: start it first$"):
        completed_among(TASKS, make_task_id(2), ON, COMMIT)


def test_a_completed_task_does_not_complete_again() -> None:
    done = completed_among(started_among(TASKS, make_task_id(1), ON), make_task_id(1), ON, COMMIT)
    with pytest.raises(CompletedAlreadyError, match=r"^T-0001 is completed already$"):
        completed_among(done, make_task_id(1), ON, COMMIT)


def test_tasks_all_completed_are_returned_as_completed() -> None:
    done = completed(started(FIRST, ON), ON, COMMIT)
    assert all_completed((done,), "S-0001") == (done,)


def test_tasks_not_all_completed_are_refused_naming_the_holder_and_the_rest() -> None:
    done = completed(started(FIRST, ON), ON, COMMIT)
    with pytest.raises(OpenTaskError, match=r"^U-0001 has Tasks to complete first: T-0002$"):
        all_completed((done, SECOND), "U-0001")
