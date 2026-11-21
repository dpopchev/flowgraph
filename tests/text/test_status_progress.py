"""The text of status under InProgress: a work item with its Tasks completed of all."""

from datetime import UTC, datetime

import pytest

from flowgraph.task import TaskRow
from flowgraph.text import status_text
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
    rows = [WorkItemRow("ST-0001", "a title", "started", created=CREATED, tasks=TASKS)]
    assert status_text(rows).splitlines()[2] == "  ST-0001  1/4 T  a title"


def test_a_started_work_item_without_a_task_read_is_listed_with_none_of_none() -> None:
    rows = [WorkItemRow("ST-0001", "a title", "started", created=CREATED)]
    assert status_text(rows).splitlines()[2] == "  ST-0001  0/0 T  a title"
