"""The top of status: the first items of a heading in the order it lists them, then the rest."""

from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.item import Store, status_item
from flowgraph.record.queue import make_queue
from flowgraph.story import STORY
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
DAYS = {number: datetime(2026, 1, 1 + number, tzinfo=UTC) for number in (1, 2, 3)}
ROWS = [
    WorkItemRow(
        f"S-000{number}", f"title {number}", "completed", "abc1234", created=CREATED, completed=day
    )
    for number, day in DAYS.items()
]


def never(*_: object) -> Never:
    """A read or a write that listing the record never asks for."""
    raise AssertionError("status reads the rows and the queue only")


def store() -> Store:
    """The store of a record holding ROWS, three Stories completed a day apart, and no queue."""
    return Store(
        find_work_item_rows=lambda kind: ROWS if kind == STORY else [],
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=lambda: make_queue([]),
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def test_the_top_of_completed_is_the_last_completed() -> None:
    assert status_item(store(), 2).splitlines()[2:] == [
        "Completed (3)",
        "  S-0003  abc1234  title 3",
        "  S-0002  abc1234  title 2",
        "  ... 1 more",
    ]
