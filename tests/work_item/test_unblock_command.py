"""The unblock of a Task inside its work item, and the command that saves it."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.task import NotBlockedError, make_task, make_task_id
from flowgraph.work_item import (
    WorkItemState,
    append_task,
    blocked_task,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    started_task,
    started_work_item,
    unblock_task,
    unblocked_task,
)

CHORE = make_kind("Chore", "a", "CH")
ONE = make_work_item_id(CHORE, 1)
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 1, 3, tzinfo=UTC)
COMMIT = make_commit("abc1234")
TASK = make_task(make_task_id(4), "a task", "an output", "", CREATED)
ITEM = append_task(make_work_item(ONE, "a title", make_scenario("a", "b", "c"), "", CREATED), TASK)
HALF = started_task(started_work_item(ITEM, NOW), make_task_id(4), NOW)
STUCK = blocked_task(HALF, make_task_id(4), "a reason", "someone", NOW)


@pytest.mark.model
def test_a_blocked_task_of_a_started_work_item_is_unblocked() -> None:
    assert unblocked_task(STUCK, make_task_id(4)) == HALF


@pytest.mark.model
def test_a_task_of_a_work_item_in_backlog_is_not_unblocked() -> None:
    with pytest.raises(NotBlockedError, match=r"^T-0004 is not blocked$"):
        unblocked_task(ITEM, make_task_id(4))


@pytest.mark.model
def test_a_task_of_a_completed_work_item_is_not_unblocked() -> None:
    whole = completed_work_item(completed_task(HALF, make_task_id(4), NOW, COMMIT), NOW, COMMIT)
    with pytest.raises(NotBlockedError, match=r"^T-0004 is not blocked$"):
        unblocked_task(whole, make_task_id(4))


@pytest.mark.command
def test_a_task_is_unblocked_and_its_work_item_saved_whole() -> None:
    saved: list[WorkItemState] = []
    unblock_task(task_id=make_task_id(4), load_holder=lambda _: STUCK, save_work_item=saved.append)
    assert saved == [HALF]


@pytest.mark.command
def test_an_unblock_names_the_work_item_that_holds_the_task() -> None:
    held = unblock_task(
        task_id=make_task_id(4), load_holder=lambda _: STUCK, save_work_item=lambda _: None
    )
    assert held == ONE


@pytest.mark.command
def test_an_unblock_refused_saves_nothing() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(NotBlockedError):
        unblock_task(
            task_id=make_task_id(4), load_holder=lambda _: HALF, save_work_item=saved.append
        )
    assert saved == []
