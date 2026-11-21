"""The text of status under a top: at most that many items a heading, then how many more."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.text import status_text
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
THREE = [WorkItemRow(f"ST-000{n}", f"title {n}", "backlog", created=CREATED) for n in (1, 2, 3)]
FEATURES = [FeatureRow(f"F-000{n}", f"feature {n}", "Backlog") for n in (1, 2, 3)]


def test_a_heading_lists_its_top_then_how_many_more() -> None:
    assert status_text(THREE, top=2) == (
        "Backlog (3)\n"
        "  ST-0001  title 1\n"
        "  ST-0002  title 2\n"
        "  ... 1 more\n"
        "InProgress (0)\n"
        "Completed (0)\n"
    )


def test_a_heading_with_as_many_items_as_the_top_lists_no_more_line() -> None:
    assert status_text(THREE, top=3).splitlines()[1:5] == [
        "  ST-0001  title 1",
        "  ST-0002  title 2",
        "  ST-0003  title 3",
        "InProgress (0)",
    ]


def test_the_features_are_listed_to_the_top_too() -> None:
    assert status_text([], FEATURES, top=1).splitlines()[:3] == [
        "Features (3)",
        "  F-0001  feature 1  Backlog",
        "  ... 2 more",
    ]
