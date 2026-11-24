"""The amend of a Task in Backlog inside its work item, and the command that saves it."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.task import (
    CompletedAlreadyError,
    StartedAlreadyError,
    TaskAmendment,
    TaskNotFoundError,
    completed,
    make_task,
    make_task_id,
    started,
)
from flowgraph.work_item import (
    NoPartError,
    RemovedAlreadyError,
    WorkItem,
    WorkItemState,
    amend_task,
    amended_task,
    append_task,
    blocked_work_item,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    removed_work_item,
    started_task,
    started_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
ID = make_work_item_id(CHORE, 1)
FIRST, SECOND, MISSING = make_task_id(1), make_task_id(2), make_task_id(9)
TASK = make_task(FIRST, "a task", "an output", "", CREATED)
OTHER = make_task(SECOND, "another task", "another output", "how", CREATED, "make test")
BACKLOG: WorkItem = append_task(
    append_task(make_work_item(ID, "a title", make_scenario("a", "b", "c"), "", CREATED), TASK),
    OTHER,
)
STARTED = started_task(started_work_item(BACKLOG, ON), FIRST, ON)
BLOCKED = blocked_work_item(STARTED, "no key", "developer", ON)
DONE = completed(started(TASK, ON), ON, make_commit("abc1234"))
COMPLETED = completed_work_item(replace(STARTED, tasks=(DONE,)), ON, make_commit("abc1234"))
REMOVED = removed_work_item(BACKLOG, "filed by mistake", ON)
AMENDMENT = TaskAmendment(title="a new title")
AMENDED = replace(OTHER, title="a new title")


@pytest.mark.model
def test_a_task_of_a_work_item_in_backlog_is_amended_and_every_other_part_stays() -> None:
    assert amended_task(BACKLOG, SECOND, AMENDMENT) == replace(BACKLOG, tasks=(TASK, AMENDED))


@pytest.mark.model
def test_a_task_in_backlog_of_a_started_work_item_is_amended_and_every_other_part_stays() -> None:
    assert amended_task(STARTED, SECOND, AMENDMENT) == replace(
        STARTED, tasks=(started(TASK, ON), AMENDED)
    )


@pytest.mark.model
def test_a_task_in_backlog_of_a_blocked_work_item_is_amended_and_every_other_part_stays() -> None:
    assert amended_task(BLOCKED, SECOND, AMENDMENT).tasks == (started(TASK, ON), AMENDED)


@pytest.mark.model
def test_the_started_task_of_a_started_work_item_is_refused() -> None:
    with pytest.raises(StartedAlreadyError, match=r"^T-0001 is started already$"):
        amended_task(STARTED, FIRST, AMENDMENT)


@pytest.mark.model
def test_a_task_of_a_completed_work_item_is_refused_with_its_line() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^T-0001 is completed already$"):
        amended_task(COMPLETED, FIRST, AMENDMENT)


@pytest.mark.model
def test_a_task_of_a_removed_work_item_is_refused() -> None:
    with pytest.raises(RemovedAlreadyError):
        amended_task(REMOVED, FIRST, AMENDMENT)


@pytest.mark.model
def test_an_amendment_of_no_part_is_refused_naming_the_task() -> None:
    with pytest.raises(NoPartError, match=r"^amend rewrites no part of T-0002: name one$"):
        amended_task(BACKLOG, SECOND, TaskAmendment())


@pytest.mark.model
def test_the_state_is_refused_before_the_missing_part() -> None:
    with pytest.raises(StartedAlreadyError):
        amended_task(STARTED, FIRST, TaskAmendment())


@pytest.mark.model
def test_a_task_the_item_does_not_hold_is_refused() -> None:
    with pytest.raises(TaskNotFoundError):
        amended_task(BACKLOG, MISSING, AMENDMENT)


@pytest.mark.command
def test_a_task_is_amended_and_its_work_item_saved_once_whole() -> None:
    saved: list[WorkItemState] = []
    amend_task(
        task_id=SECOND,
        amendment=AMENDMENT,
        load_holder=lambda _: STARTED,
        save_work_item=saved.append,
    )
    assert saved == [amended_task(STARTED, SECOND, AMENDMENT)]


@pytest.mark.command
def test_an_amend_names_the_work_item_that_holds_the_task() -> None:
    held = amend_task(
        task_id=SECOND,
        amendment=AMENDMENT,
        load_holder=lambda _: STARTED,
        save_work_item=lambda _: None,
    )
    assert held == ID


@pytest.mark.command
def test_an_amend_refused_saves_nothing() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(StartedAlreadyError):
        amend_task(
            task_id=FIRST,
            amendment=AMENDMENT,
            load_holder=lambda _: STARTED,
            save_work_item=saved.append,
        )
    assert saved == []
