"""The JSON document of status: `ready_for_review` lists the work items marked `?`."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status.document import status_json
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
DONE = TaskRow("T-0001", "a done task", "an output", "", "completed", "abc1234")
LATER = TaskRow("T-0002", "a later task", "an output", "", "backlog")


def started(number: int, *tasks: TaskRow) -> WorkItemRow:
    """A started Story of that number holding the Tasks."""
    return WorkItemRow(f"S-{number:04}", "a title", "started", created=CREATED, tasks=list(tasks))


def document(*rows: WorkItemRow | FeatureRow) -> dict[str, Any]:
    """The document of the rows, parsed."""
    return json.loads(status_json(rows))


def test_ready_for_review_lists_the_ids_of_the_ready_rows_in_the_order_given() -> None:
    listed = document(started(2, DONE), started(3, LATER), started(1, DONE))
    assert listed["ready_for_review"] == ["S-0002", "S-0001"]


def test_ready_for_review_is_empty_when_no_row_is_ready() -> None:
    assert document(started(1, DONE, LATER))["ready_for_review"] == []


def test_ready_for_review_lists_a_ready_work_item_under_a_feature() -> None:
    feature = FeatureRow(
        "F-0001",
        "a feature",
        "InProgress",
        0,
        1,
        started=[started(1, DONE)],
        is_started=True,
    )
    assert document(feature)["ready_for_review"] == ["S-0001"]


def test_a_work_item_with_no_task_is_not_listed() -> None:
    assert document(started(1))["ready_for_review"] == []
