"""The block of a Task inside its work item, and the file that keeps a blocked Task."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.task import (
    CompletedAlreadyError,
    NotStartedError,
    TaskNotFoundError,
    TaskRow,
    blocked,
    make_task,
    make_task_id,
    started,
)
from flowgraph.work_item import (
    WorkItemFileError,
    append_task,
    blocked_task,
    commit_sha,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    read_work_item,
    read_work_item_detail,
    started_task,
    started_work_item,
    state_name,
    work_item_detail,
    write_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
ONE = make_work_item_id(CHORE, 1)
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 1, 3, 9, 0, 0, tzinfo=UTC)
COMMIT = make_commit("abc1234")
SCENARIO = make_scenario("a state", "an action", "another state")
TASK = make_task(make_task_id(3), "a task title", "an output", "", CREATED)
ITEM = append_task(make_work_item(ONE, "a title", SCENARIO, "", CREATED), TASK)
HALF = started_task(started_work_item(ITEM, ON), make_task_id(3), ON)
STUCK = blocked_task(HALF, make_task_id(3), "a reason", "someone", LATER)
BLOCKED = blocked(started(TASK, ON), "a reason", "someone", LATER)
FILE = Path("items") / "CH-0001.toml"


@pytest.mark.model
def test_a_task_of_a_started_work_item_is_blocked() -> None:
    assert STUCK.tasks == (BLOCKED,)


@pytest.mark.model
def test_a_task_of_a_work_item_in_backlog_is_not_blocked() -> None:
    with pytest.raises(NotStartedError, match=r"^T-0003 is in Backlog: start it first$"):
        blocked_task(ITEM, make_task_id(3), "a reason", "someone", LATER)


@pytest.mark.model
def test_a_task_of_a_completed_work_item_is_not_blocked() -> None:
    whole = completed_work_item(completed_task(HALF, make_task_id(3), ON, COMMIT), ON, COMMIT)
    with pytest.raises(CompletedAlreadyError, match=r"^T-0003 is completed already$"):
        blocked_task(whole, make_task_id(3), "a reason", "someone", LATER)


@pytest.mark.model
def test_a_task_the_work_item_does_not_hold_is_not_blocked() -> None:
    with pytest.raises(TaskNotFoundError, match=r"^no Task T-0009 in the record$"):
        blocked_task(HALF, make_task_id(9), "a reason", "someone", LATER)


@pytest.mark.model
def test_a_blocked_task_is_named_blocked_and_has_no_commit() -> None:
    assert (state_name(BLOCKED), commit_sha(BLOCKED)) == ("blocked", "")


@pytest.mark.view
def test_the_detail_of_a_work_item_lists_its_blocked_task_with_its_reason() -> None:
    assert work_item_detail(STUCK).tasks == [
        TaskRow(
            "T-0003",
            "a task title",
            "an output",
            "",
            "blocked",
            reason="a reason",
            waiting_on="someone",
        )
    ]


@pytest.mark.edge
def test_a_blocked_task_is_written_as_a_table_with_its_block(tmp_path: Path) -> None:
    write_work_item(tmp_path, STUCK)
    assert tomllib.loads((tmp_path / FILE).read_text("utf-8"))["tasks"] == [
        {
            "id": "T-0003",
            "state": "blocked",
            "title": "a task title",
            "expected_output": "an output",
            "created": CREATED,
            "started": ON,
            "since": LATER,
            "reason": "a reason",
            "waiting_on": "someone",
        }
    ]


@pytest.mark.edge
def test_a_work_item_with_a_blocked_task_reads_back_whole(tmp_path: Path) -> None:
    write_work_item(tmp_path, STUCK)
    assert read_work_item(tmp_path, ONE) == STUCK


@pytest.mark.edge
def test_the_detail_read_from_the_file_lists_the_blocked_task_with_its_reason(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, STUCK)
    assert read_work_item_detail(tmp_path, ONE).tasks == work_item_detail(STUCK).tasks


@pytest.mark.edge
def test_a_file_of_a_work_item_in_backlog_holding_a_blocked_task_is_refused(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, STUCK)
    path = tmp_path / FILE
    path.write_text(
        path.read_text("utf-8").replace('state = "started"', 'state = "backlog"', 1), "utf-8"
    )
    with pytest.raises(WorkItemFileError, match=r"CH-0001.toml holds no Chore"):
        read_work_item(tmp_path, ONE)
