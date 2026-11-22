"""The text of status with Features: each one line in its bucket, its started work item under it."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.task import TaskRow
from flowgraph.text import status_text
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
TASKS = [
    TaskRow("T-0001", "a done task", "an output", "", "completed", "abc1234"),
    TaskRow("T-0002", "a begun task", "an output", "", "started"),
]
UNDER = WorkItemRow("S-0002", "a begun title", "started", parent="F-0002", created=CREATED)
WORKED = WorkItemRow(
    "S-0003", "a worked title", "started", parent="F-0002", created=CREATED, tasks=TASKS
)
ALONE = WorkItemRow("S-0004", "a title that stands alone", "started", created=CREATED)
OTHER = WorkItemRow("S-0005", "another that stands alone", "started", created=CREATED)
BEGUN = FeatureRow("F-0002", "a begun feature", "InProgress", 1, 4, started=[WORKED, UNDER])
ROWS = [
    WorkItemRow("S-0001", "a title", "backlog", created=CREATED),
    FeatureRow("F-0001", "a feature title", "Backlog", completed=0, held=2),
    BEGUN,
    ALONE,
    FeatureRow("F-0003", "a done feature", "Completed", completed=2, held=2),
    WorkItemRow("S-0006", "a done title", "completed", "abc1234", created=CREATED),
]


def test_a_feature_is_listed_in_its_bucket_as_one_line_with_its_progress() -> None:
    assert status_text(ROWS).splitlines()[:3] == [
        "Backlog (2)",
        "  S-0001  a title",
        "  F-0001  0/2 W  a feature title",
    ]


def test_a_feature_is_listed_among_the_work_items_of_its_bucket_in_the_order_given() -> None:
    assert status_text(ROWS).splitlines()[-3:] == [
        "Completed (2)",
        "  F-0003  2/2 W  a done feature",
        "  S-0006  abc1234  a done title",
    ]


def test_the_started_work_items_of_a_feature_are_listed_under_its_line_indented() -> None:
    assert status_text([BEGUN]).splitlines()[1:6] == [
        "InProgress (1)",
        "  F-0002  1/4 W  a begun feature",
        "    S-0003  1/2 T  a worked title",
        "      => T-0002  a begun task",
        "    S-0002  0/0 T  a begun title",
    ]


def test_a_work_item_under_its_feature_counts_neither_beside_the_heading_nor_toward_the_top() -> (
    None
):
    assert status_text([BEGUN, ALONE, OTHER], top=2).splitlines()[1:] == [
        "InProgress (3)",
        "  F-0002  1/4 W  a begun feature",
        "    S-0003  1/2 T  a worked title",
        "      => T-0002  a begun task",
        "    S-0002  0/0 T  a begun title",
        "  S-0004  0/0 T  a title that stands alone",
        "  ... 1 more",
        "Completed (0)",
    ]
