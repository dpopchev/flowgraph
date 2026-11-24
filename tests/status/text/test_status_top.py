"""The text of status under a top: at most that many items a heading, then how many more."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status import Tops, same_top, status_text
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
THREE = [WorkItemRow(f"S-000{n}", f"title {n}", "backlog", created=CREATED) for n in (1, 2, 3)]
FEATURE = FeatureRow("F-0001", "a feature title", "Backlog", 0, 0)
COMPLETED = [
    WorkItemRow(f"S-000{n}", f"title {n}", "completed", created=CREATED, commit="abc1234")
    for n in (1, 2, 3)
]
BACKLOG_ONLY = Tops(backlog=1, in_progress=None, completed=None, removed=None)


def test_a_heading_lists_its_top_then_how_many_more() -> None:
    assert status_text(THREE, same_top(2)) == (
        "Backlog (3)\n"
        "  S-0001  title 1\n"
        "  S-0002  title 2\n"
        "  ... 1 more, 0 can start\n"
        "InProgress (0)\n"
        "Completed (0)\n"
    )


def test_a_heading_with_as_many_items_as_the_top_lists_no_more_line() -> None:
    assert status_text(THREE, same_top(3)).splitlines()[1:5] == [
        "  S-0001  title 1",
        "  S-0002  title 2",
        "  S-0003  title 3",
        "InProgress (0)",
    ]


def test_a_feature_counts_once_toward_the_top_of_its_heading() -> None:
    assert status_text([THREE[0], FEATURE, *THREE[1:]], same_top(2)).splitlines()[:4] == [
        "Backlog (4)",
        "  S-0001  title 1",
        "  F-0001  0/0 W  a feature title",
        "  ... 2 more, 0 can start",
    ]


def test_each_bucket_is_listed_by_its_own_top() -> None:
    assert status_text(THREE, BACKLOG_ONLY).splitlines()[1:3] == [
        "  S-0001  title 1",
        "  ... 2 more, 0 can start",
    ]


def test_the_more_line_of_the_backlog_counts_a_marked_line_beyond_the_top_and_lists_it_not() -> (
    None
):
    rows = [*THREE[:2], replace(THREE[2], next_to_start=True)]
    assert status_text(rows, BACKLOG_ONLY).splitlines()[1:3] == [
        "  S-0001  title 1",
        "  ... 2 more, 1 can start",
    ]


def test_a_completed_heading_still_ends_with_how_many_more() -> None:
    assert status_text(COMPLETED, same_top(2)).splitlines()[-1] == "  ... 1 more"


def test_a_backlog_of_two_under_a_top_of_two_has_no_more_line() -> None:
    assert status_text(THREE[:2], same_top(2)).splitlines()[1:4] == [
        "  S-0001  title 1",
        "  S-0002  title 2",
        "InProgress (0)",
    ]
