"""The remove of a Task of a work item: only a started work item removes its Tasks."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError, make_commit, make_scenario
from flowgraph.task import (
    BlockedError,
    CompletedAlreadyError,
    ItemInBacklogError,
    TaskNotFoundError,
    TaskRemovedError,
    TaskState,
    make_task,
    make_task_id,
    removed,
)
from flowgraph.work_item import (
    RemovedAlreadyError,
    WorkItemState,
    append_task,
    blocked_task,
    blocked_work_item,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    remove_task,
    removed_task,
    removed_work_item,
    started_task,
    started_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
ONE = make_work_item_id(CHORE, 1)
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 1, 3, tzinfo=UTC)
COMMIT = make_commit("abc1234")
FIRST = make_task(make_task_id(4), "a task", "an output", "", CREATED)
SECOND = make_task(make_task_id(5), "another task", "another output", "", CREATED)
BARE = make_work_item(ONE, "a title", make_scenario("a", "b", "c"), "", CREATED)
ITEM = append_task(append_task(BARE, FIRST), SECOND)
HALF = started_task(started_work_item(ITEM, NOW), make_task_id(4), NOW)
STUCK = blocked_task(HALF, make_task_id(4), "a reason", "someone", NOW)
HELD = blocked_work_item(HALF, "no key", "developer", NOW)
LONE = started_task(started_work_item(append_task(BARE, FIRST), NOW), make_task_id(4), NOW)
DONE = completed_task(LONE, make_task_id(4), NOW, COMMIT)
WHOLE = completed_work_item(DONE, NOW, COMMIT)
GONE = removed_work_item(ITEM, "filed by mistake", NOW)


@pytest.mark.model
@pytest.mark.parametrize(
    ("item", "task_id", "tasks"),
    [
        (HALF, 5, (HALF.tasks[0], removed(SECOND, "a reason", NOW))),
        (HALF, 4, (removed(FIRST, "a reason", NOW), SECOND)),
        (STUCK, 4, (removed(FIRST, "a reason", NOW), SECOND)),
    ],
    ids=["in-backlog", "started", "blocked"],
)
def test_a_task_is_removed_among_the_others(
    item: WorkItemState, task_id: int, tasks: tuple[TaskState, ...]
) -> None:
    assert removed_task(item, make_task_id(task_id), "a reason", NOW) == replace(HALF, tasks=tasks)


@pytest.mark.model
@pytest.mark.parametrize(
    ("item", "task_id", "reason", "error", "line"),
    [
        (
            ITEM,
            4,
            "a reason",
            ItemInBacklogError,
            "T-0004 cannot be removed: CH-0001 is in Backlog",
        ),
        (
            HELD,
            5,
            "a reason",
            BlockedError,
            "T-0005 cannot be removed: CH-0001 is blocked, waiting on developer: unblock it first",
        ),
        (
            WHOLE,
            4,
            "a reason",
            CompletedAlreadyError,
            "T-0004 cannot be removed: CH-0001 is completed already",
        ),
        (GONE, 4, "a reason", RemovedAlreadyError, "CH-0001 is removed already"),
        (DONE, 4, "a reason", CompletedAlreadyError, "T-0004 is completed already"),
        (HALF, 9, "a reason", TaskNotFoundError, "no Task T-0009 in the record"),
        (HALF, 5, " ", EmptyPartError, "reason is empty"),
    ],
    ids=[
        "item-in-backlog",
        "item-blocked",
        "item-completed",
        "item-removed",
        "task-completed",
        "no-such-task",
        "blank-reason",
    ],
)
def test_a_remove_refused_names_why(
    item: WorkItemState, task_id: int, reason: str, error: type[Exception], line: str
) -> None:
    with pytest.raises(error, match=rf"^{line}$"):
        removed_task(item, make_task_id(task_id), reason, NOW)


@pytest.mark.model
def test_a_removed_task_is_not_removed_once_more() -> None:
    gone = removed_task(HALF, make_task_id(5), "a reason", NOW)
    with pytest.raises(TaskRemovedError, match=r"^T-0005 is removed already$"):
        removed_task(gone, make_task_id(5), "a reason", NOW)


@pytest.mark.command
def test_a_task_is_removed_and_its_work_item_saved_whole() -> None:
    saved: list[WorkItemState] = []
    remove_task(
        task_id=make_task_id(5),
        reason="a reason",
        load_holder=lambda _: HALF,
        save_work_item=saved.append,
        now=lambda: NOW,
    )
    assert saved == [removed_task(HALF, make_task_id(5), "a reason", NOW)]


@pytest.mark.command
def test_a_remove_names_the_work_item_that_holds_the_task() -> None:
    held = remove_task(
        task_id=make_task_id(5),
        reason="a reason",
        load_holder=lambda _: HALF,
        save_work_item=lambda _: None,
        now=lambda: NOW,
    )
    assert held == ONE


@pytest.mark.command
def test_a_remove_refused_saves_nothing() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(BlockedError):
        remove_task(
            task_id=make_task_id(5),
            reason="a reason",
            load_holder=lambda _: HELD,
            save_work_item=saved.append,
            now=lambda: NOW,
        )
    assert saved == []
