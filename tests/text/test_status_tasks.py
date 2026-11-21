"""The text of status under InProgress: the Tasks being worked, each on a line under its item."""

from datetime import UTC, datetime

import pytest

from flowgraph.task import TaskRow
from flowgraph.text import status_text
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
DONE = TaskRow("T-0001", "a done task", "an output", "", "completed", "abc1234")
HELD = TaskRow("T-0002", "a held task", "an output", "", "blocked", "", "a reason", "a reviewer")
BEGUN = TaskRow("T-0003", "a begun task", "an output", "", "started")
LATER = TaskRow("T-0004", "a later task", "an output", "", "backlog")


def started(number: int, *tasks: TaskRow) -> WorkItemRow:
    """A started Story of that number holding the Tasks."""
    return WorkItemRow(
        f"S-000{number}", f"title {number}", "started", created=CREATED, tasks=list(tasks)
    )


def test_the_started_task_is_listed_under_its_work_item_marked_as_the_one_worked() -> None:
    assert status_text([started(1, DONE, BEGUN, LATER)]).splitlines()[2:4] == [
        "  S-0001  1/3 T  title 1",
        "    => T-0003  a begun task",
    ]


def test_a_blocked_task_is_listed_marked_as_blocked_with_what_it_waits_on() -> None:
    assert status_text([started(1, HELD)]).splitlines()[3] == (
        "    !  T-0002  a held task  -- waiting on a reviewer"
    )


def test_the_tasks_being_worked_are_listed_in_the_order_of_the_file() -> None:
    assert status_text([started(1, HELD, BEGUN)]).splitlines()[3:] == [
        "    !  T-0002  a held task  -- waiting on a reviewer",
        "    => T-0003  a begun task",
        "Completed (0)",
    ]


def test_a_task_line_does_not_count_toward_the_top() -> None:
    rows = [started(1, BEGUN), started(2, BEGUN)]
    assert status_text(rows, top=1).splitlines()[1:] == [
        "InProgress (2)",
        "  S-0001  0/1 T  title 1",
        "    => T-0003  a begun task",
        "  ... 1 more",
        "Completed (0)",
    ]
