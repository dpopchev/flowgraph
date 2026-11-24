"""The text of status: what a line adds is on a line of its own right below it, under its id."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status import cut_lines, status_text
from flowgraph.status.work_item_lines import added_below
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
BEGUN = TaskRow("T-0002", "a begun task", "an output", "", "started")
HELD = TaskRow("T-0003", "a held task", "an output", "", "blocked", "", "a reason", "a reviewer")
WAITING = WorkItemRow(
    "S-0002", "a title", "backlog", created=CREATED, waits_for=["S-0003", "S-0001"]
)


def blocked(*tasks: TaskRow, reason: str = "a reason", parent: str = "") -> WorkItemRow:
    """The blocked Story S-0001 holding the Tasks, waiting on a reviewer for that reason."""
    return WorkItemRow(
        "S-0001",
        "title 1",
        "blocked",
        parent=parent,
        created=CREATED,
        started=CREATED,
        block_reason=reason,
        waiting_on="a reviewer",
        tasks=list(tasks),
    )


def removed(reason: str, superseded_by: str = "") -> WorkItemRow:
    """The removed Story S-0001 with that reason, superseded by that work item if any."""
    return WorkItemRow(
        "S-0001",
        "a title",
        "removed",
        reason=reason,
        created=CREATED,
        superseded_by=superseded_by,
    )


def test_a_line_with_nothing_to_add_is_the_line() -> None:
    assert added_below("S-0001  a title", "") == "S-0001  a title"


def test_a_waiting_work_item_names_what_it_depends_on_on_a_line_below_it() -> None:
    assert status_text([WAITING]).splitlines()[1:3] == [
        "~ S-0002  []  a title",
        "  depends on S-0003, S-0001",
    ]


def test_a_blocked_work_item_is_its_line_then_what_it_waits_on_then_its_task_lines() -> None:
    assert status_text([blocked(BEGUN)]).splitlines()[2:5] == [
        "! S-0001  0/1 T  title 1",
        "  waiting on a reviewer: a reason",
        "    => T-0002  a begun task",
    ]


def test_a_block_with_no_reason_reads_waiting_on_alone() -> None:
    assert status_text([blocked(BEGUN, reason="")]).splitlines()[3] == "  waiting on a reviewer"


def test_a_blocked_task_waits_on_a_line_below_it_under_its_id() -> None:
    started = WorkItemRow("S-0001", "title 1", "started", created=CREATED, tasks=[HELD])
    assert status_text([started]).splitlines()[3:5] == [
        "    !  T-0003  a held task",
        "       waiting on a reviewer: a reason",
    ]


def test_the_words_of_a_blocked_work_item_under_a_feature_begin_four_columns_in() -> None:
    under = blocked(BEGUN, parent="F-0001")
    feature = FeatureRow("F-0001", "a feature title", "InProgress", 0, 1, started=[under])
    assert status_text([feature]).splitlines()[5] == "    waiting on a reviewer: a reason"


def test_the_words_of_a_blocked_task_under_a_feature_begin_nine_columns_in() -> None:
    under = blocked(HELD, parent="F-0001")
    feature = FeatureRow("F-0001", "a feature title", "InProgress", 0, 1, started=[under])
    assert status_text([feature]).splitlines()[7] == "         waiting on a reviewer: a reason"


def test_a_removed_work_item_gives_its_reason_on_a_line_below_it() -> None:
    assert status_text([removed("dropped")]).splitlines()[4:6] == ["  S-0001  a title", "  dropped"]


def test_a_superseded_work_item_with_no_reason_reads_superseded_by_alone() -> None:
    assert status_text([removed("", "S-0002")]).splitlines()[5] == "  superseded by S-0002"


def test_the_two_lines_are_cut_to_the_width_apart() -> None:
    assert cut_lines(status_text([WAITING]), 20).splitlines()[1:3] == [
        "~ S-0002  []  a t...",
        "  depends on S-00...",
    ]


def test_a_removed_feature_gives_its_reason_on_a_line_below_it() -> None:
    feature = FeatureRow(
        "F-0001", "a feature title", "Removed", 0, 0, reason="dropped from the plan"
    )
    assert status_text([feature]).splitlines()[3:6] == [
        "Removed (1)",
        "  F-0001  a feature title",
        "  dropped from the plan",
    ]
