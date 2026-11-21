"""An Upkeep past Backlog in its file: kept with its times, commit and Tasks, read back whole."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.task import TaskRow, make_task, make_task_id
from flowgraph.upkeep import (
    UpkeepRow,
    UpkeepState,
    append_task,
    completed_task,
    completed_upkeep,
    make_upkeep,
    make_upkeep_id,
    read_task_ids,
    read_upkeep,
    read_upkeep_detail,
    read_upkeep_rows,
    started_task,
    started_upkeep,
    write_upkeep,
)

pytestmark = pytest.mark.edge

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
SCENARIO = make_scenario("a behavior", "it runs", "it still holds")
TASK = make_task(make_task_id(3), "a task", "an output", "", CREATED)
UPKEEP = append_task(make_upkeep(make_upkeep_id(1), "a title", SCENARIO, "", CREATED), TASK)
BEGUN = started_task(started_upkeep(UPKEEP, ON), make_task_id(3), ON)
HALF = completed_task(BEGUN, make_task_id(3), ON, make_commit("abc1234"))
WHOLE = completed_upkeep(HALF, ON, make_commit("def5678"))


@pytest.mark.parametrize(
    "upkeep", [UPKEEP, BEGUN, HALF, WHOLE], ids=["backlog", "started", "task-done", "completed"]
)
def test_an_upkeep_in_any_state_is_read_back_whole(upkeep: UpkeepState, tmp_path: Path) -> None:
    write_upkeep(tmp_path, upkeep)
    assert read_upkeep(tmp_path, make_upkeep_id(1)) == upkeep


def test_a_completed_upkeep_is_read_as_a_completed_row_with_its_commit(tmp_path: Path) -> None:
    write_upkeep(tmp_path, WHOLE)
    tasks = [TaskRow("T-0003", "a task", "an output", "", "completed", "abc1234")]
    assert read_upkeep_rows(tmp_path) == [
        UpkeepRow(
            "U-0001", "a title", "completed", "def5678", created=CREATED, completed=ON, tasks=tasks
        )
    ]


def test_a_completed_upkeep_is_read_as_detail_with_its_tasks(tmp_path: Path) -> None:
    write_upkeep(tmp_path, WHOLE)
    detail = read_upkeep_detail(tmp_path, make_upkeep_id(1))
    assert (detail.state, detail.commit, detail.tasks) == (
        "completed",
        "def5678",
        [TaskRow("T-0003", "a task", "an output", "", "completed", "abc1234")],
    )


def test_the_task_ids_of_the_upkeeps_are_read(tmp_path: Path) -> None:
    write_upkeep(tmp_path, UPKEEP)
    assert read_task_ids(tmp_path) == ["T-0003"]
