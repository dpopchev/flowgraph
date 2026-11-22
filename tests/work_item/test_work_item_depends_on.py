"""The work items a work item depends on: kept through every move, written to its file, read back.

They are stored on the item that names them, as the ids of work items of any kind.
"""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import NO_COMMIT, make_scenario
from flowgraph.relation import RelationError
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    Amendment,
    WorkItemFileError,
    WorkItemState,
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
    work_item_path,
    write_work_item,
)

pytestmark = pytest.mark.edge

CHORE = make_kind("Chore", "a", "CH")
ERRAND = make_kind("Errand", "an", "ER")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
ONE, TWO = make_work_item_id(CHORE, 1), make_work_item_id(CHORE, 2)
ABROAD = make_work_item_id(ERRAND, 1)
SCENARIO = make_scenario("a state", "an action", "another state")
TASK = make_task(make_task_id(1), "a task title", "an output", "", CREATED)
BARE = make_work_item(TWO, "a title", SCENARIO, "", CREATED)
DEPENDING = make_work_item(TWO, "a title", SCENARIO, "", CREATED, depends_on=[ONE, ABROAD])
TASKED = append_task(DEPENDING, TASK)
STARTED = started_work_item(TASKED, ON)
REMOVED = removed_work_item(DEPENDING, "a reason", ON)
DONE = completed_task(started_task(STARTED, TASK.id, ON), TASK.id, ON, NO_COMMIT)
COMPLETED = completed_work_item(DONE, ON, NO_COMMIT)
KINDS = (CHORE, ERRAND)
IDS = ("CH-0001", "ER-0001")


@pytest.mark.parametrize(
    "item",
    [DEPENDING, STARTED, COMPLETED, REMOVED],
    ids=["backlog", "started", "completed", "removed"],
)
def test_the_ids_are_read_back_in_every_state(tmp_path: Path, item: WorkItemState) -> None:
    write_work_item(tmp_path, item, KINDS)
    assert read_work_item(tmp_path, TWO, KINDS).relations.depends_on == (ONE, ABROAD)


def test_a_work_item_depends_on_none_by_default() -> None:
    assert BARE.relations.depends_on == ()


def test_a_started_work_item_keeps_the_ids() -> None:
    assert STARTED.relations.depends_on == (ONE, ABROAD)


def test_a_completed_work_item_keeps_the_ids() -> None:
    assert COMPLETED.relations.depends_on == (ONE, ABROAD)


def test_a_removed_work_item_keeps_the_ids() -> None:
    assert REMOVED.relations.depends_on == (ONE, ABROAD)


def test_a_work_item_that_names_itself_is_refused_by_name() -> None:
    with pytest.raises(RelationError, match=r"^CH-0002 cannot depend on itself$"):
        make_work_item(TWO, "a title", SCENARIO, "", CREATED, depends_on=[TWO])


def test_the_file_holds_the_ids_as_depends_on(tmp_path: Path) -> None:
    write_work_item(tmp_path, DEPENDING, KINDS)
    held = tomllib.loads(work_item_path(tmp_path, TWO).read_text(encoding="utf-8"))
    assert held["depends_on"] == list(IDS)


def test_the_file_of_a_work_item_that_depends_on_none_holds_no_depends_on(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE, KINDS)
    held = tomllib.loads(work_item_path(tmp_path, TWO).read_text(encoding="utf-8"))
    assert "depends_on" not in held


def test_the_detail_read_from_the_file_lists_the_ids_without_a_bucket(tmp_path: Path) -> None:
    write_work_item(tmp_path, DEPENDING, KINDS)
    detail = read_work_item_detail(tmp_path, TWO)
    assert [(row.id, row.bucket) for row in detail.depends_on] == [("CH-0001", ""), ("ER-0001", "")]


def test_the_row_read_from_the_file_lists_the_ids(tmp_path: Path) -> None:
    write_work_item(tmp_path, DEPENDING, KINDS)
    assert [row.depends_on for row in read_work_item_rows(tmp_path, CHORE)] == [list(IDS)]


def test_an_id_of_a_kind_not_known_is_refused_naming_the_file(tmp_path: Path) -> None:
    write_work_item(tmp_path, DEPENDING, KINDS)
    with pytest.raises(WorkItemFileError, match=r"CH-0002.toml holds no Chore: .*ER-0001"):
        read_work_item(tmp_path, TWO)


def test_a_file_that_names_its_own_item_is_refused_naming_the_file(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE, KINDS)
    path = work_item_path(tmp_path, TWO)
    path.write_text(
        'depends_on = ["CH-0002"]\n' + path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    with pytest.raises(WorkItemFileError, match=r"CH-0002.toml holds no Chore: CH-0002 cannot"):
        read_work_item(tmp_path, TWO, KINDS)


def test_an_amend_replaces_the_ids() -> None:
    amended = amended_work_item(DEPENDING, Amendment(depends_on=(ABROAD,)))
    assert amended.relations.depends_on == (ABROAD,)


def test_an_amend_that_gives_no_ids_takes_them_all_away() -> None:
    assert amended_work_item(DEPENDING, Amendment(depends_on=())).relations.depends_on == ()


def test_an_amend_that_names_no_ids_leaves_them_as_they_were() -> None:
    amended = amended_work_item(DEPENDING, Amendment(title="another title"))
    assert amended.relations.depends_on == (ONE, ABROAD)


def test_an_amend_with_only_ids_is_an_amend_of_a_part() -> None:
    assert amended_work_item(BARE, Amendment(depends_on=(ONE,))).relations.depends_on == (ONE,)


def test_an_amend_that_names_the_item_itself_is_refused() -> None:
    with pytest.raises(RelationError, match=r"^CH-0002 cannot depend on itself$"):
        amended_work_item(BARE, Amendment(depends_on=(TWO,)))
