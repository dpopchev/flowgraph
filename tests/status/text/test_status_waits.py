"""The text of status for a work item that waits: marked `~`, ending with the ids it depends on."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status import cut_lines, status_text
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
WAITING = WorkItemRow("S-0002", "a title", "backlog", created=CREATED, waits_for=["S-0001"])


def test_a_work_item_in_backlog_that_waits_is_marked_and_names_what_it_waits_for() -> None:
    assert status_text([WAITING]).splitlines()[1] == "~ S-0002  a title  -- depends on S-0001"


def test_a_work_item_names_each_one_it_waits_for_in_the_order_given() -> None:
    row = WorkItemRow(
        "S-0004", "a title", "backlog", created=CREATED, waits_for=["S-0003", "S-0001"]
    )
    assert status_text([row]).splitlines()[1].endswith("-- depends on S-0003, S-0001")


def test_a_work_item_in_backlog_that_waits_for_nothing_carries_no_mark() -> None:
    row = WorkItemRow("S-0002", "a title", "backlog", created=CREATED)
    assert status_text([row]).splitlines()[1] == "  S-0002  a title"


def test_a_feature_in_backlog_whose_first_work_item_waits_is_marked_as_it_is() -> None:
    feature = FeatureRow("F-0001", "a feature", "Backlog", 0, 2, waits_for=["S-0001"])
    assert status_text([feature]).splitlines()[1] == (
        "~ F-0001  0/2 W  a feature  -- depends on S-0001"
    )


def test_a_line_that_waits_is_cut_to_the_width_of_the_terminal_as_any_other() -> None:
    assert cut_lines(status_text([WAITING]), 20).splitlines()[1] == "~ S-0002  a title..."
