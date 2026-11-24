"""The criterion a work item realizes: kept by every move and its file, refused when alone."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.parent import (
    NO_CRITERION,
    STANDALONE,
    CriterionPlace,
    RealizesError,
    make_feature_id,
)
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    WorkItemFileError,
    WorkItemState,
    append_task,
    blocked_work_item,
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
    unblocked_work_item,
    verified_work_item,
    work_item_detail,
    work_item_path,
    work_item_row,
    write_work_item,
)
from flowgraph.work_item.agent import make_agent
from flowgraph.work_item.handed import handed_work_item

CHORE = make_kind("Chore", "a", "CH")
ONE = make_work_item_id(CHORE, 1)
ABOVE = make_feature_id(1)
SECOND = CriterionPlace(2)
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
COMMIT = make_commit("abc1234")
SCENARIO = make_scenario("a state", "an action", "another state")
TASK = make_task(make_task_id(3), "a task title", "an output", "", CREATED)
BARE = make_work_item(ONE, "a title", SCENARIO, "", CREATED, ABOVE, realizes=SECOND)
ITEM = append_task(BARE, TASK)
BEGUN = started_work_item(ITEM, ON)
READY = completed_task(started_task(BEGUN, make_task_id(3), ON), make_task_id(3), ON, COMMIT)
WHOLE = completed_work_item(READY, ON, COMMIT)
STUCK = blocked_work_item(BEGUN, "no key", "developer", ON)
GONE = removed_work_item(ITEM, "a reason", ON)
UNNAMED = make_work_item(ONE, "a title", SCENARIO, "", CREATED, ABOVE)
ALL = [ITEM, BEGUN, READY, WHOLE, STUCK, GONE]
STATES = [ITEM, BEGUN, STUCK, WHOLE, GONE]
IDS = ["with-a-task", "started", "blocked", "completed", "removed"]


@pytest.mark.model
def test_a_work_item_is_made_naming_no_criterion_by_default() -> None:
    assert UNNAMED.realizes == NO_CRITERION


@pytest.mark.model
def test_a_work_item_under_a_feature_is_made_with_the_place_given() -> None:
    assert BARE.realizes == SECOND


@pytest.mark.model
def test_a_place_given_to_a_work_item_standing_alone_is_refused() -> None:
    with pytest.raises(RealizesError, match=r"this one stands alone$"):
        make_work_item(ONE, "a title", SCENARIO, "", CREATED, STANDALONE, realizes=SECOND)


@pytest.mark.model
@pytest.mark.parametrize(
    "item", ALL, ids=["task", "started", "task-done", "done", "blocked", "gone"]
)
def test_a_work_item_keeps_its_place_through_every_move(item: WorkItemState) -> None:
    assert item.realizes == SECOND


@pytest.mark.model
def test_an_unblocked_work_item_keeps_its_place() -> None:
    assert unblocked_work_item(STUCK).realizes == SECOND


@pytest.mark.model
def test_a_work_item_handed_to_an_agent_keeps_its_place() -> None:
    assert handed_work_item(BEGUN, make_agent("sonnet-a1")).realizes == SECOND


@pytest.mark.model
def test_a_verified_work_item_keeps_its_place() -> None:
    assert verified_work_item(WHOLE, "it ran", ON).realizes == SECOND


@pytest.mark.model
def test_a_work_item_given_a_task_keeps_its_place() -> None:
    assert append_task(BARE, TASK).realizes == SECOND


@pytest.mark.edge
@pytest.mark.parametrize("item", STATES, ids=IDS)
def test_the_place_is_read_back_as_written(tmp_path: Path, item: WorkItemState) -> None:
    write_work_item(tmp_path, item)
    assert read_work_item(tmp_path, ONE) == item


@pytest.mark.edge
def test_a_file_holds_the_key_realizes_right_after_its_parent(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE)
    held = work_item_path(tmp_path, ONE).read_text(encoding="utf-8")
    assert 'parent = "F-0001"\nrealizes = 2\n' in held


@pytest.mark.edge
def test_a_file_holds_the_key_realizes_only_when_it_names_one(tmp_path: Path) -> None:
    write_work_item(tmp_path, UNNAMED)
    assert "realizes" not in work_item_path(tmp_path, ONE).read_text(encoding="utf-8")


@pytest.mark.edge
def test_a_file_without_the_key_is_read_as_no_criterion(tmp_path: Path) -> None:
    write_work_item(tmp_path, UNNAMED)
    assert read_work_item(tmp_path, ONE).realizes == NO_CRITERION


@pytest.mark.edge
def test_a_file_holding_0_is_refused_naming_it(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE)
    path = work_item_path(tmp_path, ONE)
    path.write_text(path.read_text(encoding="utf-8").replace("realizes = 2", "realizes = 0"))
    with pytest.raises(WorkItemFileError, match=r"CH-0001\.toml"):
        read_work_item(tmp_path, ONE)


@pytest.mark.edge
def test_a_file_holding_the_key_with_no_parent_is_refused_naming_it(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE)
    path = work_item_path(tmp_path, ONE)
    path.write_text(path.read_text(encoding="utf-8").replace('parent = "F-0001"\n', ""))
    with pytest.raises(WorkItemFileError, match=r"CH-0001\.toml"):
        read_work_item(tmp_path, ONE)


@pytest.mark.view
def test_the_row_projected_from_a_work_item_holds_the_number_of_its_place() -> None:
    assert work_item_row(BARE).realizes == 2


@pytest.mark.view
def test_the_row_projected_from_a_work_item_naming_none_holds_none() -> None:
    assert work_item_row(UNNAMED).realizes is None


@pytest.mark.view
def test_the_detail_projected_from_a_work_item_holds_the_number_of_its_place() -> None:
    assert work_item_detail(BARE).realizes == 2


@pytest.mark.view
def test_the_detail_projected_from_a_work_item_naming_none_holds_none() -> None:
    assert work_item_detail(UNNAMED).realizes is None


@pytest.mark.edge
def test_the_row_read_from_the_file_holds_the_number_of_its_place(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE)
    assert read_work_item_rows(tmp_path, CHORE)[0].realizes == 2


@pytest.mark.edge
def test_the_row_read_from_a_file_naming_none_holds_none(tmp_path: Path) -> None:
    write_work_item(tmp_path, UNNAMED)
    assert read_work_item_rows(tmp_path, CHORE)[0].realizes is None


@pytest.mark.edge
def test_the_detail_read_from_the_file_holds_the_number_of_its_place(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE)
    assert read_work_item_detail(tmp_path, ONE).realizes == 2


@pytest.mark.edge
def test_the_detail_read_from_a_file_naming_none_holds_none(tmp_path: Path) -> None:
    write_work_item(tmp_path, UNNAMED)
    assert read_work_item_detail(tmp_path, ONE).realizes is None
