"""The text of status when several lines can start now: each marked `>`, counted past the top."""

from datetime import UTC, datetime

import pytest

from flowgraph.status import same_top, status_text
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def line(item: int, *, marked: bool = False) -> WorkItemRow:
    """A work item in Backlog of that number, marked as able to start now or not."""
    return WorkItemRow(f"S-{item:04}", "a title", "backlog", created=CREATED, next_to_start=marked)


def test_every_line_that_can_start_is_marked() -> None:
    rows = [line(1, marked=True), line(2), line(3, marked=True)]
    assert status_text(rows).splitlines()[1:-2] == [
        "> S-0001  []  a title",
        "  S-0002  []  a title",
        "> S-0003  []  a title",
    ]


def test_every_marked_line_the_top_leaves_out_is_counted_in_the_more_line_and_not_listed() -> None:
    rows = [line(1), line(2), line(3, marked=True), line(4), line(5, marked=True)]
    assert status_text(rows, same_top(2)).splitlines()[1:-2] == [
        "  S-0001  []  a title",
        "  S-0002  []  a title",
        "  ... 3 more, 2 can start",
    ]


def test_a_marked_line_inside_the_top_is_listed_and_one_beyond_it_is_counted() -> None:
    rows = [line(1, marked=True), line(2), line(3, marked=True)]
    assert status_text(rows, same_top(2)).splitlines()[1:-2] == [
        "> S-0001  []  a title",
        "  S-0002  []  a title",
        "  ... 1 more, 1 can start",
    ]


def test_the_count_of_the_heading_stays_that_of_every_line() -> None:
    rows = [line(1), line(2), line(3, marked=True), line(4, marked=True)]
    assert status_text(rows, same_top(1)).splitlines()[0] == "Backlog (4)"
