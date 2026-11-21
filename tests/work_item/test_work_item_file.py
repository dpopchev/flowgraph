"""The file of a work item of any kind: named by its id, read back by its kind in every state."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.task import TaskRow, make_task, make_task_id
from flowgraph.work_item import (
    WorkItemDetail,
    WorkItemFileError,
    WorkItemMismatchError,
    WorkItemNotFoundError,
    WorkItemRow,
    WorkItemState,
    append_task,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    read_task_ids,
    read_work_item,
    read_work_item_detail,
    read_work_item_rows,
    started_task,
    started_work_item,
    write_work_item,
)
from flowgraph.work_item import file as work_item_file

pytestmark = pytest.mark.edge

CHORE = make_kind("Chore", "a", "CH")
ERRAND = make_kind("Errand", "an", "ER")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
COMMIT = make_commit("abc1234")
SCENARIO = make_scenario("a state", "an action", "another state")
BARE = make_work_item(make_work_item_id(CHORE, 1), "a title", SCENARIO, "", CREATED)
TASK = make_task(make_task_id(3), "a task title", "an output", "", CREATED)
ITEM = append_task(BARE, TASK)
HALF = started_task(started_work_item(ITEM, ON), make_task_id(3), ON)
WHOLE = completed_work_item(completed_task(HALF, make_task_id(3), ON, COMMIT), ON, COMMIT)
FILE = Path("items") / "CH-0001.toml"


def test_a_work_item_is_written_as_its_one_file_named_by_its_id(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE)
    assert tomllib.loads((tmp_path / FILE).read_text("utf-8")) == {
        "id": "CH-0001",
        "state": "backlog",
        "title": "a title",
        "created": CREATED,
        "criterion": {"given": "a state", "when": "an action", "then": "another state"},
    }


@pytest.mark.parametrize("item", [BARE, ITEM, HALF, WHOLE])
def test_a_work_item_in_any_state_reads_back_whole(tmp_path: Path, item: WorkItemState) -> None:
    write_work_item(tmp_path, item)
    assert read_work_item(tmp_path, make_work_item_id(CHORE, 1)) == item


def test_the_work_items_of_a_kind_are_read_as_rows_by_id(tmp_path: Path) -> None:
    later = make_work_item(make_work_item_id(CHORE, 10), "a later title", SCENARIO, "", CREATED)
    write_work_item(tmp_path, later)
    write_work_item(tmp_path, WHOLE)
    assert read_work_item_rows(tmp_path, CHORE) == [
        WorkItemRow("CH-0001", "a title", "completed", "abc1234"),
        WorkItemRow("CH-0010", "a later title", "backlog"),
    ]


def test_a_file_of_another_kind_is_left_alone(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE)
    (tmp_path / "items" / "ER-0001.toml").write_text("not a chore", encoding="utf-8")
    assert [row.id for row in read_work_item_rows(tmp_path, CHORE)] == ["CH-0001"]


def test_a_record_without_items_has_no_rows(tmp_path: Path) -> None:
    assert read_work_item_rows(tmp_path, ERRAND) == []


def test_a_work_item_is_read_as_detail_with_its_tasks(tmp_path: Path) -> None:
    write_work_item(tmp_path, HALF)
    assert read_work_item_detail(tmp_path, make_work_item_id(CHORE, 1)) == WorkItemDetail(
        id="CH-0001",
        title="a title",
        state="started",
        description="",
        given="a state",
        when="an action",
        then="another state",
        tasks=[TaskRow("T-0003", "a task title", "an output", "", "started")],
    )


def test_the_task_ids_of_a_kind_are_read_from_its_files(tmp_path: Path) -> None:
    write_work_item(tmp_path, ITEM)
    assert read_task_ids(tmp_path, CHORE) == ["T-0003"]


def test_a_work_item_the_record_does_not_hold_is_refused_naming_its_kind(tmp_path: Path) -> None:
    with pytest.raises(WorkItemNotFoundError, match=r"^no Errand ER-0002 in the record$"):
        read_work_item(tmp_path, make_work_item_id(ERRAND, 2))


def test_a_file_that_holds_no_work_item_is_refused_naming_it_and_its_kind(tmp_path: Path) -> None:
    (tmp_path / "items").mkdir()
    (tmp_path / FILE).write_text('id = "CH-0001"\n', encoding="utf-8")
    with pytest.raises(WorkItemFileError, match=r"CH-0001\.toml holds no Chore"):
        read_work_item_rows(tmp_path, CHORE)


class TestAWriteThatReadsBackDifferent:
    @pytest.fixture
    def failed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
        """The file and the message of a write whose read-back holds another title."""
        path = tmp_path / FILE
        path.parent.mkdir()
        path.write_text("previous", encoding="utf-8")
        another = {
            "id": "CH-0001",
            "state": "backlog",
            "title": "another title",
            "created": CREATED,
            "criterion": {"given": "a state", "when": "an action", "then": "another state"},
        }
        monkeypatch.setattr(work_item_file.tomllib, "loads", lambda _: another)
        with pytest.raises(WorkItemMismatchError) as error:
            write_work_item(tmp_path, BARE)
        return path, str(error.value)

    def test_keeps_the_previous_content(self, failed: tuple[Path, str]) -> None:
        assert failed[0].read_text(encoding="utf-8") == "previous"

    def test_names_the_path_and_the_kind(self, failed: tuple[Path, str]) -> None:
        assert failed[1] == f"{failed[0]}: the Chore written reads back different"
