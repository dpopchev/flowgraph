"""The rule of review: a started work item holding a Task, every Task of it completed."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status.review import ready_for_review, review_ids
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def task(state: str) -> TaskRow:
    """A Task in that state."""
    return TaskRow("T-0001", "a task", "an output", "", state)


def item(number: int, state: str, *tasks: TaskRow) -> WorkItemRow:
    """A Story of that number in that state holding the Tasks."""
    return WorkItemRow(f"S-{number:04}", "a title", state, created=CREATED, tasks=list(tasks))


def test_a_started_work_item_with_every_task_completed_is_ready() -> None:
    assert ready_for_review(item(1, "started", task("completed"), task("completed")))


def test_a_started_work_item_with_no_task_is_not_ready() -> None:
    assert not ready_for_review(item(1, "started"))


def test_a_started_work_item_with_a_task_in_backlog_is_not_ready() -> None:
    assert not ready_for_review(item(1, "started", task("completed"), task("backlog")))


def test_a_started_work_item_with_a_started_task_is_not_ready() -> None:
    assert not ready_for_review(item(1, "started", task("completed"), task("started")))


def test_a_started_work_item_with_a_blocked_task_is_not_ready() -> None:
    assert not ready_for_review(item(1, "started", task("completed"), task("blocked")))


def test_a_completed_work_item_is_not_ready() -> None:
    assert not ready_for_review(item(1, "completed", task("completed")))


def test_review_ids_lists_the_ready_rows_in_the_order_given() -> None:
    ready = [item(2, "started", task("completed")), item(1, "started", task("completed"))]
    assert review_ids([ready[0], item(3, "started", task("backlog")), ready[1]]) == [
        "S-0002",
        "S-0001",
    ]


def test_review_ids_of_a_feature_lists_the_ready_rows_among_those_it_lists() -> None:
    ready = item(2, "started", task("completed"))
    feature = FeatureRow(
        "F-0001",
        "a feature",
        "InProgress",
        0,
        2,
        started=[item(1, "started", task("backlog")), ready],
        is_started=True,
    )
    assert review_ids([feature]) == ["S-0002"]
