"""The check of a Task in the file of its work item: kept in every state, none in an old file."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    WorkItemState,
    append_task,
    blocked_task,
    completed_task,
    make_kind,
    make_work_item,
    make_work_item_id,
    read_work_item,
    read_work_item_detail,
    removed_task,
    started_task,
    started_work_item,
    write_work_item,
)

pytestmark = pytest.mark.edge

CHORE = make_kind("Chore", "a", "CH")
ID = make_work_item_id(CHORE, 1)
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
SCENARIO = make_scenario("a state", "an action", "another state")
TASK = make_task(make_task_id(3), "a task title", "an output", "", CREATED, "make test")
BARE = append_task(make_work_item(ID, "a title", SCENARIO, "", CREATED), TASK)
HALF = started_task(started_work_item(BARE, ON), make_task_id(3), ON)
STUCK = blocked_task(HALF, make_task_id(3), "a reason", "someone", ON)
WHOLE = completed_task(HALF, make_task_id(3), ON, make_commit("abc1234"))
GONE = removed_task(HALF, make_task_id(3), "a reason", ON)
OLD = """id = "CH-0001"
state = "backlog"
title = "a title"
created = 2026-01-01T12:30:15Z

[criterion]
given = "a state"
when = "an action"
then = "another state"

[[tasks]]
id = "T-0003"
state = "backlog"
title = "a task title"
expected_output = "an output"
created = 2026-01-01T12:30:15Z
"""


@pytest.mark.parametrize(
    "item",
    [BARE, HALF, STUCK, WHOLE, GONE],
    ids=["backlog", "started", "blocked", "done", "removed"],
)
def test_a_task_with_its_check_reads_back_whole_in_any_state(
    tmp_path: Path, item: WorkItemState
) -> None:
    write_work_item(tmp_path, item)
    assert read_work_item(tmp_path, ID) == item


def test_a_file_whose_task_holds_no_check_reads_with_none(tmp_path: Path) -> None:
    (tmp_path / "items").mkdir()
    (tmp_path / "items" / "CH-0001.toml").write_text(OLD, encoding="utf-8")
    assert read_work_item(tmp_path, ID).tasks[0].check is None


def test_the_detail_of_a_work_item_lists_the_check_of_its_task(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE)
    assert read_work_item_detail(tmp_path, ID).tasks[0].check == "make test"
