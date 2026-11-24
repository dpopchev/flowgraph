"""The text of status with Features: each one line in its bucket, its started work item under it."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status import same_top, status_text
from flowgraph.task import TaskRow
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
        "  S-0001  []  a title",
        "  F-0001  0/2 W  a feature title",
    ]


def test_a_feature_is_listed_among_the_work_items_of_its_bucket_in_the_order_given() -> None:
    assert status_text(ROWS).splitlines()[-3:] == [
        "Completed (2)",
        "  F-0003  a done feature",
        "  S-0006  abc1234  a done title",
    ]


def test_a_feature_completed_in_a_commit_is_listed_with_it_between_its_id_and_its_title() -> None:
    landed = FeatureRow("F-0004", "a landed feature", "Completed", 2, 2, commit="def5678")
    assert status_text([landed]).splitlines()[-1] == "  F-0004  def5678  a landed feature"


def test_a_completed_feature_with_its_completed_work_items_is_one_line_with_its_commit() -> None:
    done = WorkItemRow("S-0006", "a done title", "completed", "abc1234", created=CREATED)
    landed = FeatureRow(
        "F-0004", "a landed feature", "Completed", 1, 1, work_items=[done], commit="def5678"
    )
    assert status_text([landed]).splitlines()[-2:] == [
        "Completed (1)",
        "  F-0004  def5678  a landed feature",
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
    assert status_text([BEGUN, ALONE, OTHER], same_top(2)).splitlines()[1:] == [
        "InProgress (3)",
        "  F-0002  1/4 W  a begun feature",
        "    S-0003  1/2 T  a worked title",
        "      => T-0002  a begun task",
        "    S-0002  0/0 T  a begun title",
        "  S-0004  0/0 T  a title that stands alone",
        "  ... 1 more",
        "Completed (0)",
    ]


def waiting(number: int, waiting_on: str) -> TaskRow:
    """A blocked Task of that number, waiting on that."""
    return TaskRow(
        f"T-000{number}", "a held task", "an output", "", "blocked", "", "a reason", waiting_on
    )


def holding(*tasks: TaskRow) -> FeatureRow:
    """A started Feature whose one started work item holds the Tasks."""
    worked = WorkItemRow(
        "S-0003", "a worked title", "started", parent="F-0002", created=CREATED, tasks=list(tasks)
    )
    return FeatureRow("F-0002", "a begun feature", "InProgress", 0, 1, started=[worked])


def test_a_feature_whose_started_work_item_holds_a_blocked_task_is_marked_as_blocked() -> None:
    assert status_text([holding(waiting(1, "a reviewer"))]).splitlines()[2:4] == [
        "! F-0002  0/1 W  a begun feature",
        "  waiting on a reviewer: a reason",
    ]


def test_a_marked_feature_waits_on_what_the_first_blocked_task_of_its_work_item_waits_on() -> None:
    marked = holding(TASKS[0], waiting(3, "a reviewer"), waiting(4, "a release"))
    assert status_text([marked]).splitlines()[2:4] == [
        "! F-0002  0/1 W  a begun feature",
        "  waiting on a reviewer: a reason",
    ]


def test_a_started_task_beside_the_blocked_one_does_not_lift_the_mark_of_the_feature() -> None:
    marked = holding(waiting(3, "a reviewer"), TASKS[1])
    assert status_text([marked]).splitlines()[2:4] == [
        "! F-0002  0/1 W  a begun feature",
        "  waiting on a reviewer: a reason",
    ]


def test_a_blocked_feature_gives_what_it_waits_on_and_its_own_reason_below() -> None:
    blocked = FeatureRow(
        "F-0002",
        "a begun feature",
        "InProgress",
        0,
        1,
        waiting_on="a sponsor",
        block_reason="no budget",
    )
    assert status_text([blocked]).splitlines()[2:4] == [
        "! F-0002  0/1 W  a begun feature",
        "  waiting on a sponsor: no budget",
    ]
