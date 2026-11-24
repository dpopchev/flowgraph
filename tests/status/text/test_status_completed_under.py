"""The text of status with completed work items: under a Feature in progress, on no line else."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status import status_text
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
DONE_TASKS = [
    TaskRow("T-0001", "a done task", "an output", "", "completed", "abc1234"),
    TaskRow("T-0002", "another done task", "an output", "", "completed", "abc1234"),
]
ONE_DONE_TASK = [TaskRow("T-0003", "a task", "an output", "", "completed", "abc1234")]
TASKS = [
    TaskRow("T-0004", "a done task", "an output", "", "completed", "abc1234"),
    TaskRow("T-0005", "a begun task", "an output", "", "started"),
]
DONE = WorkItemRow("S-0001", "a done title", "completed", created=CREATED, tasks=DONE_TASKS)
OTHER_DONE = WorkItemRow(
    "S-0005", "another done title", "completed", created=CREATED, tasks=ONE_DONE_TASK
)
BARE_DONE = WorkItemRow("S-0006", "a bare done title", "completed", created=CREATED)
WORKED = WorkItemRow(
    "S-0003", "a worked title", "started", parent="F-0002", created=CREATED, tasks=TASKS
)
REMOVED = WorkItemRow(
    "S-0007", "a removed title", "removed", reason="a reason", parent="F-0002", created=CREATED
)
BACKLOG = WorkItemRow("S-0008", "a backlog title", "backlog", parent="F-0002", created=CREATED)
BEGUN = FeatureRow(
    "F-0002",
    "a begun feature",
    "InProgress",
    1,
    2,
    started=[WORKED],
    work_items=[WORKED, DONE],
)
ALONE = WorkItemRow("S-0004", "a title that stands alone", "started", created=CREATED)


def test_a_completed_work_item_under_a_feature_in_progress_is_its_last_line() -> None:
    assert status_text([BEGUN]).splitlines()[-2] == "    S-0001  2/2 T  a done title"


def test_a_completed_work_item_is_listed_after_a_started_one_with_its_task() -> None:
    assert status_text([BEGUN]).splitlines()[-3:-1] == [
        "      => T-0005  a begun task",
        "    S-0001  2/2 T  a done title",
    ]


def test_two_completed_work_items_are_listed_in_the_order_of_the_feature() -> None:
    feature = FeatureRow(
        "F-0002", "a begun feature", "InProgress", 2, 2, work_items=[DONE, OTHER_DONE]
    )
    assert status_text([feature]).splitlines()[-3:-1] == [
        "    S-0001  2/2 T  a done title",
        "    S-0005  1/1 T  another done title",
    ]


def test_a_completed_work_item_with_no_task_reads_zero_of_zero() -> None:
    feature = FeatureRow("F-0002", "a begun feature", "InProgress", 1, 1, work_items=[BARE_DONE])
    assert status_text([feature]).splitlines()[-2] == "    S-0006  0/0 T  a bare done title"


def test_a_completed_feature_lists_its_work_items_on_no_line() -> None:
    feature = FeatureRow(
        "F-0003", "a done feature", "Completed", 2, 2, work_items=[DONE, OTHER_DONE]
    )
    assert status_text([feature]).splitlines()[-2:] == [
        "Completed (1)",
        "  F-0003  a done feature",
    ]


def test_a_feature_in_backlog_lists_its_work_items_on_no_line() -> None:
    feature = FeatureRow("F-0001", "a feature title", "Backlog", 1, 2, work_items=[DONE])
    assert status_text([feature]).splitlines()[1:3] == [
        "  F-0001  1/2 W  a feature title",
        "InProgress (0)",
    ]


def test_a_removed_and_a_backlog_work_item_of_a_feature_are_on_no_line() -> None:
    feature = FeatureRow(
        "F-0002", "a begun feature", "InProgress", 0, 2, work_items=[REMOVED, BACKLOG]
    )
    text = status_text([feature])
    named = [line for line in text.splitlines() if "S-0007" in line or "S-0008" in line]
    assert named == []


def test_a_feature_with_a_completed_work_item_counts_once_toward_the_top() -> None:
    assert status_text([BEGUN, ALONE], top=1).splitlines()[1:] == [
        "InProgress (2)",
        "  F-0002  1/2 W  a begun feature",
        "    S-0003  1/2 T  a worked title",
        "      => T-0005  a begun task",
        "    S-0001  2/2 T  a done title",
        "  ... 1 more",
        "Completed (0)",
    ]
