"""The commands of a work item of any kind: each loads it whole, writes or moves it, saves it."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.parent import CriterionPlace, make_feature_id
from flowgraph.task import TaskNotFoundError, TaskRow, make_task, make_task_id
from flowgraph.work_item import (
    WorkItemDetail,
    WorkItemRow,
    WorkItemState,
    add_task,
    add_work_item,
    append_task,
    complete_task,
    completed_task,
    holder_of,
    make_kind,
    make_work_item,
    make_work_item_id,
    start_task,
    start_work_item,
    started_task,
    started_work_item,
    work_item_detail,
    work_item_row,
)

pytestmark = pytest.mark.command

CHORE = make_kind("Chore", "a", "CH")
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 1, 3, tzinfo=UTC)
COMMIT = make_commit("abc1234")
SCENARIO = make_scenario("a", "b", "c")
ONE = make_work_item_id(CHORE, 1)
BARE = make_work_item(ONE, "a title", SCENARIO, "", CREATED)
TASK = make_task(make_task_id(4), "a task", "an output", "", CREATED)
ITEM = append_task(BARE, TASK)
BEGUN = started_work_item(ITEM, NOW)
HALF = started_task(BEGUN, make_task_id(4), NOW)
FINISHED = completed_task(HALF, make_task_id(4), NOW, COMMIT)


def test_a_work_item_is_added_under_the_next_id_of_its_kind() -> None:
    saved: list[WorkItemState] = []
    add_work_item(
        kind=CHORE,
        title="a title",
        criterion=SCENARIO,
        description="",
        find_work_item_rows=lambda: [
            WorkItemRow("CH-0002", "an earlier title", "backlog", created=CREATED)
        ],
        save_work_item=saved.append,
        now=lambda: CREATED,
    )
    assert saved == [make_work_item(make_work_item_id(CHORE, 3), "a title", SCENARIO, "", CREATED)]


def test_a_work_item_added_with_a_place_is_saved_with_it() -> None:
    saved: list[WorkItemState] = []
    add_work_item(
        kind=CHORE,
        title="a title",
        criterion=SCENARIO,
        description="",
        find_work_item_rows=list,
        save_work_item=saved.append,
        now=lambda: CREATED,
        parent=make_feature_id(1),
        realizes=CriterionPlace(2),
    )
    assert saved == [
        make_work_item(
            ONE, "a title", SCENARIO, "", CREATED, make_feature_id(1), realizes=CriterionPlace(2)
        )
    ]


def test_a_task_written_for_a_work_item_takes_the_next_task_id_of_the_record() -> None:
    saved: list[WorkItemState] = []
    add_task(
        parent=ONE,
        title="a task",
        expected_output="an output",
        description="",
        load_work_item=lambda _: BARE,
        find_task_ids=lambda: ["T-0003"],
        save_work_item=saved.append,
        now=lambda: CREATED,
    )
    assert saved == [ITEM]


def test_a_work_item_is_started_and_saved_whole() -> None:
    saved: list[WorkItemState] = []
    start_work_item(
        item_id=ONE, load_work_item=lambda _: ITEM, save_work_item=saved.append, now=lambda: NOW
    )
    assert saved == [BEGUN]


def test_a_task_is_started_in_the_work_item_that_holds_it() -> None:
    saved: list[WorkItemState] = []
    start_task(
        task_id=make_task_id(4),
        load_holder=lambda _: BEGUN,
        save_work_item=saved.append,
        now=lambda: NOW,
    )
    assert saved == [HALF]


def test_a_task_is_completed_in_the_work_item_that_holds_it() -> None:
    saved: list[WorkItemState] = []
    complete_task(
        task_id=make_task_id(4),
        commit=COMMIT,
        load_holder=lambda _: HALF,
        save_work_item=saved.append,
        now=lambda: NOW,
    )
    assert saved == [FINISHED]


def test_the_holder_of_a_task_is_the_work_item_that_has_it() -> None:
    other = make_work_item_id(CHORE, 2)
    held = {other: make_work_item(other, "another", SCENARIO, "", CREATED), ONE: ITEM}
    assert holder_of(make_task_id(4), [other, ONE], held.__getitem__) == ITEM


def test_a_task_no_work_item_holds_is_refused_by_its_id() -> None:
    with pytest.raises(TaskNotFoundError, match=r"^no Task T-0009 in the record$"):
        holder_of(make_task_id(9), [ONE], lambda _: ITEM)


def test_a_work_item_is_the_row_a_view_reads() -> None:
    task = TaskRow("T-0004", "a task", "an output", "", "backlog")
    assert work_item_row(ITEM) == WorkItemRow(
        "CH-0001", "a title", "backlog", created=CREATED, tasks=[task]
    )


def test_a_work_item_is_the_detail_a_view_reads_with_its_tasks() -> None:
    assert work_item_detail(HALF) == WorkItemDetail(
        id="CH-0001",
        title="a title",
        state="started",
        description="",
        given="a",
        when="b",
        then="c",
        tasks=[TaskRow("T-0004", "a task", "an output", "", "started")],
    )
