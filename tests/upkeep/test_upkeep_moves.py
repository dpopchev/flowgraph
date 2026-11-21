"""Moving an Upkeep: it starts with a Task, its Tasks move under it, then it completes."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.task import (
    CompletedAlreadyError,
    ItemInBacklogError,
    NoTaskError,
    NotStartedError,
    OpenTaskError,
    StartedAlreadyError,
    completed,
    make_task,
    make_task_id,
    started,
)
from flowgraph.upkeep import (
    CompletedUpkeep,
    StartedUpkeep,
    append_task,
    completed_task,
    completed_upkeep,
    make_upkeep,
    make_upkeep_id,
    started_task,
    started_upkeep,
    still_open,
)

pytestmark = pytest.mark.model

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
ON = datetime(2026, 1, 2, tzinfo=UTC)
COMMIT = make_commit("abc1234")
SCENARIO = make_scenario("a behavior", "it runs", "it still holds")
BARE = make_upkeep(make_upkeep_id(1), "a title", SCENARIO, "", CREATED)
TASK = make_task(make_task_id(1), "a task", "an output", "", CREATED)
UPKEEP = append_task(BARE, TASK)
BEGUN = started_task(started_upkeep(UPKEEP, ON), make_task_id(1), ON)
HALF = completed_task(BEGUN, make_task_id(1), ON, COMMIT)


def test_an_upkeep_with_a_task_starts_with_its_task_in_backlog() -> None:
    assert started_upkeep(UPKEEP, ON) == StartedUpkeep(
        make_upkeep_id(1), "a title", SCENARIO, "", CREATED, ON, (TASK,)
    )


def test_an_upkeep_without_a_task_is_refused_by_its_id() -> None:
    with pytest.raises(NoTaskError, match=r"^U-0001 has no Task to start with$"):
        started_upkeep(BARE, ON)


def test_a_started_upkeep_does_not_start_again() -> None:
    with pytest.raises(StartedAlreadyError, match=r"^U-0001 is started already$"):
        started_upkeep(started_upkeep(UPKEEP, ON), ON)


def test_a_task_of_an_upkeep_in_backlog_is_refused_naming_both() -> None:
    with pytest.raises(ItemInBacklogError, match=r"^T-0001 cannot start: U-0001 is in Backlog$"):
        started_task(UPKEEP, make_task_id(1), ON)


def test_a_task_of_an_upkeep_in_backlog_does_not_complete() -> None:
    with pytest.raises(NotStartedError, match=r"^T-0001 is in Backlog: start it first$"):
        completed_task(UPKEEP, make_task_id(1), ON, COMMIT)


def test_a_started_task_of_a_started_upkeep_completes_in_its_commit() -> None:
    assert HALF.tasks == (completed(started(TASK, ON), ON, COMMIT),)


def test_an_upkeep_whose_tasks_are_completed_completes_in_its_commit() -> None:
    assert completed_upkeep(HALF, ON, make_commit("def5678")) == CompletedUpkeep(
        make_upkeep_id(1),
        "a title",
        SCENARIO,
        "",
        CREATED,
        ON,
        ON,
        make_commit("def5678"),
        (completed(started(TASK, ON), ON, COMMIT),),
    )


def test_an_upkeep_with_a_task_open_is_refused_naming_it() -> None:
    with pytest.raises(OpenTaskError, match=r"^U-0001 has Tasks to complete first: T-0001$"):
        completed_upkeep(BEGUN, ON, COMMIT)


def test_an_upkeep_in_backlog_does_not_complete() -> None:
    with pytest.raises(NotStartedError, match=r"^U-0001 is in Backlog: start it first$"):
        completed_upkeep(UPKEEP, ON, COMMIT)


def test_a_completed_upkeep_takes_no_new_task() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^U-0001 is completed already$"):
        still_open(completed_upkeep(HALF, ON, COMMIT))
