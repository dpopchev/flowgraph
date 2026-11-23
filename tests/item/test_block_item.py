"""The block and the unblock of an item by its id: a started work item, and a Task as before."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.item.commands import Written
from flowgraph.item.moves import block_item, unblock_item
from flowgraph.record.queue import make_queue
from flowgraph.record.store import Store
from flowgraph.story import STORY, make_story_id
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    WorkItemState,
    append_task,
    blocked_task,
    blocked_work_item,
    make_work_item,
    started_task,
    started_work_item,
    work_item_row,
)

pytestmark = pytest.mark.command

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
BEGUN = datetime(2026, 1, 2, 8, 0, 0, tzinfo=UTC)
ON = datetime(2026, 1, 3, 9, 0, 0, tzinfo=UTC)
TASK = make_task(make_task_id(1), "a task", "an output", "", CREATED)
STORY_ITEM = append_task(
    make_work_item(make_story_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED), TASK
)
STARTED = started_task(started_work_item(STORY_ITEM, BEGUN), make_task_id(1), BEGUN)
BLOCKED = blocked_work_item(STARTED, "no key", "developer", ON)


def never(*_: object) -> Never:
    """A read or a write of the record that a block never asks for."""
    raise AssertionError("a block reads and saves the work items alone")


def store(items: Sequence[WorkItemState], saved: list[WorkItemState]) -> Store:
    """The store of a record holding those Stories, which notes what it saves."""
    held = {item.id: item for item in items}
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
    )


def test_the_block_of_a_started_work_item_says_its_id_and_the_message_of_its_commit() -> None:
    written = block_item("S-0001", "no key", "developer", store([STARTED], []), lambda: ON)
    assert written == Written("blocked S-0001\n", "chore: block S-0001 in the record")


def test_the_block_of_a_started_work_item_saves_it_blocked() -> None:
    saved: list[WorkItemState] = []
    block_item("S-0001", "no key", "developer", store([STARTED], saved), lambda: ON)
    assert saved == [BLOCKED]


def test_the_unblock_of_a_blocked_work_item_says_its_id_and_the_message_of_its_commit() -> None:
    written = unblock_item("S-0001", store([BLOCKED], []))
    assert written == Written("unblocked S-0001\n", "chore: unblock S-0001 in the record")


def test_the_unblock_of_a_blocked_work_item_saves_it_started() -> None:
    saved: list[WorkItemState] = []
    unblock_item("S-0001", store([BLOCKED], saved))
    assert saved == [STARTED]


def test_a_task_is_still_blocked_through_the_task() -> None:
    saved: list[WorkItemState] = []
    written = block_item("T-0001", "no review", "the reviewer", store([STARTED], saved), lambda: ON)
    assert (written.out, saved) == (
        "blocked T-0001 of S-0001\n",
        [blocked_task(STARTED, make_task_id(1), "no review", "the reviewer", ON)],
    )
