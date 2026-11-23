"""The check of a Task at its complete: the runner is given the command and the directory."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.development.task_check import TaskCheckError, check_task_passes
from flowgraph.development.task_run import check_task_run
from flowgraph.record.queue import make_queue
from flowgraph.record.store import Store
from flowgraph.story import STORY, make_story_id
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    WorkItemState,
    append_task,
    blocked_work_item,
    make_work_item,
    started_task,
    started_work_item,
    work_item_row,
)

pytestmark = pytest.mark.model

WHERE = Path("/src/project.worktrees/S-0001-a-story")
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
CHECKED = make_task(make_task_id(1), "a task", "an output", "", CREATED, "make test")
STARTED = started_task(
    started_work_item(
        append_task(
            make_work_item(make_story_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED),
            CHECKED,
        ),
        CREATED,
    ),
    make_task_id(1),
    CREATED,
)


def never(*_: object) -> Never:
    """A read or a write of the record that the run of a check never asks for."""
    raise AssertionError("the run of a check reads the work items alone")


def holding(item: WorkItemState) -> Store:
    """The store of a record holding that Story alone."""
    return Store(
        find_work_item_rows=lambda kind: [work_item_row(item)] if kind == STORY else [],
        load_work_item=lambda _: item,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=lambda: make_queue([]),
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def test_a_task_of_a_blocked_work_item_runs_no_check() -> None:
    asked: list[str] = []

    def run(command: str, directory: Path) -> int:
        asked.append(command)
        return 0

    blocked = blocked_work_item(STARTED, "no key", "developer", CREATED)
    check_task_run("T-0001", holding(blocked), WHERE, lambda _: None, WHERE, run)
    assert asked == []


def test_the_runner_is_given_the_command_and_the_directory() -> None:
    asked: list[tuple[str, Path]] = []

    def run(command: str, directory: Path) -> int:
        asked.append((command, directory))
        return 0

    check_task_passes("T-0001", "make test", WHERE, run)
    assert asked == [("make test", WHERE)]


def test_a_check_that_exits_with_zero_is_taken() -> None:
    assert check_task_passes("T-0001", "make test", WHERE, lambda command, directory: 0) is None


def test_a_check_that_exits_with_another_status_is_refused_naming_the_task_and_the_status() -> None:
    with pytest.raises(
        TaskCheckError,
        match=r'^T-0001 cannot complete: its check "make test" exited with status 2$',
    ):
        check_task_passes("T-0001", "make test", WHERE, lambda command, directory: 2)


@pytest.mark.parametrize("check", [None, ""])
def test_a_task_that_holds_no_check_never_calls_the_runner(check: str | None) -> None:
    def run(command: str, directory: Path) -> int:
        raise AssertionError("the runner was called")

    assert check_task_passes("T-0001", check, WHERE, run) is None
