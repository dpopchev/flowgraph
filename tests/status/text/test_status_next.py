"""The text of status for the next to start: its line marked `>`, counted when the top cuts."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status import cut_lines, same_top, status_text
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
NEXT = WorkItemRow("S-0002", "a title", "backlog", created=CREATED, next_to_start=True)


def plain(item: int) -> WorkItemRow:
    """A work item in Backlog that is not the next to start, of that number."""
    return WorkItemRow(f"S-{item:04}", "a title", "backlog", created=CREATED)


def test_the_next_to_start_is_marked() -> None:
    assert status_text([NEXT]).splitlines()[1] == "> S-0002  []  a title"


def test_a_feature_that_is_the_next_to_start_is_marked() -> None:
    feature = FeatureRow("F-0001", "a feature", "Backlog", 0, 2, next_to_start=True)
    assert status_text([feature]).splitlines()[1] == "> F-0001  0/2 W  a feature"


def test_the_line_of_the_next_to_start_is_cut_to_the_width_of_the_terminal_as_any_other() -> None:
    assert cut_lines(status_text([NEXT]), 12).splitlines()[1] == "> S-0002 ..."


def test_the_next_to_start_left_out_by_the_top_is_counted_in_the_more_line_and_not_listed() -> None:
    last = WorkItemRow("S-0004", "a title", "backlog", created=CREATED, next_to_start=True)
    rows = [plain(1), plain(2), plain(3), last]
    assert status_text(rows, same_top(2)).splitlines()[1:-2] == [
        "  S-0001  []  a title",
        "  S-0002  []  a title",
        "  ... 2 more, 1 can start",
    ]


def test_the_next_to_start_inside_the_top_is_listed_once() -> None:
    rows = [plain(1), NEXT, plain(3)]
    assert status_text(rows, same_top(2)).splitlines()[1:-2] == [
        "  S-0001  []  a title",
        "> S-0002  []  a title",
        "  ... 1 more, 0 can start",
    ]


def test_a_top_that_leaves_none_out_lists_no_more_line() -> None:
    assert status_text([plain(1), NEXT], same_top(2)).splitlines()[1:-2] == [
        "  S-0001  []  a title",
        "> S-0002  []  a title",
    ]
