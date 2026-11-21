"""The block command of a work item, and the text that shows a blocked Task."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.task import BlockedError, TaskRow, make_task, make_task_id
from flowgraph.text import show_text
from flowgraph.work_item import (
    WorkItemDetail,
    WorkItemState,
    append_task,
    block_task,
    blocked_task,
    make_kind,
    make_work_item,
    make_work_item_id,
    started_task,
    started_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
ONE = make_work_item_id(CHORE, 1)
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 1, 3, tzinfo=UTC)
TASK = make_task(make_task_id(4), "a task", "an output", "", CREATED)
ITEM = append_task(make_work_item(ONE, "a title", make_scenario("a", "b", "c"), "", CREATED), TASK)
HALF = started_task(started_work_item(ITEM, NOW), make_task_id(4), NOW)
STUCK = blocked_task(HALF, make_task_id(4), "a reason", "someone", NOW)


@pytest.mark.command
def test_a_task_is_blocked_and_its_work_item_saved_whole() -> None:
    saved: list[WorkItemState] = []
    block_task(
        task_id=make_task_id(4),
        reason="a reason",
        waiting_on="someone",
        load_holder=lambda _: HALF,
        save_work_item=saved.append,
        now=lambda: NOW,
    )
    assert saved == [STUCK]


@pytest.mark.command
def test_a_block_names_the_work_item_that_holds_the_task() -> None:
    held = block_task(
        task_id=make_task_id(4),
        reason="a reason",
        waiting_on="someone",
        load_holder=lambda _: HALF,
        save_work_item=lambda _: None,
        now=lambda: NOW,
    )
    assert held == ONE


@pytest.mark.command
def test_a_block_refused_saves_nothing() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(BlockedError):
        block_task(
            task_id=make_task_id(4),
            reason="a reason",
            waiting_on="someone",
            load_holder=lambda _: STUCK,
            save_work_item=saved.append,
            now=lambda: NOW,
        )
    assert saved == []


@pytest.mark.view
def test_a_blocked_task_is_shown_in_inprogress_as_blocked_with_its_reason() -> None:
    detail = WorkItemDetail(
        id="CH-0001",
        title="a title",
        state="started",
        description="",
        given="a",
        when="b",
        then="c",
        tasks=[
            TaskRow("T-0004", "a task", "an output", "how", "blocked", "", "a reason", "someone")
        ],
    )
    assert show_text(detail).splitlines()[-6:] == [
        "  T-0004  a task",
        "    bucket           InProgress, blocked",
        "    reason           a reason",
        "    waiting on       someone",
        "    expected output  an output",
        "    description      how",
    ]
