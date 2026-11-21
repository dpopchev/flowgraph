"""One started Task among the Tasks of a work item: a second start or unblock is refused."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest
import tomli_w

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.task import (
    TaskInProgressError,
    TaskState,
    blocked,
    completed,
    make_task,
    make_task_id,
    started,
)
from flowgraph.task_list import at_most_one_started, started_among, unblocked_among
from flowgraph.work_item import (
    WorkItemFileError,
    append_task,
    make_kind,
    make_work_item,
    make_work_item_id,
    read_work_item,
    started_task,
    started_work_item,
    write_work_item,
)

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
FIRST = make_task(make_task_id(1), "a task", "an output", "", CREATED)
SECOND = make_task(make_task_id(2), "another task", "another output", "", CREATED)
BEGUN = started(FIRST, ON)
STUCK = blocked(BEGUN, "a reason", "someone", ON)
DONE = completed(BEGUN, ON, make_commit("abc1234"))
CHORE = make_kind("Chore", "a", "CH")
ONE = make_work_item_id(CHORE, 1)


@pytest.mark.model
def test_a_task_is_not_started_beside_a_started_one() -> None:
    with pytest.raises(
        TaskInProgressError,
        match=r"^T-0002 cannot start: T-0001 is started -- complete or block it first$",
    ):
        started_among((BEGUN, SECOND), make_task_id(2), ON)


@pytest.mark.model
@pytest.mark.parametrize("first", [STUCK, DONE], ids=["blocked", "completed"])
def test_a_task_is_started_beside_one_that_is_not_started(first: TaskState) -> None:
    assert started_among((first, SECOND), make_task_id(2), ON) == (first, started(SECOND, ON))


@pytest.mark.model
def test_a_task_is_not_unblocked_beside_a_started_one() -> None:
    with pytest.raises(
        TaskInProgressError,
        match=r"^T-0001 cannot be unblocked: T-0002 is started -- complete or block it first$",
    ):
        unblocked_among((STUCK, started(SECOND, ON)), make_task_id(1))


@pytest.mark.model
def test_tasks_with_one_started_among_them_are_as_they_are() -> None:
    assert at_most_one_started((BEGUN, SECOND, STUCK)) == (BEGUN, SECOND, STUCK)


@pytest.mark.model
def test_tasks_with_two_started_among_them_are_refused_naming_them() -> None:
    with pytest.raises(
        TaskInProgressError, match=r"^more than one Task is started: T-0001, T-0002$"
    ):
        at_most_one_started((BEGUN, started(SECOND, ON)))


@pytest.mark.edge
def test_a_file_holding_two_started_tasks_is_refused_naming_them(tmp_path: Path) -> None:
    bare = make_work_item(ONE, "a title", make_scenario("a", "b", "c"), "", CREATED)
    item = append_task(append_task(bare, FIRST), SECOND)
    write_work_item(tmp_path, started_task(started_work_item(item, ON), make_task_id(1), ON))
    path = tmp_path / "items" / "CH-0001.toml"
    held = tomllib.loads(path.read_text("utf-8"))
    held["tasks"][1] |= {"state": "started", "started": ON}
    path.write_text(tomli_w.dumps(held), "utf-8")
    with pytest.raises(
        WorkItemFileError,
        match=r"CH-0001.toml holds no Chore: more than one Task is started: T-0001, T-0002$",
    ):
        read_work_item(tmp_path, ONE)
