"""The Completed of status: the last completed first, by kind and number when at one time."""

from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.item import Store, status_item
from flowgraph.queue import make_queue
from flowgraph.story import STORY
from flowgraph.upkeep import UPKEEP
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
EARLY = datetime(2026, 1, 2, tzinfo=UTC)
LATE = datetime(2026, 1, 3, tzinfo=UTC)
ROWS = {
    STORY: [
        WorkItemRow("S-0001", "a story", "completed", "abc1234", created=CREATED, completed=EARLY),
        WorkItemRow(
            "S-0002", "a last story", "completed", "abc1234", created=CREATED, completed=LATE
        ),
        WorkItemRow(
            "S-0003", "a twin story", "completed", "abc1234", created=CREATED, completed=EARLY
        ),
    ],
    UPKEEP: [
        WorkItemRow("U-0001", "an upkeep", "completed", "abc1234", created=CREATED, completed=LATE)
    ],
}


def never(*_: object) -> Never:
    """A read or a write that listing the record never asks for."""
    raise AssertionError("status reads the rows and the queue only")


def store() -> Store:
    """The store of a record holding ROWS and no queue."""
    return Store(
        find_work_item_rows=lambda kind: ROWS.get(kind, []),
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=lambda: make_queue([]),
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def test_completed_is_listed_the_last_completed_first() -> None:
    assert status_item(store()).splitlines()[3::2] == [
        "  S-0002  abc1234  a last story",
        "  S-0001  abc1234  a story",
    ]


def test_work_items_completed_at_one_time_are_listed_by_kind_and_number() -> None:
    assert status_item(store()).splitlines()[3:] == [
        "  S-0002  abc1234  a last story",
        "  U-0001  abc1234  an upkeep",
        "  S-0001  abc1234  a story",
        "  S-0003  abc1234  a twin story",
    ]
