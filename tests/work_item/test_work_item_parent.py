"""The parent of a work item: a Feature or standing alone, kept through every move and its file."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.parent import STANDALONE, make_feature_id
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    Amendment,
    WorkItemFileError,
    WorkItemState,
    add_work_item,
    amended_work_item,
    append_task,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    read_work_item,
    read_work_item_detail,
    read_work_item_rows,
    removed_work_item,
    started_task,
    started_work_item,
    work_item_detail,
    work_item_row,
    write_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
ONE = make_work_item_id(CHORE, 1)
ABOVE = make_feature_id(1)
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
COMMIT = make_commit("abc1234")
SCENARIO = make_scenario("a state", "an action", "another state")
TASK = make_task(make_task_id(3), "a task title", "an output", "", CREATED)
BARE = make_work_item(ONE, "a title", SCENARIO, "", CREATED, ABOVE)
ITEM = append_task(BARE, TASK)
BEGUN = started_work_item(ITEM, ON)
READY = completed_task(started_task(BEGUN, make_task_id(3), ON), make_task_id(3), ON, COMMIT)
WHOLE = completed_work_item(READY, ON, COMMIT)
GONE = removed_work_item(ITEM, "a reason", ON)
ALONE = make_work_item(ONE, "a title", SCENARIO, "", CREATED)
FILE = Path("items") / "CH-0001.toml"


@pytest.mark.model
def test_a_work_item_made_under_a_feature_names_it_as_its_parent() -> None:
    assert BARE.parent == ABOVE


@pytest.mark.model
def test_a_work_item_made_without_a_parent_stands_alone() -> None:
    assert ALONE.parent == STANDALONE


@pytest.mark.model
@pytest.mark.parametrize(
    "item",
    [ITEM, BEGUN, READY, WHOLE, GONE, amended_work_item(BARE, Amendment(title="one more"))],
    ids=["with-a-task", "started", "task-completed", "completed", "removed", "amended"],
)
def test_a_work_item_keeps_its_parent_through_every_move(item: WorkItemState) -> None:
    assert item.parent == ABOVE


@pytest.mark.view
def test_the_row_and_the_detail_of_a_work_item_name_its_parent() -> None:
    assert (work_item_row(ITEM).parent, work_item_detail(ITEM).parent) == ("F-0001", "F-0001")


@pytest.mark.view
def test_the_row_of_a_work_item_that_stands_alone_names_no_parent() -> None:
    assert work_item_row(ALONE).parent == ""


@pytest.mark.command
def test_a_work_item_is_added_under_the_parent_given() -> None:
    saved: list[WorkItemState] = []
    add_work_item(
        kind=CHORE,
        title="a title",
        criterion=SCENARIO,
        description="",
        find_work_item_rows=lambda: [],
        save_work_item=saved.append,
        now=lambda: CREATED,
        parent=ABOVE,
    )
    assert saved == [BARE]


@pytest.mark.edge
def test_the_parent_is_written_as_the_id_of_the_feature(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE)
    assert tomllib.loads((tmp_path / FILE).read_text("utf-8"))["parent"] == "F-0001"


@pytest.mark.edge
def test_a_work_item_that_stands_alone_is_written_without_a_parent(tmp_path: Path) -> None:
    write_work_item(tmp_path, ALONE)
    assert "parent" not in tomllib.loads((tmp_path / FILE).read_text("utf-8"))


@pytest.mark.edge
@pytest.mark.parametrize(
    "item",
    [BARE, BEGUN, WHOLE, GONE, ALONE],
    ids=["backlog", "started", "completed", "removed", "alone"],
)
def test_a_work_item_reads_back_with_its_parent(tmp_path: Path, item: WorkItemState) -> None:
    write_work_item(tmp_path, item)
    assert read_work_item(tmp_path, ONE) == item


@pytest.mark.edge
def test_the_row_and_the_detail_read_from_the_file_name_the_parent(tmp_path: Path) -> None:
    write_work_item(tmp_path, ITEM)
    assert (read_work_item_rows(tmp_path, CHORE), read_work_item_detail(tmp_path, ONE)) == (
        [work_item_row(ITEM)],
        work_item_detail(ITEM),
    )


@pytest.mark.edge
def test_a_file_whose_parent_is_no_feature_id_is_refused(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE)
    path = tmp_path / FILE
    path.write_text(path.read_text("utf-8").replace("F-0001", "ST-0001"), "utf-8")
    with pytest.raises(
        WorkItemFileError, match=r"CH-0001.toml holds no Chore: 'ST-0001' is no Feature id"
    ):
        read_work_item(tmp_path, ONE)
