"""The text of status for a work item in Backlog: its count of Tasks in brackets."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status import status_text
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def tasks(count: int) -> list[TaskRow]:
    """That many Tasks in Backlog."""
    return [TaskRow(f"T-{n:04}", "a task", "an output", "", "backlog") for n in range(1, count + 1)]


def backlog(count: int, *, marked: bool = False) -> WorkItemRow:
    """A work item in Backlog holding that many Tasks, marked as the next to start or not."""
    return WorkItemRow(
        "S-0001", "a title", "backlog", created=CREATED, tasks=tasks(count), next_to_start=marked
    )


def lines(row: WorkItemRow) -> list[str]:
    """The lines of the text of status for that row alone."""
    return status_text([row]).splitlines()


def test_a_work_item_in_backlog_with_three_tasks_reads_them_in_brackets() -> None:
    assert lines(backlog(3))[1] == "  S-0001  [3 T]  a title"


def test_a_work_item_in_backlog_with_one_task_reads_it_in_brackets() -> None:
    assert lines(backlog(1))[1] == "  S-0001  [1 T]  a title"


def test_a_work_item_in_backlog_with_no_task_reads_empty_brackets() -> None:
    assert lines(backlog(0))[1] == "  S-0001  []  a title"


def test_one_that_waits_keeps_its_mark_and_its_words_around_the_brackets() -> None:
    row = WorkItemRow("S-0002", "a title", "backlog", created=CREATED, waits_for=["S-0001"])
    assert lines(row)[1:3] == ["~ S-0002  []  a title", "  depends on S-0001"]


def test_the_next_to_start_keeps_its_mark_before_the_brackets() -> None:
    assert lines(backlog(0, marked=True))[1] == "  S-0001  []  a title"


def test_a_completed_work_item_with_no_commit_reads_as_before() -> None:
    row = WorkItemRow("S-0001", "a title", "completed", created=CREATED)
    assert status_text([row]).splitlines()[-1] == "  S-0001  a title"


def test_a_removed_work_item_with_no_reason_reads_as_before() -> None:
    row = WorkItemRow("S-0001", "a title", "removed", created=CREATED)
    assert status_text([row]).splitlines()[-1] == "  S-0001  a title"


def test_a_work_item_marked_under_a_started_feature_reads_its_brackets_two_columns_in() -> None:
    row = WorkItemRow(
        "S-0003", "a title", "backlog", created=CREATED, tasks=tasks(1), next_to_start=True
    )
    feature = FeatureRow(
        "F-0001", "a feature", "in-progress", 0, 1, work_items=[row], is_started=True
    )
    assert "    S-0003  [1 T]  a title" in status_text([feature]).splitlines()
