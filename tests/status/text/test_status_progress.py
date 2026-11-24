"""The text of status under InProgress: a work item with its Tasks completed of all."""

from datetime import UTC, datetime

import pytest

from flowgraph.status import status_text
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
TASKS = [
    TaskRow("T-0001", "a task title", "an output", "", "completed", "abc1234"),
    TaskRow("T-0002", "a task title", "an output", "", "started"),
    TaskRow("T-0003", "a task title", "an output", "", "blocked", "", "a reason", "a reviewer"),
    TaskRow("T-0004", "a task title", "an output", "", "backlog"),
]


def test_a_started_work_item_is_listed_with_its_tasks_completed_of_all() -> None:
    rows = [WorkItemRow("S-0001", "a title", "started", created=CREATED, tasks=TASKS)]
    assert status_text(rows).splitlines()[2] == "  S-0001  1/4 T  a title"


def test_a_started_work_item_without_a_task_read_is_listed_with_none_of_none() -> None:
    rows = [WorkItemRow("S-0001", "a title", "started", created=CREATED)]
    assert status_text(rows).splitlines()[2] == "  S-0001  0/0 T  a title"


def removed(number: int) -> TaskRow:
    """The removed Task of that number, with its reason."""
    return TaskRow(f"T-000{number}", "a task title", "an output", "", "removed", reason="r")


@pytest.mark.parametrize(
    ("state", "line"),
    [("backlog", "  S-0001  0/1 T  a title"), ("completed", "@ S-0001  1/1 T  a title")],
    ids=["in-backlog", "completed"],
)
def test_a_started_work_item_counts_the_one_task_beside_two_removed(state: str, line: str) -> None:
    left = TaskRow("T-0003", "a task title", "an output", "", state)
    tasks = [removed(1), removed(2), left]
    rows = [WorkItemRow("S-0001", "a title", "started", created=CREATED, tasks=tasks)]
    assert status_text(rows).splitlines()[2] == line


def test_a_started_work_item_whose_every_task_is_removed_is_listed_with_none_of_none() -> None:
    tasks = [removed(1), removed(2)]
    rows = [WorkItemRow("S-0001", "a title", "started", created=CREATED, tasks=tasks)]
    assert status_text(rows).splitlines()[2] == "  S-0001  0/0 T  a title"
