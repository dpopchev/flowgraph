"""The lines that can start now beside a blocked work item: it takes a place as a started one."""

from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.record.queue import make_queue
from flowgraph.record.store import Store
from flowgraph.status.next import Within, start_now_ids
from flowgraph.status.view import status_rows
from flowgraph.story import STORY
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
TASK = TaskRow("T-0001", "a task", "an output", "", "backlog")
ROWS = [
    WorkItemRow(
        "S-0001",
        "a blocked title",
        "blocked",
        created=CREATED,
        started=CREATED,
        block_reason="no key",
        waiting_on="developer",
        tasks=[TaskRow("T-0002", "a task", "an output", "", "started")],
    ),
    WorkItemRow("S-0002", "a title", "backlog", created=CREATED, tasks=[TASK]),
]


def never(*_: object) -> Never:
    """A read or a write that listing the record never asks for."""
    raise AssertionError("status reads the rows and the queue only")


def test_no_line_is_marked_beside_a_blocked_work_item_under_a_limit_of_one() -> None:
    store = Store(
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
    assert start_now_ids(status_rows(store, Within(1))) == []
