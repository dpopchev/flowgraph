"""The text of status when several lines can start now: each marked `>`, kept when the top cuts."""

from datetime import UTC, datetime

import pytest

from flowgraph.status import status_text
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def line(item: int, *, marked: bool = False) -> WorkItemRow:
    """A work item in Backlog of that number, marked as able to start now or not."""
    return WorkItemRow(f"S-{item:04}", "a title", "backlog", created=CREATED, next_to_start=marked)


def test_every_line_that_can_start_is_marked() -> None:
    rows = [line(1, marked=True), line(2), line(3, marked=True)]
    assert status_text(rows).splitlines()[1:-2] == [
        "> S-0001  a title",
        "  S-0002  a title",
        "> S-0003  a title",
    ]


def test_every_marked_line_the_top_leaves_out_is_listed_after_the_top() -> None:
    rows = [line(1), line(2), line(3, marked=True), line(4), line(5, marked=True)]
    assert status_text(rows, 2).splitlines()[1:-2] == [
        "  S-0001  a title",
        "  S-0002  a title",
        "> S-0003  a title",
        "> S-0005  a title",
        "  ... 1 more",
    ]


def test_each_marked_line_is_listed_once_when_one_is_inside_the_top_and_one_is_not() -> None:
    rows = [line(1, marked=True), line(2), line(3, marked=True)]
    assert status_text(rows, 2).splitlines()[1:-2] == [
        "> S-0001  a title",
        "  S-0002  a title",
        "> S-0003  a title",
    ]


def test_the_count_of_the_heading_stays_that_of_every_line() -> None:
    rows = [line(1), line(2), line(3, marked=True), line(4, marked=True)]
    assert status_text(rows, 1).splitlines()[0] == "Backlog (4)"
