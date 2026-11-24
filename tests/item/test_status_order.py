"""The Backlog of status: listed in queue order across the kinds, the rest as they were added."""

from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.item.commands import Store, status_item
from flowgraph.record.queue import Queue, make_queue
from flowgraph.story import STORY, make_story_id
from flowgraph.upkeep import UPKEEP
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

EARLY = datetime(2026, 1, 1, tzinfo=UTC)
LATE = datetime(2026, 1, 2, tzinfo=UTC)
ROWS = {
    STORY: [
        WorkItemRow("S-0001", "a story", "backlog", created=LATE),
        WorkItemRow("S-0002", "a done story", "completed", "abc1234", created=EARLY),
        WorkItemRow("S-0003", "a twin story", "backlog", created=EARLY),
    ],
    UPKEEP: [WorkItemRow("U-0001", "an upkeep", "backlog", created=EARLY)],
}


def never(*_: object) -> Never:
    """A read or a write that listing the record never asks for."""
    raise AssertionError("status reads the rows and the queue only")


def store(queue: Queue) -> Store:
    """The store of a record holding ROWS and that queue."""
    return Store(
        find_work_item_rows=lambda kind: ROWS.get(kind, []),
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=lambda: [],
        save_work_item=never,
        load_queue=lambda: queue,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def test_the_backlog_is_listed_as_added_and_by_kind_and_id_when_added_at_one_time() -> None:
    assert status_item(store(make_queue([]))) == (
        "backlog (3)\n"
        "> S-0003  []  a twin story\n"
        "  U-0001  []  an upkeep\n"
        "  S-0001  []  a story\n"
        "in-progress (0)\n"
        "completed (1)\n"
        "  S-0002  abc1234  a done story\n"
    )


def test_a_placed_work_item_is_listed_above_the_ones_never_placed() -> None:
    assert status_item(store(make_queue([make_story_id(1)]))).splitlines()[1:4] == [
        "> S-0001  []  a story",
        "  S-0003  []  a twin story",
        "  U-0001  []  an upkeep",
    ]
