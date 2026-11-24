"""The remove of a work item by its id: a started one is removed where its Tasks are written."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.item.commands import remove_item
from flowgraph.record.queue import make_queue
from flowgraph.record.store import Store
from flowgraph.story import STORY, make_story_id
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    RemovedAlreadyError,
    WorkItemState,
    append_task,
    blocked_work_item,
    completed_task,
    make_work_item,
    removed_work_item,
    started_task,
    started_work_item,
    work_item_row,
)

pytestmark = pytest.mark.command

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
BEGUN = datetime(2026, 1, 2, 8, 0, 0, tzinfo=UTC)
ON = datetime(2026, 1, 3, 9, 0, 0, tzinfo=UTC)
ITEM = make_story_id(1)
FIRST, SECOND = make_task_id(1), make_task_id(2)
QUEUED = append_task(
    append_task(
        make_work_item(ITEM, "a title", make_scenario("a", "b", "c"), "", CREATED),
        make_task(FIRST, "a task", "an output", "", CREATED),
    ),
    make_task(SECOND, "another task", "an output", "", CREATED),
)
STARTED = started_work_item(QUEUED, BEGUN)
WORKED = completed_task(started_task(STARTED, FIRST, BEGUN), FIRST, ON, make_commit("abc1234"))
BLOCKED = blocked_work_item(WORKED, "no key", "developer", ON)


def never(*_: object) -> Never:
    """A read or a write of the record that a remove never asks for."""
    raise AssertionError("a remove loads and saves the work item alone")


def store(
    items: Sequence[WorkItemState],
    saved: list[WorkItemState],
    written: Sequence[WorkItemState] | None = (),
) -> Store:
    """The store of a record holding those Stories, which notes what it saves.

    Its load_written loads the work items written, none when written is None.
    """
    held = {item.id: item for item in items}
    elsewhere = {item.id: item for item in written or ()}
    return Store(
        find_work_item_rows=lambda kind: (
            [work_item_row(item) for item in items] if kind == STORY else []
        ),
        load_work_item=held.__getitem__,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=saved.append,
        load_queue=lambda: make_queue([]),
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
        load_written=None if written is None else elsewhere.__getitem__,
    )


def test_a_started_work_item_is_removed_from_the_copy_where_its_tasks_are_written() -> None:
    saved: list[WorkItemState] = []
    remove_item("S-0001", "pivoted", store([STARTED], saved, [WORKED]), lambda: ON)
    assert saved == [removed_work_item(WORKED, "pivoted", ON)]


def test_a_started_work_item_removed_names_itself_to_unbranch() -> None:
    written = remove_item("S-0001", "pivoted", store([STARTED], [], [WORKED]), lambda: ON)
    assert written.unbranches == ITEM


def test_a_blocked_copy_where_its_tasks_are_written_is_the_one_removed() -> None:
    saved: list[WorkItemState] = []
    remove_item("S-0001", "pivoted", store([STARTED], saved, [BLOCKED]), lambda: ON)
    assert saved == [removed_work_item(BLOCKED, "pivoted", ON)]


def test_a_started_work_item_with_no_load_written_is_removed_from_the_record() -> None:
    saved: list[WorkItemState] = []
    remove_item("S-0001", "pivoted", store([WORKED], saved, None), lambda: ON)
    assert saved == [removed_work_item(WORKED, "pivoted", ON)]


def test_a_work_item_in_backlog_names_none_to_unbranch_and_never_asks_load_written() -> None:
    held = replace(store([QUEUED], []), load_written=never)
    assert remove_item("S-0001", "pivoted", held, lambda: ON).unbranches is None


def test_a_remove_refused_saves_nothing() -> None:
    saved: list[WorkItemState] = []
    gone = removed_work_item(QUEUED, "filed by mistake", ON)
    with pytest.raises(RemovedAlreadyError):
        remove_item("S-0001", "pivoted", store([STARTED], saved, [gone]), lambda: ON)
    assert saved == []
