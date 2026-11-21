"""The remove of a work item: one in Backlog is removed with its reason, and kept in its file."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import EmptyPartError, make_commit, make_scenario
from flowgraph.task import CompletedAlreadyError, StartedAlreadyError, make_task, make_task_id
from flowgraph.work_item import (
    Amendment,
    RemovedAlreadyError,
    RemovedWorkItem,
    WorkItemRow,
    amended_work_item,
    append_task,
    commit_sha,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    read_work_item,
    read_work_item_rows,
    removed_work_item,
    started_task,
    started_work_item,
    state_name,
    still_open,
    work_item_detail,
    work_item_row,
    write_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
ONE = make_work_item_id(CHORE, 1)
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, 500, tzinfo=UTC)
COMMIT = make_commit("abc1234")
SCENARIO = make_scenario("a state", "an action", "another state")
TASK = make_task(make_task_id(3), "a task title", "an output", "", CREATED)
ITEM = append_task(make_work_item(ONE, "a title", SCENARIO, "why", CREATED), TASK)
BEGUN = started_work_item(ITEM, ON)
GONE = removed_work_item(ITEM, "filed by mistake", ON)
FILE = Path("items") / "CH-0001.toml"


@pytest.mark.model
def test_a_work_item_in_backlog_is_removed_with_its_reason_and_keeps_its_tasks() -> None:
    assert removed_work_item(ITEM, "filed by mistake", ON) == RemovedWorkItem(
        ONE,
        "a title",
        SCENARIO,
        "why",
        CREATED,
        ON.replace(microsecond=0),
        "filed by mistake",
        (TASK,),
    )


@pytest.mark.model
def test_a_started_work_item_is_not_removed() -> None:
    with pytest.raises(StartedAlreadyError, match=r"^CH-0001 is started already$"):
        removed_work_item(BEGUN, "a reason", ON)


@pytest.mark.model
def test_a_completed_work_item_is_not_removed() -> None:
    done = completed_task(started_task(BEGUN, make_task_id(3), ON), make_task_id(3), ON, COMMIT)
    with pytest.raises(CompletedAlreadyError, match=r"^CH-0001 is completed already$"):
        removed_work_item(completed_work_item(done, ON, COMMIT), "a reason", ON)


@pytest.mark.model
def test_a_removed_work_item_is_not_removed_once_more() -> None:
    with pytest.raises(RemovedAlreadyError, match=r"^CH-0001 is removed already$"):
        removed_work_item(GONE, "a reason", ON)


@pytest.mark.model
def test_a_remove_with_a_blank_reason_is_refused() -> None:
    with pytest.raises(EmptyPartError, match=r"^reason is empty$"):
        removed_work_item(ITEM, " ", ON)


@pytest.mark.model
def test_a_removed_work_item_takes_no_task() -> None:
    with pytest.raises(RemovedAlreadyError, match=r"^CH-0001 is removed already$"):
        still_open(GONE)


@pytest.mark.model
def test_a_removed_work_item_is_not_started() -> None:
    with pytest.raises(RemovedAlreadyError, match=r"^CH-0001 is removed already$"):
        started_work_item(GONE, ON)


@pytest.mark.model
def test_a_removed_work_item_is_not_amended() -> None:
    with pytest.raises(RemovedAlreadyError, match=r"^CH-0001 is removed already$"):
        amended_work_item(GONE, Amendment(title="one more"))


@pytest.mark.model
def test_a_removed_work_item_is_not_completed() -> None:
    with pytest.raises(RemovedAlreadyError, match=r"^CH-0001 is removed already$"):
        completed_work_item(GONE, ON, COMMIT)


@pytest.mark.model
def test_a_removed_work_item_is_named_removed_and_has_no_commit() -> None:
    assert (state_name(GONE), commit_sha(GONE)) == ("removed", "")


@pytest.mark.view
def test_the_row_of_a_removed_work_item_names_its_reason() -> None:
    assert work_item_row(GONE) == WorkItemRow(
        "CH-0001", "a title", "removed", reason="filed by mistake", created=CREATED
    )


@pytest.mark.view
def test_the_detail_of_a_removed_work_item_names_its_reason() -> None:
    assert work_item_detail(GONE).reason == "filed by mistake"


@pytest.mark.edge
def test_a_removed_work_item_is_written_with_its_removal(tmp_path: Path) -> None:
    write_work_item(tmp_path, GONE)
    written = tomllib.loads((tmp_path / FILE).read_text("utf-8"))
    assert (written["state"], written["removed"], written["reason"]) == (
        "removed",
        ON.replace(microsecond=0),
        "filed by mistake",
    )


@pytest.mark.edge
def test_a_removed_work_item_reads_back_whole(tmp_path: Path) -> None:
    write_work_item(tmp_path, GONE)
    assert read_work_item(tmp_path, ONE) == GONE


@pytest.mark.edge
def test_the_row_read_from_the_file_of_a_removed_work_item_names_its_reason(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, GONE)
    assert read_work_item_rows(tmp_path, CHORE) == [work_item_row(GONE)]
